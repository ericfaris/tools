"""Tool plugin registry.

Each tool is a self-contained module that builds a `Tool` and calls
`register()`. The portal grid and routes are generated from `REGISTRY`, so
adding a tool never touches the core.

A tool's `run` callable is intentionally framework-agnostic for easy testing:

    run(files: list[tuple[str, bytes]], opts: dict) -> Result

where `files` is a list of (filename, raw_bytes) and `Result` carries the output
bytes, a download filename, and a media type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Option:
    """A single user-configurable option rendered on the tool page."""
    name: str
    label: str
    type: str = "text"  # text | number | select | checkbox
    default: Any = None
    choices: list[tuple[str, str]] = field(default_factory=list)  # (value, label)
    help: str = ""


@dataclass
class Result:
    """A downloadable file produced by a tool."""
    data: bytes
    filename: str
    media_type: str


@dataclass
class JsonResult:
    """An inline result rendered in the page rather than downloaded.

    `render` names the client-side renderer (e.g. "palette"); `payload` is the
    data it renders.
    """
    render: str
    payload: dict[str, Any]


# run(files, opts) -> Result | JsonResult
RunFn = Callable[[list[tuple[str, bytes]], dict[str, Any]], "Result | JsonResult"]


@dataclass
class Tool:
    id: str
    name: str
    family: str  # "PDF" | "Image" | "Convert"
    icon: str  # emoji shown on the tile
    description: str
    run: RunFn
    accept: str = ""  # HTML file-input accept attribute
    multiple: bool = False  # accept more than one file
    requires_file: bool = True  # False for tools that need no upload (e.g. live-data lookups)
    options: list[Option] = field(default_factory=list)


REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    if tool.id in REGISTRY:
        raise ValueError(f"Duplicate tool id: {tool.id}")
    REGISTRY[tool.id] = tool
    return tool


def families() -> list[str]:
    """Distinct families in stable insertion order."""
    seen: list[str] = []
    for t in REGISTRY.values():
        if t.family not in seen:
            seen.append(t.family)
    return seen
