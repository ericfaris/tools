"""Shared builders and constants for the test suite."""
import io

from PIL import Image
from pypdf import PdfWriter

# The TestClient talks to http://testserver, so a matching Origin passes the
# CSRF Origin/Referer check for state-changing requests.
ORIGIN = {"Origin": "http://testserver"}


def make_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_image(fmt: str = "PNG", color=(255, 0, 0), size=(32, 32)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()
