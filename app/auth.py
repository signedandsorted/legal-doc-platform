"""Client accounts: register, sign in/out, password reset. Session = random token in an
HttpOnly, SameSite=Lax, Secure cookie; only its SHA-256 is stored in the database."""
import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update

from .db import engine, new_id, now, password_resets, sessions, users, utc
from .mailer import send
from .retainer import clean_retainer, effect
from .security import (CSRF_COOKIE, RESET_MINUTES, SESSION_COOKIE, SESSION_DAYS, audit, check_password_rules, clear_attempts, client_ip, cookie_secure,
                       dummy_verify, hash_password, new_token, normalise_email, rate_limited, record_attempt, token_hash, verify_password)

log = logging.getLogger("legal-doc")
router = APIRouter(prefix="/api/auth")


class Credentials(BaseModel):
    email: str
    password: str


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    password: str


def public(u) -> dict:
    record = clean_retainer(u.get("retainer") or {})
    return {
        "id": u["id"], "email": u["email"], "role": u["role"],
        "retainer": {**record, "effect": effect(record, "will") if record["signed"] else ""},
    }


def set_csrf_cookie(response: Response, request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE) or new_token()
    response.set_cookie(CSRF_COOKIE, token, httponly=False, secure=cookie_secure(), samesite="strict", max_age=SESSION_DAYS * 86400, path="/")
    return token


def _start_session(response: Response, request: Request, user_id: str) -> None:
    token = new_token()
    with engine().begin() as conn:
        conn.execute(insert(sessions).values(token_hash=token_hash(token), user_id=user_id, created_at=now(), expires_at=now() + timedelta(days=SESSION_DAYS), ip=client_ip(request)))
        conn.execute(update(users).where(users.c.id == user_id).values(last_login_at=now()))
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=cookie_secure(), samesite="lax", max_age=SESSION_DAYS * 86400, path="/")
    # rotate the CSRF token at sign-in
    response.set_cookie(CSRF_COOKIE, new_token(), httponly=False, secure=cookie_secure(), samesite="strict", max_age=SESSION_DAYS * 86400, path="/")


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with engine().connect() as conn:
        row = conn.execute(select(users, sessions.c.expires_at).join(sessions, sessions.c.user_id == users.c.id).where(sessions.c.token_hash == token_hash(token))).mappings().first()
    if not row or utc(row["expires_at"]) < now():
        return None
    return dict(row)


def require_user(request: Request) -> dict:
    u = current_user(request)
    if not u:
        raise HTTPException(401, "Please sign in")
    return u


def require_staff(request: Request) -> dict:
    u = require_user(request)
    if u["role"] not in ("staff", "admin"):
        raise HTTPException(403, "This desk is for firm staff")
    return u


def seed_staff() -> None:
    """Optional firm login from STAFF_EMAIL + STAFF_INITIAL_PASSWORD. Never demotes an admin."""
    email, pw = os.getenv("STAFF_EMAIL", "").strip().lower(), os.getenv("STAFF_INITIAL_PASSWORD", "")
    if not email:
        return
    with engine().begin() as conn:
        u = conn.execute(select(users).where(users.c.email == email)).mappings().first()
        if u:
            if u["role"] == "client":
                conn.execute(update(users).where(users.c.id == u["id"]).values(role="staff"))
            return
        if len(pw) < 12:
            log.warning("STAFF_EMAIL is set but STAFF_INITIAL_PASSWORD is missing or under 12 characters; no staff account created.")
            return
        conn.execute(insert(users).values(id=new_id(), email=email, password_hash=hash_password(pw), role="staff", created_at=now()))
    audit("staff_seeded", None, "user", None, {"email": email})


