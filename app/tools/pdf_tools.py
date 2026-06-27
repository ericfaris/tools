"""PDF manipulation tools (pure-Python: pypdf)."""
from __future__ import annotations

import io
import zipfile
from typing import Any

from pypdf import PdfReader, PdfWriter

from .base import Option, Result, Tool, register


def _merge(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    writer = PdfWriter()
    for _name, data in files:
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return Result(out.getvalue(), "merged.pdf", "application/pdf")


def _split(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    """Explode a PDF into one PDF per page, returned as a zip."""
    name, data = files[0]
    reader = PdfReader(io.BytesIO(data))
    stem = name.rsplit(".", 1)[0] or "page"
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            pbuf = io.BytesIO()
            writer.write(pbuf)
            z.writestr(f"{stem}-{i:03d}.pdf", pbuf.getvalue())
    return Result(zbuf.getvalue(), f"{stem}-pages.zip", "application/zip")


register(Tool(
    id="pdf-merge",
    name="Merge PDFs",
    family="PDF",
    icon="🧩",
    description="Combine several PDFs into one, in the order you add them.",
    run=_merge,
    accept="application/pdf",
    multiple=True,
))

register(Tool(
    id="pdf-split",
    name="Split PDF",
    family="PDF",
    icon="✂️",
    description="Explode a PDF into one file per page, delivered as a zip.",
    run=_split,
    accept="application/pdf",
    multiple=False,
))
