import re
import uuid

from sqlalchemy import select

from app.db import engine, sessions, users
from app.mailer import OUTBOX
from tests.helpers import PASSWORD, anon_client, csrf, reset_limits, user_client


def test_register_hashes_password_and_sets_secure_cookie_flags():
    with user_client() as c:
        me = c.get("/api/auth/me").json()["user"]
        assert me["email"] == c.email and me["role"] == "client"
        with engine().connect() as conn:
            stored = conn.execute(select(users.c.password_hash).where(users.c.email == c.email)).scalar_one()
            tokens = [r[0] for r in conn.execute(select(sessions.c.token_hash).where(sessions.c.user_id == me["id"]))]
        assert stored.startswith("$argon2id$") and PASSWORD not in stored
        assert c.cookies.get("sas_session") not in tokens and len(tokens[0]) == 64  # only the hash is stored
    with anon_client() as c:
        reset_limits()
        r = c.post("/api/auth/register", json={"email": f"x{uuid.uuid4().hex[:6]}@example.com", "password": PASSWORD})
        cookie = [h for h in r.headers.get_list("set-cookie") if h.startswith("sas_session=")][0].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie
        csrf(c)
        assert c.post("/api/auth/register", json={"email": "bad", "password": PASSWORD}).status_code == 400
        assert c.post("/api/auth/register", json={"email": "short@example.com", "password": "short"}).status_code == 400


def test_drafts_need_login_and_belong_to_owner():
    with anon_client() as anon:
        assert anon.post("/api/drafts", json={"service": "will", "answers": {}}).status_code == 401
        with user_client() as a, user_client() as b:
            d = a.post("/api/drafts", json={"service": "will", "answers": {}}).json()
            a.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("n.txt", b"hello", "text/plain")})
            up = a.get(f"/api/drafts/{d['id']}/uploads").json()[0]
            # the reference number alone is not enough any more
            assert anon.get(f"/api/drafts/{d['id']}").status_code == 401
            for path in (f"/api/drafts/{d['id']}", f"/api/drafts/{d['id']}/pdf", f"/api/drafts/{d['id']}/uploads", f"/api/drafts/{d['id']}/uploads/{up['id']}"):
                assert b.get(path).status_code == 404, path
            assert b.put(f"/api/drafts/{d['id']}", json={"answers": {}}).status_code == 404
            assert b.delete(f"/api/drafts/{d['id']}/uploads/{up['id']}").status_code == 404
            assert [x["id"] for x in a.get("/api/drafts").json()] == [d["id"]]
            assert b.get("/api/drafts").json() == []
            assert a.get(f"/api/drafts/{d['id']}/uploads/{up['id']}").content == b"hello"


def test_csrf_required_on_unsafe_requests():
    with user_client() as c:
        token = c.headers.pop("X-CSRF-Token")
        assert c.post("/api/drafts", json={"service": "will", "answers": {}}).status_code == 403
        assert c.post("/api/drafts", json={"service": "will", "answers": {}}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
        assert c.post("/api/drafts", json={"service": "will", "answers": {}}, headers={"X-CSRF-Token": token, "Origin": "https://evil.example"}).status_code == 403
        assert c.post("/api/drafts", json={"service": "will", "answers": {}}, headers={"X-CSRF-Token": token, "Origin": "http://testserver"}).status_code == 200


def test_login_logout_and_rate_limit():
    with user_client() as c:
        email = c.email
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/auth/me").json()["user"] is None
        for _ in range(5):
            assert c.post("/api/auth/login", json={"email": email, "password": "wrong password!"}).status_code == 401
        # even the right password is refused while locked
        assert c.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 429
        reset_limits()
        assert c.post("/api/auth/login", json={"email": email.upper(), "password": PASSWORD}).status_code == 200
        csrf(c)  # the CSRF token rotates at sign-in
        assert c.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}).status_code == 401


def test_password_reset_flow():
    with user_client() as c:
        email = c.email
        OUTBOX.clear()
        r = c.post("/api/auth/reset-request", json={"email": email}).json()
        assert r["ok"] and len(OUTBOX) == 1 and OUTBOX[0]["to"] == email
        assert c.post("/api/auth/reset-request", json={"email": "nobody@example.com"}).json() == r  # same reply either way
        token = re.search(r"#/reset/(\S+)", OUTBOX[0]["body"]).group(1)
        assert c.post("/api/auth/reset", json={"token": "nope", "password": "a brand new password"}).status_code == 400
        assert c.post("/api/auth/reset", json={"token": token, "password": "a brand new password"}).status_code == 200
        csrf(c)
        assert c.post("/api/auth/reset", json={"token": token, "password": "another new password"}).status_code == 400  # single use
        reset_limits()
        assert c.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 401
        assert c.post("/api/auth/login", json={"email": email, "password": "a brand new password"}).status_code == 200


def test_cookies_are_secure_by_default(monkeypatch):
    from app.security import cookie_secure
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    assert cookie_secure() is True
    monkeypatch.setenv("COOKIE_SECURE", "0")
    assert cookie_secure() is False
