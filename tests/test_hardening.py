"""Unit tests for the security-hardening helpers in app.main."""
import time

from app import config
from app import main as main_module
from app.main import _csrf_ok, _is_rate_limited, _record_failure, _safe_filename


def test_safe_filename_strips_path_and_dangerous_chars():
    assert _safe_filename('e"vil.zip') == "evil.zip"
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("a\r\nb.pdf") == "ab.pdf"
    assert _safe_filename("normal-name.pdf") == "normal-name.pdf"


def test_safe_filename_strips_angle_brackets_and_controls():
    # Angle brackets and control chars are dropped so the name can't inject into
    # the Content-Disposition header or the DOM when echoed back to the user.
    assert _safe_filename("<img src=x onerror=alert(1)>.png") == "img src=x onerror=alert(1).png"
    assert _safe_filename("a\x00\x07b\tc.txt") == "abc.txt"


def test_safe_filename_falls_back_when_empty():
    assert _safe_filename('"') == "download"
    assert _safe_filename("") == "download"
    assert _safe_filename("<>") == "download"


def test_rate_limit_table_is_bounded(monkeypatch):
    # Once the table is full, recording a failure for a new IP sweeps buckets
    # whose entries have all aged out, instead of growing without bound.
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_TRACKED_IPS", 5)
    main_module._failures.clear()
    stale = time.time() - (config.RATE_LIMIT_WINDOW_SECONDS + 100)
    for i in range(5):
        main_module._failures[f"10.0.0.{i}"] = [stale]  # all aged out
    try:
        _record_failure("203.0.113.7")  # new IP, table at capacity
        # Stale buckets were reclaimed; the table didn't blow past the cap.
        assert "203.0.113.7" in main_module._failures
        assert len(main_module._failures) <= config.RATE_LIMIT_MAX_TRACKED_IPS
    finally:
        main_module._failures.clear()


def test_rate_limit_table_drops_empty_buckets():
    # A bucket whose only entry is outside the window must be pruned, not kept.
    stale = time.time() - (main_module.config.RATE_LIMIT_WINDOW_SECONDS + 100)
    main_module._failures["9.9.9.9"] = [stale]
    try:
        assert _is_rate_limited("9.9.9.9") is False
        assert "9.9.9.9" not in main_module._failures
    finally:
        main_module._failures.pop("9.9.9.9", None)


class _FakeRequest:
    def __init__(self, headers):
        self.headers = headers


def test_csrf_exact_host_match():
    host = "tools.example.com"
    assert _csrf_ok(_FakeRequest({"origin": f"https://{host}", "host": host})) is True
    # Look-alike that merely contains the host as a substring is rejected.
    assert _csrf_ok(_FakeRequest({"origin": f"https://{host}.evil.com", "host": host})) is False
    assert _csrf_ok(_FakeRequest({"referer": f"https://evil.com/?{host}", "host": host})) is False
    # Missing Origin/Referer is rejected.
    assert _csrf_ok(_FakeRequest({"host": host})) is False
