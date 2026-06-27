"""Regression tests for the platform's privacy / ephemerality guarantees.

These lock in the promises that (a) nothing about a request is cached, logged,
or retained, and (b) every uploaded file is closed/cleaned the instant the
request finishes — even when the tool fails.
"""
import starlette.datastructures as ds

from app import config
from app import main as main_module

from .helpers import ORIGIN, make_image, make_pdf


def test_responses_are_never_cached(client):
    r = client.get("/")
    assert r.headers["cache-control"] == "no-store, max-age=0"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "content-security-policy" in r.headers


def test_downloads_are_never_cached(client):
    r = client.post(
        "/api/tools/pdf-merge",
        files=[
            ("files", ("a.pdf", make_pdf(), "application/pdf")),
            ("files", ("b.pdf", make_pdf(), "application/pdf")),
        ],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store, max-age=0"
    assert "attachment" in r.headers["content-disposition"]


def _count_closes(monkeypatch):
    """Patch UploadFile.close to count how many times it's invoked."""
    calls = {"n": 0}
    original = ds.UploadFile.close

    async def counting_close(self):
        calls["n"] += 1
        return await original(self)

    monkeypatch.setattr(ds.UploadFile, "close", counting_close)
    return calls


def test_uploads_are_closed_after_success(client, monkeypatch):
    calls = _count_closes(monkeypatch)
    r = client.post(
        "/api/tools/images-to-pdf",
        files=[
            ("files", ("1.png", make_image("PNG"), "image/png")),
            ("files", ("2.png", make_image("PNG"), "image/png")),
        ],
        headers=ORIGIN,
    )
    assert r.status_code == 200
    assert calls["n"] == 2  # both uploads explicitly closed


def test_uploads_are_closed_even_on_failure(client, monkeypatch):
    calls = _count_closes(monkeypatch)
    r = client.post(
        "/api/tools/pdf-merge",
        files=[("files", ("bad.txt", b"not a pdf", "text/plain"))],
        headers=ORIGIN,
    )
    assert r.status_code == 422
    assert calls["n"] == 1  # cleanup still ran on the error path


def test_security_headers_present_on_401(client, monkeypatch):
    monkeypatch.setattr(config, "AUTH_CREDENTIALS", [("alice", "secret")])
    r = client.get("/")  # rejected -> 401, but still hardened
    assert r.status_code == 401
    assert r.headers["cache-control"] == "no-store, max-age=0"
    assert "content-security-policy" in r.headers
    assert r.headers["referrer-policy"] == "no-referrer"


def test_security_headers_present_on_csrf_403(client):
    r = client.post(  # no Origin/Referer -> 403
        "/api/tools/pdf-merge",
        files=[("files", ("a.pdf", make_pdf(), "application/pdf"))],
    )
    assert r.status_code == 403
    assert r.headers["cache-control"] == "no-store, max-age=0"
    assert "content-security-policy" in r.headers


def test_no_application_logger_exists():
    # We deliberately keep no module-level logger that could record activity.
    assert not hasattr(main_module, "logger")


def test_access_logging_off_by_default():
    assert config.ACCESS_LOG is False
