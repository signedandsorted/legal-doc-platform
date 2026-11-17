import uuid
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import engine, login_attempts
from app.main import app

PASSWORD = "correct horse battery"


def reset_limits():
    with engine().begin() as conn:
        conn.execute(delete(login_attempts))


def csrf(c):
    c.headers["X-CSRF-Token"] = c.cookies.get("sas_csrf")


@contextmanager
def anon_client():
    with TestClient(app) as c:
        c.get("/api/auth/me")
        csrf(c)
        yield c


@contextmanager
def user_client(email: str | None = None, password: str = PASSWORD):
    with anon_client() as c:
        reset_limits()
        email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
        r = c.post("/api/auth/register", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        csrf(c)
        c.email = email
        yield c


@contextmanager
def admin_client():
    with anon_client() as c:
        reset_limits()
        r = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "test-only-admin-password"})
        assert r.status_code == 200, r.text
        csrf(c)
        yield c
