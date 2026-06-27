"""Unit tests for the framework-agnostic tool `run` functions."""
import io
import zipfile

from PIL import Image
from pypdf import PdfReader

from app.tools import REGISTRY

from .helpers import make_image, make_pdf


def test_pdf_merge_combines_pages():
    files = [("a.pdf", make_pdf(2)), ("b.pdf", make_pdf(3))]
    result = REGISTRY["pdf-merge"].run(files, {})
    assert result.media_type == "application/pdf"
    assert result.filename == "merged.pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 5


def test_pdf_split_returns_one_pdf_per_page_in_zip():
    result = REGISTRY["pdf-split"].run([("doc.pdf", make_pdf(3))], {})
    assert result.media_type == "application/zip"
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        names = z.namelist()
        assert len(names) == 3
        # Each entry must itself be a single-page PDF.
        for name in names:
            assert len(PdfReader(io.BytesIO(z.read(name))).pages) == 1


def test_image_convert_png_to_jpg_flattens_alpha():
    # An RGBA source must convert to JPEG without raising.
    img = Image.new("RGBA", (16, 16), (10, 20, 30, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = REGISTRY["image-convert"].run([("pic.png", buf.getvalue())], {"format": "jpg"})
    assert result.media_type == "image/jpeg"
    assert result.filename.endswith(".jpg")
    assert Image.open(io.BytesIO(result.data)).format == "JPEG"


def test_image_convert_to_webp():
    result = REGISTRY["image-convert"].run([("p.png", make_image("PNG"))], {"format": "webp"})
    assert result.media_type == "image/webp"
    assert Image.open(io.BytesIO(result.data)).format == "WEBP"


def test_image_convert_rejects_unknown_format():
    import pytest
    with pytest.raises(ValueError):
        REGISTRY["image-convert"].run([("p.png", make_image("PNG"))], {"format": "tiff"})


def test_images_to_pdf_one_page_per_image():
    files = [("1.png", make_image("PNG")), ("2.png", make_image("PNG", (0, 255, 0)))]
    result = REGISTRY["images-to-pdf"].run(files, {})
    assert result.media_type == "application/pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 2


def test_favicon_zip_contains_full_icon_set():
    result = REGISTRY["favicon"].run([("logo.png", make_image("PNG", size=(120, 80)))], {})
    assert result.media_type == "application/zip"
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        names = set(z.namelist())
        assert {
            "favicon.ico", "favicon-16x16.png", "favicon-32x32.png",
            "favicon-48x48.png", "apple-touch-icon.png", "icon-192.png",
            "icon-512.png", "head-snippet.html",
        } == names
        # Icons must be square and correctly sized.
        assert Image.open(io.BytesIO(z.read("icon-512.png"))).size == (512, 512)
        assert Image.open(io.BytesIO(z.read("apple-touch-icon.png"))).size == (180, 180)


def test_color_palette_finds_dominant_color():
    result = REGISTRY["color-palette"].run([("red.png", make_image("PNG", (255, 0, 0)))], {"count": "4"})
    assert result.render == "palette"
    colors = result.payload["colors"]
    assert colors
    assert colors[0]["hex"] == "#ff0000"
    assert colors[0]["rgb"] == [255, 0, 0]
    assert 0 <= colors[0]["weight"] <= 1


def test_color_palette_respects_count():
    # A 4-color image, asking for at most 4.
    img = Image.new("RGB", (40, 40))
    for i, c in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]):
        img.paste(c, (i * 10, 0, i * 10 + 10, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = REGISTRY["color-palette"].run([("x.png", buf.getvalue())], {"count": "4"})
    assert len(result.payload["colors"]) <= 4
