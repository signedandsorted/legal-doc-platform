"""Outgoing email for password resets. Uses SMTP only if SMTP_HOST is set; otherwise the
message is not sent. In development (MAIL_BACKEND=log) the reset link is written to the log;
in tests (MAIL_BACKEND=memory) it is kept in OUTBOX. Production default never logs links."""
import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger("legal-doc")
OUTBOX: list[dict] = []


def send(to: str, subject: str, body: str) -> str:
    backend = os.getenv("MAIL_BACKEND", "smtp" if os.getenv("SMTP_HOST") else "none")
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body})
        return "memory"
    if backend == "log":
        log.warning("MAIL_BACKEND=log (development only) to=%s subject=%s body=%s", to, subject, body)
        return "log"
    if backend == "smtp" and os.getenv("SMTP_HOST"):
        msg = EmailMessage()
        msg["From"] = os.getenv("MAIL_FROM", "no-reply@signedandsorted.com")
        msg["To"], msg["Subject"] = to, subject
        msg.set_content(body)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=20) as s:
            s.starttls()
            if os.getenv("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            s.send_message(msg)
        return "smtp"
    log.warning("Password reset requested but no email is configured (set SMTP_HOST). Nothing was sent.")
    return "none"
