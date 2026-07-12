"""End-to-end HTTP tests for the portal and tool API."""
import io
import zipfile

import pytest
from pypdf import PdfReader

from app import config
from app.tools import REGISTRY

from .helpers import ORIGIN, make_image, make_pdf


# --- Portal & pages -----------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["tools"] == len(REGISTRY)


def test_portal_renders_all_tiles_and_privacy_footer(client):
    r = client.get("/")
    assert r.status_code == 200
    for tool in REGISTRY.values():
        assert tool.name in r.text
    assert "nothing stored" in r.text  # privacy footer present


@pytest.mark.parametrize("tool_id", sorted(REGISTRY))
def test_tool_page_renders(client, tool_id):
    r = client.get(f"/tools/{tool_id}")
    assert r.status_code == 200
    assert REGISTRY[tool_id].name in r.text


def test_unknown_tool_page_404(client):
    assert client.get("/tools/does-not-exist").status_code == 404


def test_unknown_tool_api_404(client):
    r = client.post("/api/tools/nope", files=[("files", ("a.pdf", make_pdf(), "application/pdf"))], headers=ORIGIN)
    assert r.status_code == 404


# --- Request validation -------------------------------------------------------

def test_post_without_files_400(client):
    r = client.post("/api/tools/pdf-merge", data={}, headers=ORIGIN)
    assert r.status_code == 400


def test_post_without_origin_is_csrf_blocked(client):
    # No Origin/Referer header -> CSRF check fails.
    r = client.post("/api/tools/pdf-merge", files=[("files", ("a.pdf", make_pdf(), "application/pdf"))])
    assert r.status_code == 403


def test_upload_too_large_413(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("big.pdf", make_pdf(5), "application/pdf"))],
        headers=ORIGIN,
    )
    assert r.status_code == 413


def test_single_oversized_file_rejected_before_buffering(client, monkeypatch):
    # One file larger than the cap must be rejected by the chunked reader,
    # not buffered whole then checked.
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("big.bin", b"x" * 5000, "application/octet-stream"))],
        headers=ORIGIN,
    )
    assert r.status_code == 413


def test_download_filename_is_sanitized(client):
    # image-convert derives the download name from the upload name; a quote in
    # it must not break the Content-Disposition header.
    r = client.post(
        "/api/tools/image-convert",
        files=[("files", ('e"vil.png', make_image("PNG"), "image/png"))],
        data={"format": "png"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    # A well-formed header has exactly the two wrapping quotes and no stray ones.
    assert cd.count('"') == 2
    assert "\n" not in cd and "\r" not in cd


def test_download_filename_strips_angle_brackets(client):
    # A name carrying an HTML payload must come back with the angle brackets
    # gone, so it can't inject when the browser echoes the download name.
    r = client.post(
        "/api/tools/image-convert",
        files=[("files", ("<script>x.png", make_image("PNG"), "image/png"))],
        data={"format": "png"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    assert "<" not in cd and ">" not in cd


def test_oversized_content_length_rejected_before_parsing(client, monkeypatch):
    # The early Content-Length guard rejects a too-large body up front, before
    # request.form() spools the multipart payload to the tmpfs.
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 5)
    r = client.post(
        "/api/tools/pdf-merge",
        content=b"x" * 5000,
        headers={**ORIGIN, "Content-Type": "multipart/form-data; boundary=zzz"},
    )
    assert r.status_code == 413


def test_malformed_multipart_is_400_not_500(client):
    # A body that isn't valid multipart must surface as a client error, not an
    # unhandled server fault.
    r = client.post(
        "/api/tools/pdf-merge",
        content=b"garbage not multipart",
        headers={
            **ORIGIN,
            "Content-Type": "multipart/form-data; boundary=z",
        },
    )
    assert r.status_code == 400


def test_image_decompression_bomb_rejected_422(client, monkeypatch):
    # An image whose pixel count exceeds the cap is refused as unprocessable,
    # rather than being decoded and exhausting memory.
    monkeypatch.setattr(config, "MAX_IMAGE_PIXELS", 100)  # 32x32 = 1024 > 100
    r = client.post(
        "/api/tools/image-convert",
        files=[("files", ("big.png", make_image("PNG", size=(32, 32)), "image/png"))],
        data={"format": "png"},
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert "too large" in r.json()["detail"].lower()


def test_tool_failure_returns_422_not_500(client):
    # A text file is not a valid PDF; the tool raises and we surface 422.
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("notapdf.txt", b"hello world", "text/plain"))],
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert "Could not complete request" in r.json()["detail"]


# --- Per-tool round trips over HTTP -------------------------------------------

def test_api_pdf_merge(client):
    r = client.post(
        "/api/tools/pdf-merge",
        files=[
            ("files", ("a.pdf", make_pdf(2), "application/pdf")),
            ("files", ("b.pdf", make_pdf(3), "application/pdf")),
        ],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="merged.pdf"' in r.headers["content-disposition"]
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 5


def test_api_pdf_split(client):
    r = client.post(
        "/api/tools/pdf-split",
        files=[("files", ("doc.pdf", make_pdf(4), "application/pdf"))],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert len(z.namelist()) == 4


def test_api_image_convert(client):
    r = client.post(
        "/api/tools/image-convert",
        files=[("files", ("p.png", make_image("PNG"), "image/png"))],
        data={"format": "jpg"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_api_images_to_pdf(client):
    r = client.post(
        "/api/tools/images-to-pdf",
        files=[
            ("files", ("1.png", make_image("PNG"), "image/png")),
            ("files", ("2.png", make_image("PNG", (0, 255, 0)), "image/png")),
        ],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 2


def test_api_favicon(client):
    r = client.post(
        "/api/tools/favicon",
        files=[("files", ("logo.png", make_image("PNG", size=(100, 60)), "image/png"))],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert "favicon.ico" in z.namelist()


def test_api_color_palette_returns_json(client):
    r = client.post(
        "/api/tools/color-palette",
        files=[("files", ("red.png", make_image("PNG", (255, 0, 0)), "image/png"))],
        data={"count": "4"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["render"] == "palette"
    assert body["colors"][0]["hex"] == "#ff0000"


def test_api_bingo_cards(client):
    items = "\n".join(f"item{i}" for i in range(30)).encode()
    r = client.post(
        "/api/tools/bingo-cards",
        files=[("files", ("items.txt", items, "text/plain"))],
        data={"rows": "5", "cols": "5", "cards": "2"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 2


def test_api_super_bowl_bingo_needs_no_file_upload(client, monkeypatch):
    # requires_file=False: the tool must run over plain form data, no `files` part.
    from app.tools import bingo_tools

    monkeypatch.setattr(
        bingo_tools, "_get_super_bowl_matchup",
        lambda: ({"id": "1", "abbr": "AAA", "name": "Team A"}, {"id": "2", "abbr": "BBB", "name": "Team B"}),
    )
    monkeypatch.setattr(
        bingo_tools, "_get_roster",
        lambda team_id: [
            {"name": f"P{team_id}-{i}", "pos": "WR", "status": None} for i in range(10)
        ],
    )
    monkeypatch.setattr(bingo_tools, "_get_relevant_news", lambda team_names, limit=6: [])

    r = client.post(
        "/api/tools/super-bowl-bingo",
        data={"rows": "3", "cols": "3", "cards": "1"},
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
