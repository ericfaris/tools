import os
from pathlib import Path

# Application version — single source of truth is the top-level VERSION file.
VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()

# External URL where the portal is reachable (used for absolute links if needed).
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# --- Privacy ------------------------------------------------------------------
# This platform is deliberately stateless: uploads are processed in memory and
# discarded the instant a response is sent. Nothing is written to disk and no
# record of activity is kept. Request logging is OFF by default so we never
# learn what anyone does here; set ACCESS_LOG=true only for local debugging.
ACCESS_LOG = os.environ.get("ACCESS_LOG", "false").lower() == "true"

# --- Auth ---------------------------------------------------------------------
# HTTP Basic Auth. Single credential by default; AUTH_USERS takes precedence and
# allows multiple (AUTH_USERS=alice:pass1,bob:pass2).
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASS = os.environ.get("AUTH_PASS", "")

_raw_users = os.environ.get("AUTH_USERS", "")
if _raw_users:
    AUTH_CREDENTIALS: list[tuple[str, str]] = [
        (e.strip().split(":", 1)[0], e.strip().split(":", 1)[1])
        for e in _raw_users.split(",")
        if ":" in e.strip()
    ]
elif AUTH_USER and AUTH_PASS:
    AUTH_CREDENTIALS = [(AUTH_USER, AUTH_PASS)]
else:
    AUTH_CREDENTIALS = []

# --- Limits -------------------------------------------------------------------
# Max upload size per request (bytes). Default 100 MB.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))

# Caps on multipart structure, enforced during form parsing so a single request
# can't open thousands of parts/fields and exhaust memory before we read them.
MAX_UPLOAD_FILES = int(os.environ.get("MAX_UPLOAD_FILES", "100"))
MAX_FORM_FIELDS = int(os.environ.get("MAX_FORM_FIELDS", "100"))

# Decompression-bomb guard: refuse images whose decoded pixel count exceeds this,
# regardless of how few bytes they occupy on the wire. Default ~64 MP.
MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", str(64 * 1024 * 1024)))

# Rate limiting: max failed auth attempts per IP within the window (seconds).
RATE_LIMIT_MAX_FAILURES = int(os.environ.get("RATE_LIMIT_MAX_FAILURES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "300"))

# Hard cap on how many distinct client IPs the rate-limit table will track at
# once, so a flood of one-off IPs can't grow it without bound.
RATE_LIMIT_MAX_TRACKED_IPS = int(os.environ.get("RATE_LIMIT_MAX_TRACKED_IPS", "10000"))

# Comma-separated IPs of trusted reverse proxies (e.g. the Cloudflare Tunnel
# connector). When the direct peer is one of these, the real client IP for rate
# limiting is taken from CF-Connecting-IP / X-Forwarded-For — otherwise every
# user shares the proxy's single bucket. Empty by default (direct-exposure safe:
# forwarding headers are ignored unless the peer is explicitly trusted).
TRUSTED_PROXIES = {
    ip.strip() for ip in os.environ.get("TRUSTED_PROXIES", "").split(",") if ip.strip()
}
