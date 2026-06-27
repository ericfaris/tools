import os

# Where temporary/working files live (Docker volume mount).
DATA_DIR = os.environ.get("DATA_DIR", "/data")
TMP_DIR = os.path.join(DATA_DIR, "tmp")

# External URL where the portal is reachable (used for absolute links if needed).
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

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

# Rate limiting: max failed auth attempts per IP within the window (seconds).
RATE_LIMIT_MAX_FAILURES = int(os.environ.get("RATE_LIMIT_MAX_FAILURES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "300"))
