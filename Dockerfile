FROM python:3.12-slim

# System tools for the heavier converters get added here as those tools land
# (e.g. ghostscript, imagemagick, ffmpeg, libreoffice-core, tesseract-ocr).
# The current pure-Python tools (pypdf, Pillow) need no extra system packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV DATA_DIR=/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
