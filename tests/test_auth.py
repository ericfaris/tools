"""Tests for HTTP Basic Auth, CSRF, and failed-auth rate limiting."""
import pytest

from app import config

from .helpers import ORIGIN, make_pdf

CREDS = [("alice", "secret")]


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setattr(config, "AUTH_CREDENTIALS", CREDS)


def test_auth_disabled_allows_anonymous(client):
    # The autouse fixture leaves AUTH_CREDENTIALS empty.
    assert client.get("/").status_code == 200


def test_requires_auth_when_enabled(client, auth_on):
    r = client.get("/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")


def test_correct_credentials_allowed(client, auth_on):
    assert client.get("/", auth=("alice", "secret")).status_code == 200


def test_wrong_credentials_rejected(client, auth_on):
    assert client.get("/", auth=("alice", "nope")).status_code == 401
    assert client.get("/", auth=("mallory", "secret")).status_code == 401


@pytest.mark.parametrize("path", ["/health", "/static/styles.css", "/static/tool.js"])
def test_public_paths_bypass_auth(client, auth_on, path):
    assert client.get(path).status_code == 200


def test_protected_post_needs_both_auth_and_origin(client, auth_on):
    # Authenticated but no Origin -> still blocked by CSRF.
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("a.pdf", make_pdf(), "application/pdf"))],
        auth=("alice", "secret"),
    )
    assert r.status_code == 403

    # Authenticated and correct Origin -> allowed through.
    r = client.post(
        "/api/tools/pdf-merge",
        files=[
            ("files", ("a.pdf", make_pdf(), "application/pdf")),
            ("files", ("b.pdf", make_pdf(), "application/pdf")),
        ],
        auth=("alice", "secret"),
        headers=ORIGIN,
    )
    assert r.status_code == 200


def test_rate_limit_after_repeated_failures(client, auth_on):
    limit = config.RATE_LIMIT_MAX_FAILURES
    # Exhaust the allowance with wrong credentials.
    for _ in range(limit):
        assert client.get("/", auth=("alice", "wrong")).status_code == 401
    # The next attempt is rate-limited, even with correct credentials.
    assert client.get("/", auth=("alice", "secret")).status_code == 429
