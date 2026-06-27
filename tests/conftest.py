"""Pytest fixtures shared across the suite."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app import main as main_module
from app.main import app


@pytest.fixture(autouse=True)
def clean_state():
    """Each test starts with auth disabled and an empty rate-limit table.

    Tests that exercise auth opt back in by setting config.AUTH_CREDENTIALS
    themselves (via monkeypatch).
    """
    saved = config.AUTH_CREDENTIALS
    config.AUTH_CREDENTIALS = []
    main_module._failures.clear()
    try:
        yield
    finally:
        config.AUTH_CREDENTIALS = saved
        main_module._failures.clear()


@pytest.fixture
def client():
    return TestClient(app)
