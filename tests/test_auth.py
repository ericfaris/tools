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


def test_successful_auth_clears_failure_history(client, auth_on):
    limit = config.RATE_LIMIT_MAX_FAILURES
    for _ in range(limit - 1):
        assert client.get("/", auth=("alice", "wrong")).status_code == 401
    # A success resets the counter to zero...
    assert client.get("/", auth=("alice", "secret")).status_code == 200
    # ...so another (limit - 1) failures still don't trip the limiter.
    for _ in range(limit - 1):
        assert client.get("/", auth=("alice", "wrong")).status_code == 401


def test_csrf_rejects_lookalike_origin(client):
    # Auth is disabled here, so only the CSRF check can block this POST.
    # Origin merely *contains* the host ("testserver") but is a different site.
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("a.pdf", make_pdf(), "application/pdf"))],
        headers={"Origin": "http://testserver.evil.com"},
    )
    assert r.status_code == 403


def test_csrf_accepts_matching_referer(client):
    r = client.post(
        "/api/tools/pdf-merge",
        files=[
            ("files", ("a.pdf", make_pdf(), "application/pdf")),
            ("files", ("b.pdf", make_pdf(), "application/pdf")),
        ],
        headers={"Referer": "http://testserver/tools/pdf-merge"},
    )
    assert r.status_code == 200


def test_rate_limit_uses_forwarded_ip_behind_trusted_proxy(client, auth_on, monkeypatch):
    # The TestClient's direct peer is "testclient"; treat it as a trusted proxy.
    monkeypatch.setattr(config, "TRUSTED_PROXIES", {"testclient"})
    limit = config.RATE_LIMIT_MAX_FAILURES

    for _ in range(limit):
        r = client.get("/", auth=("alice", "wrong"), headers={"CF-Connecting-IP": "1.1.1.1"})
        assert r.status_code == 401
    # That forwarded IP is now limited (even correct creds get 429)...
    assert client.get("/", auth=("alice", "secret"),
                      headers={"CF-Connecting-IP": "1.1.1.1"}).status_code == 429
    # ...but a different forwarded IP has its own, untouched bucket.
    assert client.get("/", auth=("alice", "wrong"),
                      headers={"CF-Connecting-IP": "2.2.2.2"}).status_code == 401


def test_forwarded_ip_ignored_from_untrusted_peer(client, auth_on, monkeypatch):
    # With no trusted proxies, a spoofed CF-Connecting-IP must NOT shard buckets:
    # all attempts count against the real peer, so the limiter still trips.
    monkeypatch.setattr(config, "TRUSTED_PROXIES", set())
    limit = config.RATE_LIMIT_MAX_FAILURES
    for i in range(limit):
        r = client.get("/", auth=("alice", "wrong"), headers={"CF-Connecting-IP": f"9.9.9.{i}"})
        assert r.status_code == 401
    assert client.get("/", auth=("alice", "wrong"),
                      headers={"CF-Connecting-IP": "9.9.9.250"}).status_code == 429
