"""Outgoing email for password resets. Prefers Resend's HTTPS API when
RESEND_API_KEY is set (Render's free plan blocks SMTP ports). Falls back to SMTP
when SMTP_HOST is set. Otherwise the message is not sent. In development
(MAIL_BACKEND=log) the reset link is written to the log; in tests
(MAIL_BACKEND=memory) it is kept in OUTBOX. Production default never logs links."""
import logging
import os
import smtplib
from email.message import EmailMessage

import httpx

log = logging.getLogger("legal-doc")
OUTBOX: list[dict] = []
RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "josh@signedandsorted.com"
USER_AGENT = "legal-doc-platform/1.0"


def _mail_from() -> str:
    return os.getenv("MAIL_FROM", DEFAULT_FROM)


def _send_resend(to: str, subject: str, body: str) -> None:
    key = os.environ["RESEND_API_KEY"]
    with httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
        response = client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"from": _mail_from(), "to": [to], "subject": subject, "text": body},
        )
        response.raise_for_status()


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = _mail_from()
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=20) as s:
        s.starttls()
        if os.getenv("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)


def _error_label(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, OSError) and exc.errno is not None:
        return f"{type(exc).__name__} errno {exc.errno}"
    return type(exc).__name__


def send(to: str, subject: str, body: str) -> str:
    backend = os.getenv("MAIL_BACKEND")
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body})
        return "memory"
    if backend == "log":
        log.warning("MAIL_BACKEND=log (development only) to=%s subject=%s body=%s", to, subject, body)
        return "log"
    if os.getenv("RESEND_API_KEY"):
        try:
            _send_resend(to, subject, body)
            return "resend"
        except Exception as exc:
            smtp_ready = bool(os.getenv("SMTP_HOST"))
            log.warning(
                "Resend send failed (%s); %s",
                _error_label(exc),
                "falling back to SMTP" if smtp_ready else "no SMTP fallback configured",
            )
            if smtp_ready:
                _send_smtp(to, subject, body)
                return "smtp"
            return "none"
    if os.getenv("SMTP_HOST"):
        _send_smtp(to, subject, body)
        return "smtp"
    log.warning("Password reset requested but no email is configured (set RESEND_API_KEY or SMTP_HOST). Nothing was sent.")
    return "none"
