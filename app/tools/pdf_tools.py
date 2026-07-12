"""PDF manipulation tools (pure-Python: pypdf, PyMuPDF, ebooklib)."""
from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from typing import Any

import fitz  # PyMuPDF
from ebooklib import epub
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


# --- PDF -> EPUB -----------------------------------------------------------
# Ports the formatting-preserving conversion (headings/bold/italic/chapters)
# from the standalone pdf-to-epub script into the tool plugin interface.

_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4


def _classify_sizes(doc: fitz.Document) -> tuple[float, list[float]]:
    sizes = []
    for page in doc:
        for block in page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip():
                        sizes.append(round(span["size"], 1))

    if not sizes:
        return 12.0, []

    size_counts = Counter(sizes)
    body_size = size_counts.most_common(1)[0][0]

    sorted_sizes = sorted(set(sizes), reverse=True)
    heading_sizes = [s for s in sorted_sizes if s > body_size * 1.05][:3]
    return body_size, heading_sizes


def _is_running_header(block: dict, page_height: float, body_size: float) -> bool:
    bbox = block.get("bbox", (0, 0, 0, 0))
    block_top = bbox[1]
    block_bottom = bbox[3]

    near_edge = block_top < page_height * 0.08 or block_bottom > page_height * 0.92

    texts = []
    sizes = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            t = span["text"].strip()
            if t:
                texts.append(t)
                sizes.append(round(span["size"], 1))

    if not texts:
        return True

    small_font = sizes and max(sizes) < body_size * 0.95

    combined = " ".join(texts)
    looks_like_header = bool(
        re.match(r"^(PAGE\s+\d+|page\s+\d+|\d+)(\s+OF\s+\d+)?$", combined, re.IGNORECASE)
    )

    return near_edge and (small_font or looks_like_header)


def _span_to_html(span: dict) -> str:
    text = span["text"]
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if not text.strip():
        return escaped

    flags = span["flags"]
    is_bold = bool(flags & _FLAG_BOLD)
    is_italic = bool(flags & _FLAG_ITALIC)

    if is_bold and is_italic:
        return f"<strong><em>{escaped}</em></strong>"
    elif is_bold:
        return f"<strong>{escaped}</strong>"
    elif is_italic:
        return f"<em>{escaped}</em>"
    return escaped


def _extract_html(doc: fitz.Document) -> str:
    body_size, heading_sizes = _classify_sizes(doc)
    html_parts = []

    for page in doc:
        page_height = page.rect.height
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block["type"] != 0:
                continue
            if _is_running_header(block, page_height, body_size):
                continue

            line_htmls = []
            dominant_size = body_size
            is_bold_block = False

            for line in block["lines"]:
                line_html = ""
                for span in line["spans"]:
                    line_html += _span_to_html(span)
                    if span["text"].strip():
                        dominant_size = round(span["size"], 1)
                        is_bold_block = bool(span["flags"] & _FLAG_BOLD)
                stripped = line_html.strip()
                if stripped:
                    line_htmls.append(stripped)

            block_text = " ".join(line_htmls).strip()
            if not block_text:
                continue

            if dominant_size in heading_sizes:
                level = heading_sizes.index(dominant_size) + 1
                tag = f"h{level}"
            elif is_bold_block and dominant_size >= body_size * 0.95:
                tag = "h3"
            else:
                tag = "p"

            html_parts.append(f"<{tag}>{block_text}</{tag}>")

    return "\n".join(html_parts)


def _split_into_chapters(html_content: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?=<h[123][^>]*>)", re.IGNORECASE)
    sections = pattern.split(html_content)

    chapters = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r"<h[123][^>]*>(.*?)</h[123]>", section, re.IGNORECASE | re.DOTALL)
        if title_match:
            raw = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
            title = raw[:80] if raw else f"Section {i}"
        else:
            title = f"Section {i}"
        chapters.append((title, section))

    if not chapters:
        chapters = [("Content", html_content)]

    return chapters


def _build_epub(chapters: list[tuple[str, str]], title: str, author: str) -> bytes:
    book = epub.EpubBook()
    book.set_identifier("pdf-converted-001")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content="""
body { font-family: serif; line-height: 1.6; margin: 1em 2em; }
h1, h2, h3 { font-family: sans-serif; margin-top: 1.5em; line-height: 1.3; }
p { margin: 0.5em 0; text-indent: 1.5em; }
p:first-of-type, h1 + p, h2 + p, h3 + p { text-indent: 0; }
""".strip(),
    )
    book.add_item(css)

    epub_chapters = []
    spine = ["nav"]

    for idx, (ch_title, ch_html) in enumerate(chapters):
        file_name = f"chapter_{idx:03d}.xhtml"
        content = (
            "<?xml version='1.0' encoding='utf-8'?>\n"
            "<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head>\n"
            f"  <title>{ch_title}</title>\n"
            '  <link rel="stylesheet" href="../style/main.css" type="text/css"/>\n'
            "</head>\n"
            "<body>\n"
            f"{ch_html}\n"
            "</body>\n"
            "</html>"
        )
        ch = epub.EpubHtml(title=ch_title, file_name=file_name, lang="en")
        ch.content = content.encode("utf-8")
        ch.add_item(css)
        book.add_item(ch)
        epub_chapters.append(ch)
        spine.append(ch)

    book.toc = [epub.Link(c.file_name, c.title, c.file_name) for c in epub_chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    out = io.BytesIO()
    epub.write_epub(out, book)
    return out.getvalue()


def _pdf_to_epub(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    name, data = files[0]
    stem = name.rsplit(".", 1)[0] or "book"

    doc = fitz.open(stream=data, filetype="pdf")
    html_content = _extract_html(doc)
    doc.close()

    chapters = _split_into_chapters(html_content)

    title = (opts.get("title") or "").strip() or stem
    author = (opts.get("author") or "").strip() or "Unknown"

    epub_bytes = _build_epub(chapters, title, author)
    return Result(epub_bytes, f"{stem}.epub", "application/epub+zip")


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

register(Tool(
    id="pdf-to-epub",
    name="PDF to EPUB",
    family="PDF",
    icon="📖",
    description="Convert a PDF into an EPUB, preserving headings, bold/italic, and chapter breaks.",
    run=_pdf_to_epub,
    accept="application/pdf",
    multiple=False,
    options=[
        Option(name="title", label="Title", type="text", default="", help="Defaults to the PDF filename."),
        Option(name="author", label="Author", type="text", default="", help="Defaults to \"Unknown\"."),
    ],
))
