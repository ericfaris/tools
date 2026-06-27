"""Tests for the tool registry's invariants."""
import pytest

from app.tools import REGISTRY, Tool, families, register

EXPECTED_IDS = {
    "pdf-merge", "pdf-split", "image-convert", "images-to-pdf",
    "favicon", "color-palette",
}


def test_all_expected_tools_registered():
    assert EXPECTED_IDS <= set(REGISTRY)


def test_registry_key_matches_tool_id():
    for key, tool in REGISTRY.items():
        assert key == tool.id


def test_every_tool_is_well_formed():
    for tool in REGISTRY.values():
        assert tool.id and isinstance(tool.id, str)
        assert tool.name
        assert tool.family
        assert tool.icon
        assert tool.description
        assert callable(tool.run)
        for opt in tool.options:
            assert opt.name and opt.label and opt.type


def test_families_are_unique_and_cover_all_tools():
    fams = families()
    assert len(fams) == len(set(fams))
    assert {t.family for t in REGISTRY.values()} == set(fams)


def test_register_rejects_duplicate_id():
    existing = next(iter(REGISTRY.values()))
    with pytest.raises(ValueError):
        register(Tool(
            id=existing.id, name="dup", family="X", icon="x",
            description="dup", run=lambda files, opts: None,
        ))
