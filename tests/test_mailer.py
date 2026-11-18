"""Mailer delivery: Resend HTTPS when RESEND_API_KEY is set, SMTP as fallback."""
import httpx

from app import mailer


def _client_that_posts(handler):
    class _Client:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, headers=None, json=None):
            return handler(url, headers or {}, json or {}, self.kwargs)

    return _Client


def test_resend_preferred_when_api_key_set(monkeypatch):
    calls = {}

    def handler(url, headers, payload, kwargs):
        calls.update(url=url, headers=headers, payload=payload, kwargs=kwargs)
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"id": "test-email-id"}, request=request)

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_not_real")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    monkeypatch.setattr(mailer.httpx, "Client", _client_that_posts(handler))

    assert mailer.send("josh@signedandsorted.com", "Reset your Signed and Sorted password", "Open this link") == "resend"
    assert calls["url"] == "https://api.resend.com/emails"
    assert calls["headers"]["Authorization"] == "Bearer re_test_key_not_real"
    assert calls["payload"] == {
        "from": "josh@signedandsorted.com",
        "to": ["josh@signedandsorted.com"],
        "subject": "Reset your Signed and Sorted password",
        "text": "Open this link",
    }
    assert calls["kwargs"]["headers"]["User-Agent"] == "legal-doc-platform/1.0"


def test_resend_uses_mail_from_override(monkeypatch):
    calls = {}

    def handler(url, headers, payload, kwargs):
        calls["payload"] = payload
        return httpx.Response(200, json={"id": "x"}, request=httpx.Request("POST", url))

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_not_real")
    monkeypatch.setenv("MAIL_FROM", "Signed and Sorted <hello@signedandsorted.com>")
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setattr(mailer.httpx, "Client", _client_that_posts(handler))

    assert mailer.send("a@example.com", "Hi", "Body") == "resend"
    assert calls["payload"]["from"] == "Signed and Sorted <hello@signedandsorted.com>"


def test_resend_failure_falls_back_to_smtp(monkeypatch):
    def handler(url, headers, payload, kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(403, json={"name": "restricted"}, request=request)

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def starttls(self):
            sent["starttls"] = True

        def login(self, user, password):
            sent["login"] = user

        def send_message(self, msg):
            sent["from"] = msg["From"]
            sent["to"] = msg["To"]
            sent["subject"] = msg["Subject"]
            sent["body"] = msg.get_content()

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_not_real")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "josh@signedandsorted.com")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-password")
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    monkeypatch.setattr(mailer.httpx, "Client", _client_that_posts(handler))
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    assert mailer.send("to@example.com", "Subject", "Body text") == "smtp"
    assert sent["host"] == "smtp.example.com" and sent["port"] == 587 and sent["starttls"] is True
    assert sent["login"] == "josh@signedandsorted.com"
    assert sent["from"] == "josh@signedandsorted.com" and sent["to"] == "to@example.com"


def test_resend_failure_without_smtp_returns_none(monkeypatch):
    def handler(url, headers, payload, kwargs):
        return httpx.Response(500, json={"name": "application_error"}, request=httpx.Request("POST", url))

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_not_real")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    monkeypatch.setattr(mailer.httpx, "Client", _client_that_posts(handler))

    assert mailer.send("to@example.com", "Subject", "Body") == "none"


def test_smtp_used_when_no_resend_key(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def starttls(self):
            pass

        def send_message(self, msg):
            sent["to"] = msg["To"]

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    assert mailer.send("to@example.com", "Subject", "Body") == "smtp"
    assert sent == {"host": "smtp.example.com", "to": "to@example.com"}


def test_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("MAIL_BACKEND", raising=False)
    assert mailer.send("to@example.com", "Subject", "Body") == "none"


def test_memory_backend_still_wins(monkeypatch):
    mailer.OUTBOX.clear()
    monkeypatch.setenv("MAIL_BACKEND", "memory")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key_not_real")

    def fail(*args, **kwargs):
        raise AssertionError("Resend should not be called when MAIL_BACKEND=memory")

    monkeypatch.setattr(mailer.httpx, "Client", fail)
    assert mailer.send("to@example.com", "Subject", "Body") == "memory"
    assert mailer.OUTBOX == [{"to": "to@example.com", "subject": "Subject", "body": "Body"}]
