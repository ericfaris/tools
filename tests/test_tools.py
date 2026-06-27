"""Unit tests for the framework-agnostic tool `run` functions."""
import io
import zipfile

from PIL import Image
from pypdf import PdfReader, PdfWriter

from app.tools import REGISTRY


def _make_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_image(fmt: str = "PNG", color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", (32, 32), color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_registry_has_expected_tools():
    for tid in ("pdf-merge", "pdf-split", "image-convert", "images-to-pdf"):
        assert tid in REGISTRY


def test_pdf_merge_combines_pages():
    tool = REGISTRY["pdf-merge"]
    files = [("a.pdf", _make_pdf(2)), ("b.pdf", _make_pdf(3))]
    result = tool.run(files, {})
    assert result.media_type == "application/pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 5


def test_pdf_split_returns_zip_per_page():
    tool = REGISTRY["pdf-split"]
    result = tool.run([("doc.pdf", _make_pdf(3))], {})
    assert result.media_type == "application/zip"
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        assert len(z.namelist()) == 3


def test_image_convert_to_jpg():
    tool = REGISTRY["image-convert"]
    result = tool.run([("pic.png", _make_image("PNG"))], {"format": "jpg"})
    assert result.media_type == "image/jpeg"
    assert result.filename.endswith(".jpg")
    assert Image.open(io.BytesIO(result.data)).format == "JPEG"


def test_images_to_pdf():
    tool = REGISTRY["images-to-pdf"]
    files = [("1.png", _make_image("PNG")), ("2.png", _make_image("PNG", (0, 255, 0)))]
    result = tool.run(files, {})
    assert result.media_type == "application/pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 2
