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


def _items(n: int) -> bytes:
    return "\n".join(f"item{i}" for i in range(n)).encode()


def test_bingo_cards_generates_requested_page_count():
    from pypdf import PdfReader

    result = REGISTRY["bingo-cards"].run(
        [("items.txt", _items(30))], {"rows": "5", "cols": "5", "cards": "3"}
    )
    assert result.media_type == "application/pdf"
    assert result.filename == "bingo_cards.pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 3


def test_bingo_cards_free_space_reduces_items_needed():
    # A 3x3 card with free space only needs 8 unique items, not 9.
    result = REGISTRY["bingo-cards"].run(
        [("items.txt", _items(8))],
        {"rows": "3", "cols": "3", "cards": "1", "free_space": "true", "free_text": "WILD"},
    )
    assert result.media_type == "application/pdf"


def test_bingo_cards_rejects_too_few_items():
    import pytest

    with pytest.raises(ValueError):
        REGISTRY["bingo-cards"].run([("items.txt", _items(5))], {"rows": "5", "cols": "5", "cards": "1"})


def test_bingo_cards_rejects_too_many_cards():
    import pytest

    with pytest.raises(ValueError):
        REGISTRY["bingo-cards"].run([("items.txt", _items(30))], {"rows": "5", "cols": "5", "cards": "9999"})


def _fake_roster(team_id: str) -> list[dict]:
    positions = ["QB", "RB", "WR", "TE", "LB", "CB", "K"]
    return [
        {"name": f"Player{team_id}-{i}", "pos": positions[i % len(positions)], "status": None}
        for i in range(10)
    ]


def test_super_bowl_bingo_builds_cards_from_mocked_espn_data(monkeypatch):
    from pypdf import PdfReader

    from app.tools import bingo_tools

    monkeypatch.setattr(
        bingo_tools, "_get_super_bowl_matchup",
        lambda: ({"id": "1", "abbr": "AAA", "name": "Team A"}, {"id": "2", "abbr": "BBB", "name": "Team B"}),
    )
    monkeypatch.setattr(bingo_tools, "_get_roster", _fake_roster)
    monkeypatch.setattr(bingo_tools, "_get_relevant_news", lambda team_names, limit=6: ["A headline"])

    result = REGISTRY["super-bowl-bingo"].run(
        [], {"rows": "3", "cols": "3", "cards": "2", "halftime_performer": "The Band", "extra_items": "Foo, Bar"}
    )
    assert result.media_type == "application/pdf"
    assert len(PdfReader(io.BytesIO(result.data)).pages) == 2


def test_super_bowl_bingo_title_defaults_to_matchup(monkeypatch):
    from app.tools import bingo_tools

    monkeypatch.setattr(
        bingo_tools, "_get_super_bowl_matchup",
        lambda: ({"id": "1", "abbr": "AAA", "name": "Team A"}, {"id": "2", "abbr": "BBB", "name": "Team B"}),
    )
    monkeypatch.setattr(bingo_tools, "_get_roster", _fake_roster)
    monkeypatch.setattr(bingo_tools, "_get_relevant_news", lambda team_names, limit=6: [])

    result = REGISTRY["super-bowl-bingo"].run([], {"rows": "3", "cols": "3", "cards": "1"})
    assert result.media_type == "application/pdf"  # title="AAA vs BBB" renders without error


def test_super_bowl_bingo_propagates_matchup_not_set_error(monkeypatch):
    import pytest

    from app.tools import bingo_tools

    def _raise():
        raise ValueError("The Super Bowl matchup isn't set yet")

    monkeypatch.setattr(bingo_tools, "_get_super_bowl_matchup", _raise)

    with pytest.raises(ValueError, match="matchup isn't set yet"):
        REGISTRY["super-bowl-bingo"].run([], {"rows": "3", "cols": "3", "cards": "1"})


def test_super_bowl_bingo_rejects_grid_too_large_for_available_items(monkeypatch):
    import pytest

    from app.tools import bingo_tools

    monkeypatch.setattr(
        bingo_tools, "_get_super_bowl_matchup",
        lambda: ({"id": "1", "abbr": "AAA", "name": "Team A"}, {"id": "2", "abbr": "BBB", "name": "Team B"}),
    )
    monkeypatch.setattr(bingo_tools, "_get_roster", lambda team_id: _fake_roster(team_id)[:2])
    monkeypatch.setattr(bingo_tools, "_get_relevant_news", lambda team_names, limit=6: [])

    with pytest.raises(ValueError):
        REGISTRY["super-bowl-bingo"].run([], {"rows": "10", "cols": "10", "cards": "1"})
