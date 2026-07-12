"""Bingo card generator (pure-Python: reportlab).

Turns a plain-text list of items (one per line) into a multi-page PDF of
randomized bingo cards, one card per page. Also includes a Super Bowl variant
that builds the item list live from ESPN's public (no-key) NFL API instead of
an uploaded file.
"""
from __future__ import annotations

import io
import json
import textwrap
import urllib.error
import urllib.request
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from .base import Option, Result, Tool, register

PAGE_WIDTH, PAGE_HEIGHT = LETTER
MARGIN = 0.75 * inch
TITLE_FONT_SIZE = 28
FOOTER_FONT_SIZE = 10
CELL_FONT_SIZE = 11  # will auto-shrink for long text
HEADER_GAP = 0.35 * inch
FOOTER_GAP = 0.30 * inch

GRID_LINE_COLOR = HexColor("#222222")
FREE_SPACE_BG = HexColor("#FFF3CD")
HEADER_COLOR = HexColor("#1A1A2E")
CELL_TEXT_COLOR = HexColor("#1A1A2E")

MAX_CARDS = 200


def _load_items(data: bytes) -> list[str]:
    """Parse one item per line, skipping blanks and #-comments."""
    items: list[str] = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            items.append(stripped)
    return items


def _generate_card(
    items: list[str], rng, rows: int, cols: int, use_free_space: bool, free_space_text: str
) -> list[list[str]]:
    cells_needed = rows * cols
    center_odd = use_free_space and rows % 2 == 1 and cols % 2 == 1
    if center_odd:
        cells_needed -= 1

    chosen = rng.sample(items, cells_needed)
    idx = 0
    card: list[list[str]] = []
    center_r, center_c = rows // 2, cols // 2

    for r in range(rows):
        row: list[str] = []
        for c in range(cols):
            if center_odd and r == center_r and c == center_c:
                row.append(free_space_text)
            else:
                row.append(chosen[idx])
                idx += 1
        card.append(row)
    return card


def _draw_cell_text(canvas: Canvas, text: str, x: float, y: float, w: float, h: float, is_free: bool):
    padding = 4
    max_w = w - 2 * padding
    max_h = h - 2 * padding
    font_name = "Helvetica-Bold" if is_free else "Helvetica"

    for size in range(CELL_FONT_SIZE, 5, -1):
        canvas.setFont(font_name, size)
        wrapped = textwrap.wrap(text, width=max(int(max_w / (size * 0.5)), 8))
        line_height = size * 1.2
        total_text_h = len(wrapped) * line_height
        fits = total_text_h <= max_h
        if fits:
            for line in wrapped:
                if canvas.stringWidth(line, font_name, size) > max_w:
                    fits = False
                    break
        if fits:
            break
    else:
        size = 6
        wrapped = textwrap.wrap(text, width=max(int(max_w / (size * 0.5)), 8))
        line_height = size * 1.2
        total_text_h = len(wrapped) * line_height

    start_y = y + h / 2 + total_text_h / 2 - line_height + (line_height - size) / 2
    canvas.setFillColor(CELL_TEXT_COLOR)
    canvas.setFont(font_name, size)
    for i, line in enumerate(wrapped):
        canvas.drawCentredString(x + w / 2, start_y - i * line_height, line)


