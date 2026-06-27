from __future__ import annotations

import base64
import hmac
import threading
import time
from pathlib import Path

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
    # Trust only the direct peer; forwarding headers can be spoofed.
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    with _failures_lock:
        hits = [t for t in _failures.get(ip, []) if now - t < window]
        _failures[ip] = hits
        return len(hits) >= config.RATE_LIMIT_MAX_FAILURES


def _record_failure(ip: str) -> None:
    # Counters live in memory only (for rate limiting) and are never logged.
    with _failures_lock:
        _failures.setdefault(ip, []).append(time.time())


# --- CSRF (Origin/Referer check on state-changing requests) -------------------
def _is_state_changing(request: Request) -> bool:
    return request.method in ("POST", "PUT", "PATCH", "DELETE")


def _csrf_ok(request: Request) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return False
    host = request.headers.get("host", "")
    return host in origin


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


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    is_public = any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)

    if not is_public:
        ip = _client_ip(request)
        if _is_rate_limited(ip):
            return Response(status_code=429, content="Too many failed attempts")

        if not _check_basic_auth(request):
            if config.AUTH_CREDENTIALS:
                _record_failure(ip)
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Tools"'},
            )

        if _is_state_changing(request) and not _csrf_ok(request):
            return Response(status_code=403, content="CSRF check failed")

    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Never let a browser, proxy, or CDN cache anyone's files or results.
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "tools": len(REGISTRY)}


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

    form = await request.form()
    uploads = [v for v in form.getlist("files") if isinstance(v, UploadFile)]
    if not uploads:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Everything below stays in memory. The `finally` closes each UploadFile,
    # which deletes any transient on-disk spool immediately — so no upload, and
    # no intermediate artifact, ever outlives the request.
    files: list[tuple[str, bytes]] = []
    try:
        total = 0
        for up in uploads:
            data = await up.read()
            total += len(data)
            if total > config.MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Upload too large")
            files.append((up.filename or "file", data))

        opts = {opt.name: form.get(opt.name, opt.default) for opt in tool.options}

        try:
            result = tool.run(files, opts)
        except HTTPException:
            raise
        except Exception as exc:  # tool failures must not 500 the portal
            # The reason goes to the user only; we keep no server-side log of it.
            raise HTTPException(status_code=422, detail=f"Could not process file: {exc}")

        if isinstance(result, JsonResult):
            return JSONResponse({"render": result.render, **result.payload})

        safe_name = Path(result.filename).name
        return Response(
            content=result.data,
            media_type=result.media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )
    finally:
        for up in uploads:
            await up.close()  # removes the temp spool file, if any
        files.clear()