def require_admin(request: Request) -> dict:
    u = require_user(request)
    if u["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return u


@router.get("/me")
def me(request: Request, response: Response):
    set_csrf_cookie(response, request)
    u = current_user(request)
    return {"user": public(u) if u else None}


@router.post("/register")
def register(body: Credentials, request: Request, response: Response):
    ip = client_ip(request)
    if rate_limited("register_ip", ip):
        raise HTTPException(429, "Too many attempts. Please try again later.")
    record_attempt("register_ip", ip)
    email = normalise_email(body.email)
    check_password_rules(body.password, email)
    with engine().begin() as conn:
        if conn.execute(select(users.c.id).where(users.c.email == email)).first():
            raise HTTPException(409, "An account with that email already exists. Sign in or reset your password.")
        uid = new_id()
        conn.execute(insert(users).values(id=uid, email=email, password_hash=hash_password(body.password), role="client", created_at=now()))
    audit("register", {"id": uid, "email": email}, "user", uid, ip=ip)
    _start_session(response, request, uid)
    return {"user": {"id": uid, "email": email, "role": "client"}}


@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    ip = client_ip(request)
    email = (body.email or "").strip().lower()
    if rate_limited("login_ip", ip) or rate_limited("login_email", email):
        audit("login_rate_limited", None, "user", None, {"email": email}, ip)
        raise HTTPException(429, "Too many sign-in attempts. Please wait 15 minutes or reset your password.")
    with engine().connect() as conn:
        u = conn.execute(select(users).where(users.c.email == email)).mappings().first()
    if not u:
        dummy_verify(body.password or "")
    if not u or not verify_password(u["password_hash"], body.password or ""):
        record_attempt("login_ip", ip)
        record_attempt("login_email", email)
        audit("login_failed", None, "user", u["id"] if u else None, {"email": email}, ip)
        raise HTTPException(401, "Email or password is not right")
    clear_attempts("login_email", email)
    _start_session(response, request, u["id"])
    audit("login", public(u), "user", u["id"], ip=ip)
    return {"user": public(u)}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with engine().begin() as conn:
            conn.execute(delete(sessions).where(sessions.c.token_hash == token_hash(token)))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


def base_url(request: Request) -> str:
    return os.getenv("APP_BASE_URL", str(request.base_url)).rstrip("/")


@router.post("/reset-request")
def reset_request(body: ResetRequest, request: Request):
    ip = client_ip(request)
    email = (body.email or "").strip().lower()
    generic = {"ok": True, "message": "If that email has an account, we've sent a link to reset the password. It works for 60 minutes."}
    if rate_limited("reset_ip", ip) or rate_limited("reset_email", email):
        return generic
    record_attempt("reset_ip", ip)
    record_attempt("reset_email", email)
    with engine().connect() as conn:
        u = conn.execute(select(users).where(users.c.email == email)).mappings().first()
    if u:
        token = new_token()
        with engine().begin() as conn:
            conn.execute(insert(password_resets).values(token_hash=token_hash(token), user_id=u["id"], created_at=now(), expires_at=now() + timedelta(minutes=RESET_MINUTES), used=False))
        link = f"{base_url(request)}/#/reset/{token}"
        how = send(u["email"], "Reset your Signed and Sorted password",
                   f"Someone asked to reset the password for this account.\n\nTo choose a new password, open this link within {RESET_MINUTES} minutes:\n{link}\n\nIf this wasn't you, ignore this email.")
        audit("password_reset_requested", public(u), "user", u["id"], {"delivery": how}, ip)
    return generic


@router.post("/reset")
def reset(body: ResetConfirm, request: Request, response: Response):
    th = token_hash(body.token or "")
    with engine().connect() as conn:
        r = conn.execute(select(password_resets).where(password_resets.c.token_hash == th)).mappings().first()
    if not r or r["used"] or utc(r["expires_at"]) < now():
        raise HTTPException(400, "This reset link has expired or been used. Please ask for a new one.")
    with engine().connect() as conn:
        u = conn.execute(select(users).where(users.c.id == r["user_id"])).mappings().first()
    check_password_rules(body.password, u["email"])
    with engine().begin() as conn:
        conn.execute(update(users).where(users.c.id == u["id"]).values(password_hash=hash_password(body.password)))
        conn.execute(update(password_resets).where(password_resets.c.user_id == u["id"]).values(used=True))
        conn.execute(delete(sessions).where(sessions.c.user_id == u["id"]))  # sign out everywhere
    clear_attempts("login_email", u["email"])
    audit("password_reset", public(u), "user", u["id"], ip=client_ip(request))
    _start_session(response, request, u["id"])
    return {"user": public(u)}


def seed_admin() -> None:
    """Create the first admin from ADMIN_EMAIL + ADMIN_INITIAL_PASSWORD (env only; never hard-coded).
    If the account exists it is made an admin, and its password is left alone."""
    email, pw = os.getenv("ADMIN_EMAIL", "").strip().lower(), os.getenv("ADMIN_INITIAL_PASSWORD", "")
    if not email:
        return
    with engine().begin() as conn:
        u = conn.execute(select(users).where(users.c.email == email)).mappings().first()
        if u:
            if u["role"] != "admin":
                conn.execute(update(users).where(users.c.id == u["id"]).values(role="admin"))
            return
        if len(pw) < 12:
            log.warning("ADMIN_EMAIL is set but ADMIN_INITIAL_PASSWORD is missing or under 12 characters; no admin created.")
            return
        conn.execute(insert(users).values(id=new_id(), email=email, password_hash=hash_password(pw), role="admin", created_at=now()))
    audit("admin_seeded", None, "user", None, {"email": email})


__all__ = ["router", "current_user", "require_user", "require_admin", "require_staff", "seed_admin", "seed_staff", "Depends"]
