from __future__ import annotations

import base64
import hmac
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile

from . import config
from .tools import REGISTRY, JsonResult, families

# No application logger by design: this platform keeps no record of activity.
# (Request/access logging is disabled at the uvicorn level — see Dockerfile.)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["version"] = config.VERSION

app = FastAPI(title="Tools")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Paths reachable without auth.
PUBLIC_PREFIXES = ("/static/", "/favicon.ico", "/health")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; connect-src 'self'"
)

# --- Rate limiting (failed auth attempts per IP) ------------------------------
_failures: dict[str, list[float]] = {}
_failures_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    # Only honor forwarding headers when the direct peer is a trusted proxy;
    # otherwise they can be spoofed. Behind the Cloudflare Tunnel this keeps the
    # rate limiter per-user instead of lumping everyone into the proxy's bucket.
    if peer in config.TRUSTED_PROXIES:
        forwarded = (
            request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for", "")
        )
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    with _failures_lock:
        hits = [t for t in _failures.get(ip, []) if now - t < window]
        if hits:
            _failures[ip] = hits
        else:
            _failures.pop(ip, None)  # don't retain empty buckets forever
        return len(hits) >= config.RATE_LIMIT_MAX_FAILURES


def _record_failure(ip: str) -> None:
    # Counters live in memory only (for rate limiting) and are never logged.
    now = time.time()
    with _failures_lock:
        # Bound the table: if we're at capacity and this is a brand-new IP, drop
        # any buckets whose entries have all aged out so a flood of one-off IPs
        # can't grow it without limit. (Sweep only on the rare capacity hit.)
        if ip not in _failures and len(_failures) >= config.RATE_LIMIT_MAX_TRACKED_IPS:
            window = config.RATE_LIMIT_WINDOW_SECONDS
            for stale_ip in [
                k for k, ts in _failures.items() if all(now - t >= window for t in ts)
            ]:
                del _failures[stale_ip]
        _failures.setdefault(ip, []).append(now)


def _clear_failures(ip: str) -> None:
    # A successful auth wipes the IP's failure history.
    with _failures_lock:
        _failures.pop(ip, None)


# --- CSRF (Origin/Referer check on state-changing requests) -------------------
def _is_state_changing(request: Request) -> bool:
    return request.method in ("POST", "PUT", "PATCH", "DELETE")


def _csrf_ok(request: Request) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return False
    # Exact host match — a substring check would accept evil-<host>.com etc.
    return urlparse(origin).netloc == request.headers.get("host", "")


def _safe_filename(name: str) -> str:
    """Strip path components and characters that would corrupt or inject into
    the Content-Disposition header or, once the name is echoed back into the
    page, the DOM (the name can derive from a user upload). We drop angle
    brackets and all C0 control characters in addition to quotes and CR/LF."""
    base = Path(name).name
    cleaned = "".join(ch for ch in base if ch not in '"<>' and ord(ch) >= 0x20)
    return cleaned or "download"


def _check_basic_auth(request: Request) -> bool:
    if not config.AUTH_CREDENTIALS:
        return True  # auth disabled
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
    except Exception:
        return False
    for valid_user, valid_pw in config.AUTH_CREDENTIALS:
        if hmac.compare_digest(user, valid_user) and hmac.compare_digest(pw, valid_pw):
            return True
    return False


def _apply_security_headers(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Never let a browser, proxy, or CDN cache anyone's files or results.
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


async def _authorize_or_dispatch(request: Request, call_next) -> Response:
    path = request.url.path
    is_public = any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)
    if is_public:
        return await call_next(request)

    ip = _client_ip(request)
    if _is_rate_limited(ip):
        return Response(status_code=429, content="Too many failed attempts")

    if config.AUTH_CREDENTIALS:
        if _check_basic_auth(request):
            _clear_failures(ip)
        else:
            _record_failure(ip)
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Tools"'},
            )

    if _is_state_changing(request) and not _csrf_ok(request):
        return Response(status_code=403, content="CSRF check failed")

    # Reject oversized bodies up front, before request.form() spools the whole
    # multipart payload to the in-memory tmpfs. The per-chunk check in run_tool
    # still backstops chunked uploads that omit Content-Length.
    if _is_state_changing(request):
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > config.MAX_UPLOAD_BYTES:
            return Response(status_code=413, content="Upload too large")

    return await call_next(request)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Security headers are applied to *every* response, including the early
    # 401/403/429 returns above.
    return _apply_security_headers(await _authorize_or_dispatch(request, call_next))


@app.get("/health")
def health():
    return {"status": "ok", "version": config.VERSION, "tools": len(REGISTRY)}


@app.get("/", response_class=HTMLResponse)
def portal(request: Request):
    grouped = {fam: [] for fam in families()}
    for tool in REGISTRY.values():
        grouped[tool.family].append(tool)
    return templates.TemplateResponse(
        request, "index.html", {"grouped": grouped}
    )


@app.get("/tools/{tool_id}", response_class=HTMLResponse)
def tool_page(request: Request, tool_id: str):
    tool = REGISTRY.get(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Unknown tool")
    return templates.TemplateResponse(
        request, "tool.html", {"tool": tool}
    )


@app.post("/api/tools/{tool_id}")
async def run_tool(request: Request, tool_id: str):
    tool = REGISTRY.get(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Unknown tool")

    try:
        form = await request.form(
            max_files=config.MAX_UPLOAD_FILES, max_fields=config.MAX_FORM_FIELDS
        )
    except Exception:
        # A malformed multipart body (bad boundary, truncated payload, or more
        # parts/fields than allowed) is a client error, not a server fault.
        raise HTTPException(status_code=400, detail="Malformed upload")
    uploads = [v for v in form.getlist("files") if isinstance(v, UploadFile)]
    if not uploads and tool.requires_file:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Everything below stays in memory. The `finally` closes each UploadFile,
    # which deletes any transient on-disk spool immediately — so no upload, and
    # no intermediate artifact, ever outlives the request.
    files: list[tuple[str, bytes]] = []
    try:
        total = 0
        for up in uploads:
            # Read in bounded chunks so an oversized file is rejected before it
            # is ever buffered whole — no single upload can exhaust memory.
            buf = bytearray()
            while chunk := await up.read(64 * 1024):
                total += len(chunk)
                if total > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Upload too large")
                buf += chunk
            files.append((up.filename or "file", bytes(buf)))

        opts = {opt.name: form.get(opt.name, opt.default) for opt in tool.options}

        try:
            result = tool.run(files, opts)
        except HTTPException:
            raise
        except Exception as exc:  # tool failures must not 500 the portal
            # The reason goes to the user only; we keep no server-side log of it.
            raise HTTPException(status_code=422, detail=f"Could not complete request: {exc}")

        if isinstance(result, JsonResult):
            return JSONResponse({"render": result.render, **result.payload})

        safe_name = _safe_filename(result.filename)
        return Response(
            content=result.data,
            media_type=result.media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )
    finally:
        for up in uploads:
            await up.close()  # removes the temp spool file, if any
        files.clear()
