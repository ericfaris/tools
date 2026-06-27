"""Image tools and image<->PDF conversion (pure-Python: Pillow)."""
from __future__ import annotations

import io
import zipfile
from typing import Any

from PIL import Image

from .base import JsonResult, Option, Result, Tool, register

_PIL_FORMAT = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}
_MEDIA_TYPE = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}


def _convert(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    fmt = str(opts.get("format", "png")).lower()
    pil_fmt = _PIL_FORMAT.get(fmt)
    if pil_fmt is None:
        raise ValueError(f"Unsupported target format: {fmt}")

    name, data = files[0]
    img = Image.open(io.BytesIO(data))

    # JPEG has no alpha channel; flatten transparency onto white.
    if pil_fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    out = io.BytesIO()
    img.save(out, format=pil_fmt)
    stem = name.rsplit(".", 1)[0] or "image"
    return Result(out.getvalue(), f"{stem}.{fmt}", _MEDIA_TYPE[fmt])


def _images_to_pdf(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    images = [Image.open(io.BytesIO(d)).convert("RGB") for _n, d in files]
    out = io.BytesIO()
    images[0].save(out, format="PDF", save_all=True, append_images=images[1:])
    return Result(out.getvalue(), "images.pdf", "application/pdf")


def _square(img: Image.Image) -> Image.Image:
    """Center-crop to a square so icons aren't distorted."""
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    return img.crop((left, top, left + side, top + side))


# Standard favicon / app-icon set: (filename, size, format).
_FAVICON_SET = [
    ("favicon-16x16.png", 16, "PNG"),
    ("favicon-32x32.png", 32, "PNG"),
    ("favicon-48x48.png", 48, "PNG"),
    ("apple-touch-icon.png", 180, "PNG"),
    ("icon-192.png", 192, "PNG"),
    ("icon-512.png", 512, "PNG"),
]

_FAVICON_SNIPPET = """<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
"""


def _favicons(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    _name, data = files[0]
    src = _square(Image.open(io.BytesIO(data)).convert("RGBA"))

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, size, fmt in _FAVICON_SET:
            resized = src.resize((size, size), Image.LANCZOS)
            pbuf = io.BytesIO()
            resized.save(pbuf, format=fmt)
            z.writestr(fname, pbuf.getvalue())

        # Multi-resolution favicon.ico (16/32/48).
        ico = io.BytesIO()
        src.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        z.writestr("favicon.ico", ico.getvalue())

        z.writestr("head-snippet.html", _FAVICON_SNIPPET)

    return Result(zbuf.getvalue(), "favicons.zip", "application/zip")


def _palette(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> JsonResult:
    count = int(opts.get("count", 6))
    img = Image.open(io.BytesIO(files[0][1])).convert("RGB")
    img.thumbnail((240, 240))  # downscale for speed; colors are unaffected enough

    quant = img.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette()
    # getcolors() -> [(pixel_count, palette_index), ...]
    by_freq = sorted(quant.getcolors() or [], reverse=True)
    total = sum(c for c, _ in by_freq) or 1

    colors = []
    for pixel_count, idx in by_freq[:count]:
        r, g, b = palette[idx * 3 : idx * 3 + 3]
        colors.append({
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "rgb": [r, g, b],
            "weight": round(pixel_count / total, 3),
        })
    return JsonResult(render="palette", payload={"colors": colors})


register(Tool(
    id="favicon",
    name="Favicon Generator",
    family="Image",
    icon="⭐",
    description="Turn any image into a full favicon / app-icon set, zipped with an HTML snippet.",
    run=_favicons,
    accept="image/*",
    multiple=False,
))

register(Tool(
    id="color-palette",
    name="Color Picker",
    family="Image",
    icon="🎯",
    description="Pull the dominant color palette from an image — click any swatch to copy its hex.",
    run=_palette,
    accept="image/*",
    multiple=False,
    options=[
        Option(
            name="count",
            label="Colors",
            type="select",
            default="6",
            choices=[("4", "4"), ("6", "6"), ("8", "8"), ("12", "12")],
        ),
    ],
))


register(Tool(
    id="image-convert",
    name="Convert Image",
    family="Image",
    icon="🎨",
    description="Convert an image between PNG, JPG, and WebP.",
    run=_convert,
    accept="image/*",
    multiple=False,
    options=[
        Option(
            name="format",
            label="Convert to",
            type="select",
            default="png",
            choices=[("png", "PNG"), ("jpg", "JPG"), ("webp", "WebP")],
        ),
    ],
))

register(Tool(
    id="images-to-pdf",
    name="Images → PDF",
    family="Convert",
    icon="📚",
    description="Stitch one or more images into a single PDF, one image per page.",
    run=_images_to_pdf,
    accept="image/*",
    multiple=True,
))