def _draw_card(
    canvas: Canvas,
    card: list[list[str]],
    card_number: int,
    title: str,
    rows: int,
    cols: int,
    use_free_space: bool,
):
    usable_w = PAGE_WIDTH - 2 * MARGIN

    canvas.setFont("Helvetica-Bold", TITLE_FONT_SIZE)
    canvas.setFillColor(HEADER_COLOR)
    title_y = PAGE_HEIGHT - MARGIN
    canvas.drawCentredString(PAGE_WIDTH / 2, title_y - TITLE_FONT_SIZE, title)

    canvas.setFont("Helvetica", FOOTER_FONT_SIZE)
    canvas.setFillColor(HEADER_COLOR)
    footer_y = MARGIN
    canvas.drawCentredString(PAGE_WIDTH / 2, footer_y, f"Card #{card_number}")

    grid_top = title_y - TITLE_FONT_SIZE - HEADER_GAP
    grid_bottom = footer_y + FOOTER_FONT_SIZE + FOOTER_GAP
    grid_height = grid_top - grid_bottom
    grid_width = usable_w

    cell_w = grid_width / cols
    cell_h = grid_height / rows
    grid_x = MARGIN
    grid_y = grid_bottom

    center_r, center_c = rows // 2, cols // 2
    center_odd = use_free_space and rows % 2 == 1 and cols % 2 == 1

    for r in range(rows):
        for c in range(cols):
            x = grid_x + c * cell_w
            y = grid_y + (rows - 1 - r) * cell_h

            is_free = center_odd and r == center_r and c == center_c
            if is_free:
                canvas.setFillColor(FREE_SPACE_BG)
                canvas.rect(x, y, cell_w, cell_h, stroke=0, fill=1)

            canvas.setStrokeColor(GRID_LINE_COLOR)
            canvas.setLineWidth(1)
            canvas.rect(x, y, cell_w, cell_h, stroke=1, fill=0)

            _draw_cell_text(canvas, card[r][c], x, y, cell_w, cell_h, is_free)


def _parse_grid_opts(opts: dict[str, Any]) -> tuple[int, int, int, bool, str]:
    """Parse the rows/cols/cards/free-space options shared by both bingo tools."""
    rows = int(opts.get("rows", 5))
    cols = int(opts.get("cols", 5))
    num_cards = int(opts.get("cards", 10))
    use_free_space = opts.get("free_space") in (True, "true", "on")
    free_space_text = str(opts.get("free_text") or "FREE")

    if rows < 1 or cols < 1:
        raise ValueError("Rows and columns must be at least 1")
    if not 1 <= num_cards <= MAX_CARDS:
        raise ValueError(f"Number of cards must be between 1 and {MAX_CARDS}")

    return rows, cols, num_cards, use_free_space, free_space_text


def _cells_needed(rows: int, cols: int, use_free_space: bool) -> int:
    n = rows * cols
    if use_free_space and rows % 2 == 1 and cols % 2 == 1:
        n -= 1
    return n


def _render_pdf(
    items: list[str], rows: int, cols: int, num_cards: int, title: str,
    use_free_space: bool, free_space_text: str,
) -> bytes:
    import random

    rng = random.Random()
    out = io.BytesIO()
    canvas = Canvas(out, pagesize=LETTER)
    for n in range(1, num_cards + 1):
        card = _generate_card(items, rng, rows, cols, use_free_space, free_space_text)
        _draw_card(canvas, card, n, title, rows, cols, use_free_space)
        canvas.showPage()
    canvas.save()
    return out.getvalue()


