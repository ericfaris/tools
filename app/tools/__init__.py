"""Importing this package registers all built-in tools into the REGISTRY."""
from . import bingo_tools, image_tools, pdf_tools  # noqa: F401  (side-effect: registration)
from .base import REGISTRY, JsonResult, Option, Result, Tool, families, register

__all__ = ["REGISTRY", "JsonResult", "Option", "Result", "Tool", "families", "register"]
