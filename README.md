# Tools

A clean, private, self-hosted **portal of everyday utility tools** — PDF, image,
and file conversions — that replaces the ad-ridden, subscription-gated public
tool sites. No ads, no subscriptions, no data harvesting. Your files are
processed on **your** server, and the whole thing is designed to feel genuinely
good to use.

Accessible at `http://localhost:8200` locally, or at `https://tools.mooseflip.com`
via Cloudflare Tunnel.

See [`SPEC.md`](SPEC.md) for the full product vision.

---

## Tools (v1)

| Tool | Family | What it does |
|------|--------|--------------|
| Merge PDFs | PDF | Combine several PDFs into one |
| Split PDF | PDF | Explode a PDF into one file per page (zip) |
| Convert Image | Image | PNG ⇄ JPG ⇄ WebP |
| Images → PDF | Convert | Stitch images into a single PDF |

More PDF/image/audio/video/document tools are planned — see `SPEC.md §5`.

---

## Running locally (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000>. With no `AUTH_USER`/`AUTH_PASS` set, auth is
disabled (handy for local dev).

## Running with Docker

```bash
cp .env.example .env   # then edit AUTH_USER / AUTH_PASS
docker compose up -d --build
```

The portal is served on `127.0.0.1:8200` (mapped to the container's `8000`).

---

## Configuration

All config is via environment variables (see `app/config.py` / `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_USER` / `AUTH_PASS` | — | Single-credential HTTP Basic Auth (blank = no auth) |
| `AUTH_USERS` | — | `user:pass,user2:pass2` multi-user (takes precedence) |
| `BASE_URL` | `http://localhost:8000` | Public URL of the portal |
| `MAX_UPLOAD_BYTES` | `104857600` | Max upload size per request (100 MB) |
| `MAX_UPLOAD_FILES` | `100` | Max file parts accepted per request |
| `MAX_FORM_FIELDS` | `100` | Max non-file form fields per request |
| `MAX_IMAGE_PIXELS` | `67108864` | Decompression-bomb cap on decoded image pixels (~64 MP) |
| `RATE_LIMIT_MAX_TRACKED_IPS` | `10000` | Cap on IPs held in the failed-auth table |
| `ACCESS_LOG` | `false` | Request logging — leave off; `true` only for local debugging |

**Security:** HTTP Basic Auth on all non-public routes, CSRF Origin/Referer
checks on state-changing requests, failed-auth rate limiting, a strict
Content-Security-Policy, and a `127.0.0.1`-only bind.

---

## Privacy & ephemerality

This is a deliberately **stateless, zero-retention** platform — safe to share
with friends and family. Their documents are theirs; the server never keeps them
and never learns what anyone did.

- **Processed in memory, then gone.** Uploads and every intermediate artifact
  live only in RAM for the duration of one request. The only thing that leaves
  the server is the result you download.
- **Explicit cleanup.** Each upload is closed in a `finally` block, deleting any
  transient temp spool the instant the response is sent — even if the tool fails.
- **No logs.** Request/access logging is off by default (`--no-access-log`), and
  the app keeps no activity logger. Failed-auth counters live in memory only.
- **No caching.** Every response sends `Cache-Control: no-store` so nothing is
  cached by browsers, proxies, or CDNs.
- **No persistence by construction.** In Docker the root filesystem is
  `read_only`, `/tmp` is an in-memory `tmpfs`, and there is **no volume** — there
  is physically nowhere for a document to be stored.

These guarantees are covered by regression tests in `tests/test_privacy.py`.

---

## Adding a tool

Tools are self-contained plugins. Create a module in `app/tools/`, build a
`Tool`, and `register()` it — the portal grid and routes pick it up
automatically. The `run` function is framework-agnostic for easy testing:

```python
from .base import Result, Tool, register

def _shout(files, opts):
    name, data = files[0]
    return Result(data.upper(), f"loud-{name}", "text/plain")

register(Tool(
    id="shout", name="Shout", family="Convert", icon="📣",
    description="Uppercase a text file.", run=_shout, accept="text/plain",
))
```

Import it from `app/tools/__init__.py` and add a test in `tests/`.

---

## Tests

```bash
python -m pytest -q
```

CI runs the same on every PR and push to `main`.

## Deploy

Tag a release to trigger the Docker Hub build, then pull & restart — or just run
the `/deploy` slash command (see `.claude/commands/deploy.md`).