def _generate(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    rows, cols, num_cards, use_free_space, free_space_text = _parse_grid_opts(opts)
    title = str(opts.get("title") or "BINGO")

    items = _load_items(files[0][1])
    needed = _cells_needed(rows, cols, use_free_space)
    if len(items) < needed:
        raise ValueError(
            f"Need at least {needed} unique items to fill a {rows}x{cols} "
            f"card, but only {len(items)} were provided"
        )

    pdf = _render_pdf(items, rows, cols, num_cards, title, use_free_space, free_space_text)
    return Result(pdf, "bingo_cards.pdf", "application/pdf")


register(Tool(
    id="bingo-cards",
    name="Bingo Card Generator",
    family="Generate",
    icon="🎲",
    description="Turn a plain-text list of items into printable, randomized bingo cards (PDF).",
    run=_generate,
    accept=".txt,text/plain",
    multiple=False,
    options=[
        Option(name="rows", label="Rows", type="number", default=5),
        Option(name="cols", label="Columns", type="number", default=5),
        Option(name="cards", label="Number of cards", type="number", default=10),
        Option(name="title", label="Title", type="text", default="BINGO"),
        Option(name="free_space", label="Center free space", type="checkbox", default=False),
        Option(name="free_text", label="Free space label", type="text", default="FREE"),
    ],
))


# ---------------------------------------------------------------------------
# Super Bowl variant — item list is built live from ESPN's public NFL API
# (no API key required) instead of an uploaded file.
# ---------------------------------------------------------------------------

ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
_HEADERS = {"User-Agent": "sb-bingo/1.0 (self-hosted bingo card generator)"}

QB_TEMPLATES = [
    "{name} ({abbr}) throws a touchdown pass",
    "{name} ({abbr}) completes a deep pass",
    "{name} ({abbr}) scrambles for positive yards",
    "{name} ({abbr}) is shown talking to a coach on the sideline",
]
SKILL_TEMPLATES = [
    "{name} ({abbr}) picks up a first down",
    "{name} ({abbr}) makes a highlight-reel catch",
    "{name} ({abbr}) breaks a tackle",
    "{name} ({abbr}) scores a touchdown",
]
DEFENSE_TEMPLATES = [
    "{name} ({abbr}) makes a solo tackle",
    "{name} ({abbr}) records a sack",
    "{name} ({abbr}) breaks up a pass",
    "{name} ({abbr}) forces a fumble",
]
SPECIAL_TEMPLATES = [
    "{name} ({abbr}) kicks a field goal",
    "{name} ({abbr}) punts the ball",
]
INJURY_STATUSES = {"Questionable", "Doubtful", "Out"}
INJURY_TEMPLATES = [
    "{name} ({abbr}), listed as {status}, takes the field",
    "Broadcast mentions {name} ({abbr})'s {status} injury status",
]

_QB = {"QB"}
_SKILL = {"RB", "FB", "WR", "TE"}
_DEFENSE = {"DE", "DT", "NT", "LB", "ILB", "OLB", "CB", "DB", "S", "FS", "SS"}
_SPECIAL = {"K", "P"}


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not reach ESPN's NFL API ({exc})") from None


def _get_super_bowl_matchup() -> tuple[dict, dict]:
    """Return (team1, team2) dicts with id/abbr/name for this season's Super Bowl.

    Raises ValueError if the matchup isn't determined yet (teams still TBD).
    """
    data = _fetch_json(f"{ESPN_API}/scoreboard?seasontype=3&week=5")
    events = data.get("events") or []
    if not events:
        raise ValueError("Could not find this season's Super Bowl game on ESPN")

    competitors = events[0].get("competitions", [{}])[0].get("competitors", [])
    if len(competitors) != 2:
        raise ValueError("Super Bowl matchup isn't available yet")

    teams = []
    for c in competitors:
        team = c.get("team", {})
        abbr = team.get("abbreviation", "TBD")
        if not team.get("id") or abbr == "TBD":
            raise ValueError(
                "The Super Bowl matchup isn't set yet — check back once both "
                "conference championship games are final, or use the Bingo Card "
                "Generator tool with a manual item list instead"
            )
        teams.append({"id": team["id"], "abbr": abbr, "name": team.get("displayName", abbr)})

    return teams[0], teams[1]


def _get_roster(team_id: str) -> list[dict]:
    data = _fetch_json(f"{ESPN_API}/teams/{team_id}/roster")
    players = []
    for group in data.get("athletes") or []:
        for athlete in group.get("items") or []:
            pos = (athlete.get("position") or {}).get("abbreviation", "")
            name = athlete.get("displayName")
            if not name or not pos:
                continue
            status = None
            for injury in athlete.get("injuries") or []:
                s = injury.get("status")
                if isinstance(s, str) and s in INJURY_STATUSES:
                    status = s
                    break
            players.append({"name": name, "pos": pos, "status": status})
    return players


def _get_relevant_news(team_names: list[str], limit: int = 6) -> list[str]:
    """Best-effort: league headlines that mention either team. Never fails the
    whole card generation — an empty list just means fewer non-player items."""
    try:
        data = _fetch_json(f"{ESPN_API}/news?limit=50")
    except ValueError:
        return []
    headlines = []
    for article in data.get("articles") or []:
        headline = article.get("headline")
        if headline and any(name.split()[-1] in headline for name in team_names):
            headlines.append(headline)
        if len(headlines) >= limit:
            break
    return headlines


def _team_items(rng, team: dict, roster: list[dict]) -> list[str]:
    items = []
    for p in roster:
        template_set = (
            QB_TEMPLATES if p["pos"] in _QB else
            SKILL_TEMPLATES if p["pos"] in _SKILL else
            DEFENSE_TEMPLATES if p["pos"] in _DEFENSE else
            SPECIAL_TEMPLATES if p["pos"] in _SPECIAL else
            None
        )
        if template_set is None:
            continue
        if p["status"] and rng.random() < 0.5:
            template = rng.choice(INJURY_TEMPLATES)
            items.append(template.format(name=p["name"], abbr=team["abbr"], status=p["status"]))
        else:
            template = rng.choice(template_set)
            items.append(template.format(name=p["name"], abbr=team["abbr"]))
    return items


def _generate_sb(files: list[tuple[str, bytes]], opts: dict[str, Any]) -> Result:
    import random

    rows, cols, num_cards, use_free_space, free_space_text = _parse_grid_opts(opts)

    team1, team2 = _get_super_bowl_matchup()
    roster1 = _get_roster(team1["id"])
    roster2 = _get_roster(team2["id"])
    if not roster1 or not roster2:
        raise ValueError("ESPN did not return roster data for one of the teams yet")

    rng = random.Random()
    items = _team_items(rng, team1, roster1) + _team_items(rng, team2, roster2)
    items += _get_relevant_news([team1["name"], team2["name"]])

    for key, phrasing in (
        ("halftime_performer", "{v} takes the stage for the halftime show"),
        ("anthem_singer", "{v} sings the national anthem"),
    ):
        value = str(opts.get(key) or "").strip()
        if value:
            items.append(phrasing.format(v=value))

    extra = str(opts.get("extra_items") or "")
    items += [s.strip() for s in extra.split(",") if s.strip()]

    # Dedupe while preserving order (a headline or manual entry could repeat).
    items = list(dict.fromkeys(items))

    needed = _cells_needed(rows, cols, use_free_space)
    if len(items) < needed:
        raise ValueError(
            f"Only found {len(items)} usable items from ESPN for a {rows}x{cols} "
            f"card, but {needed} are needed — try a smaller grid"
        )

    title = str(opts.get("title") or "").strip() or f"{team1['abbr']} vs {team2['abbr']}"
    pdf = _render_pdf(items, rows, cols, num_cards, title, use_free_space, free_space_text)
    return Result(pdf, "super_bowl_bingo.pdf", "application/pdf")


register(Tool(
    id="super-bowl-bingo",
    name="Super Bowl Bingo",
    family="Generate",
    icon="🏈",
    description=(
        "Live Super Bowl bingo cards — pulls this season's matchup, rosters, "
        "and injury/news data straight from ESPN. No file upload needed."
    ),
    run=_generate_sb,
    requires_file=False,
    options=[
        Option(name="rows", label="Rows", type="number", default=5),
        Option(name="cols", label="Columns", type="number", default=5),
        Option(name="cards", label="Number of cards", type="number", default=10),
        Option(name="title", label="Title", type="text", default="",
               help="Leave blank to auto-fill with the matchup (e.g. \"KC vs PHI\")"),
        Option(name="free_space", label="Center free space", type="checkbox", default=True),
        Option(name="free_text", label="Free space label", type="text", default="FREE"),
        Option(name="halftime_performer", label="Halftime performer", type="text", default="",
               help="Optional — announced weeks ahead of the game"),
        Option(name="anthem_singer", label="National anthem singer", type="text", default="",
               help="Optional"),
        Option(name="extra_items", label="Extra items", type="text", default="",
               help="Optional, comma-separated (celebrities spotted, commercial themes, storylines, etc.)"),
    ],
))
