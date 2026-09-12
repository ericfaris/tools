FROM python:3.14-slim

# System tools for the heavier converters get added here as those tools land
# (e.g. ghostscript, imagemagick, ffmpeg, libreoffice-core, tesseract-ocr).
# The current pure-Python tools (pypdf, Pillow) need no extra system packages.
# upgrade first: picks up any Debian security patches released since this
# base image tag was last rebuilt (python:3.14-slim), independent of when
# Docker Hub gets around to republishing it -- Trivy found several dozen
# already-fixed CVEs sitting unpatched purely because of that lag.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION .
COPY app/ ./app/

# Don't write .pyc files, and send transient temp spills to /tmp (mounted as an
# in-memory tmpfs by docker-compose, so even those never touch disk).
ENV PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR=/tmp

EXPOSE 8000

# --no-access-log: we keep no record of who used the platform or what they did.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
