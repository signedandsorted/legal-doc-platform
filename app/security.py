"""Passwords (argon2id), opaque session tokens stored hashed, CSRF double-submit, DB-backed rate limits, audit log."""
import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request
from sqlalchemy import delete, func, insert, select

from .db import audit_log, engine, login_attempts, now

log = logging.getLogger("legal-doc")
_ph = PasswordHasher()  # argon2id with library defaults
SESSION_COOKIE = "sas_session"
CSRF_COOKIE = "sas_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_DAYS = 14
RESET_MINUTES = 60
MIN_PASSWORD = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# (bucket prefix, max events, window minutes)
LIMITS = {"login_email": (5, 15), "login_ip": (20, 15), "register_ip": (10, 60), "reset_ip": (10, 60), "reset_email": (3, 60)}


def cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "1") != "0"


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(stored: str, pw: str) -> bool:
    try:
        return _ph.verify(stored, pw)
    except (VerificationError, InvalidHashError):
        return False


_DUMMY = None


def dummy_verify(pw: str) -> None:
    """Spend the same time when the email is unknown, so timing does not reveal accounts."""
    global _DUMMY
    _DUMMY = _DUMMY or _ph.hash("not-a-real-password")
    verify_password(_DUMMY, pw)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_password_rules(pw: str, email: str = "") -> None:
    if len(pw or "") < MIN_PASSWORD:
        raise HTTPException(400, f"Use a password of at least {MIN_PASSWORD} characters")
    if email and pw.lower() == email.lower():
        raise HTTPException(400, "Your password must not be your email address")


def normalise_email(email: str) -> str:
    e = (email or "").strip().lower()
    if not EMAIL_RE.match(e) or len(e) > 254:
        raise HTTPException(400, "Enter a valid email address")
    return e


def client_ip(request: Request) -> str:
    # Render puts the client address first in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")) or "unknown"


def rate_limited(kind: str, key: str) -> bool:
    limit, minutes = LIMITS[kind]
    bucket = f"{kind}:{key}"[:300]
    since = now() - timedelta(minutes=minutes)
    with engine().connect() as conn:
        n = conn.execute(select(func.count()).select_from(login_attempts).where(login_attempts.c.bucket == bucket, login_attempts.c.at >= since)).scalar_one()
    return n >= limit


def record_attempt(kind: str, key: str) -> None:
    with engine().begin() as conn:
        conn.execute(insert(login_attempts).values(bucket=f"{kind}:{key}"[:300], at=now()))
        conn.execute(delete(login_attempts).where(login_attempts.c.at < now() - timedelta(days=1)))


def clear_attempts(kind: str, key: str) -> None:
    with engine().begin() as conn:
        conn.execute(delete(login_attempts).where(login_attempts.c.bucket == f"{kind}:{key}"[:300]))


def audit(action: str, actor: dict | None = None, target_type: str | None = None, target_id: str | None = None, detail: dict | None = None, ip: str | None = None) -> None:
    with engine().begin() as conn:
        conn.execute(insert(audit_log).values(at=now(), actor_id=(actor or {}).get("id"), actor_email=(actor or {}).get("email"), action=action,
                                              target_type=target_type, target_id=target_id, detail=detail or {}, ip=ip))


def csrf_ok(request: Request) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        return False
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("host", "")
        if origin.split("://", 1)[-1] != host:
            return False
    return True
