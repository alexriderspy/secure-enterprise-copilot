"""Secrets never show up in reprs or logs."""
import logging

from app.logsafe import RedactingFilter
from kb.config import Secret, secret


def test_secret_repr_is_masked():
    s = Secret("sk-live-abc")
    assert "abc" not in repr(s) and "abc" not in str(s) and "abc" not in f"{s}" and s.get() == "sk-live-abc"


def test_secret_from_file(tmp_path, monkeypatch):
    f = tmp_path / "key"
    f.write_text("from-a-file\n")
    monkeypatch.setenv("SOME_KEY_FILE", str(f))
    assert secret("SOME_KEY").get() == "from-a-file"


def test_login_codes_and_tokens_are_masked_in_access_logs():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("127.0.0.1:5", "GET", "/callback?state=abc&code=SECRETCODE", "1.1", 307), None)
    RedactingFilter().filter(rec)
    assert "SECRETCODE" not in rec.getMessage() and "code=***" in rec.getMessage()
