"""Image tools and image<->PDF conversion (pure-Python: Pillow)."""
from __future__ import annotations

import io
from typing import Any

from PIL import Image

from .base import Option, Result, Tool, register

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
