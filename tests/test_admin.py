import os
import tempfile

from sqlalchemy import create_engine, inspect, text

from app.migrations import migrate
from tests.helpers import admin_client, user_client


def test_admin_seeded_from_env_and_clients_blocked():
    with admin_client() as adm:
        assert adm.get("/api/auth/me").json()["user"]["role"] == "admin"
    with user_client() as c:
        for path in ("/api/admin/summary", "/api/admin/users", "/api/admin/drafts", "/api/admin/uploads", "/api/admin/audit"):
            assert c.get(path).status_code == 403
    assert "test-only-admin-password" not in open("app/auth.py").read()


def test_admin_lists_views_downloads_deletes_and_audits():
    with user_client() as c, admin_client() as adm:
        d = c.post("/api/drafts", json={"service": "will", "answers": {"about_you": {"full_name": "Zed Client"}}}).json()
        up = c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("note.txt", b"old will text", "text/plain")}).json()
        users_ = adm.get("/api/admin/users").json()
        me = [u for u in users_ if u["email"] == c.email][0]
        assert me["drafts"] == 1
        drafts_ = adm.get(f"/api/admin/drafts?user_id={me['id']}").json()
        assert drafts_[0]["owner_email"] == c.email and drafts_[0]["uploads"] == 1
        view = adm.get(f"/api/admin/drafts/{d['id']}").json()
        assert view["answers"]["about_you"]["full_name"] == "Zed Client" and view["uploads"][0]["filename"] == "note.txt"
        assert adm.get(f"/api/admin/uploads/{up['id']}/download").content == b"old will text"
        assert any(u["id"] == up["id"] for u in adm.get("/api/admin/uploads").json())
        assert adm.delete(f"/api/admin/uploads/{up['id']}").status_code == 200
        assert c.get(f"/api/drafts/{d['id']}/uploads").json() == []
        assert adm.delete(f"/api/admin/drafts/{d['id']}").status_code == 200
        assert c.get(f"/api/drafts/{d['id']}").status_code == 404
        actions = [a["action"] for a in adm.get("/api/admin/audit?limit=50").json()]
        for a in ("admin_view_draft", "admin_download_upload", "admin_delete_upload", "admin_delete_draft", "upload_added", "draft_created"):
            assert a in actions
        # role changes; an admin can't demote themself
        assert adm.patch(f"/api/admin/users/{me['id']}", json={"role": "admin"}).status_code == 200
        own = adm.get("/api/auth/me").json()["user"]["id"]
        assert adm.patch(f"/api/admin/users/{own}", json={"role": "client"}).status_code == 400
        assert adm.delete(f"/api/admin/users/{me['id']}").status_code == 200
        assert c.get("/api/auth/me").json()["user"] is None


def test_migration_upgrades_old_schema_and_is_idempotent():
    path = os.path.join(tempfile.mkdtemp(), "old.db")
    eng = create_engine(f"sqlite:///{path}")
    with eng.begin() as conn:  # the table exactly as it exists on the live database today
        conn.execute(text("CREATE TABLE drafts (id VARCHAR(36) PRIMARY KEY, service VARCHAR(32) NOT NULL, client_name TEXT NOT NULL, client_email TEXT, "
                          "answers JSON NOT NULL, status VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"))
        conn.execute(text("INSERT INTO drafts VALUES ('old-1','will','Old Client',NULL,'{}','draft','2026-01-01','2026-01-01')"))
    assert migrate(eng) == [1, 2]
    assert migrate(eng) == []
    insp = inspect(eng)
    assert "user_id" in {c["name"] for c in insp.get_columns("drafts")}
    assert {"users", "sessions", "password_resets", "login_attempts", "audit_log", "uploads", "schema_migrations"} <= set(insp.get_table_names())
    with eng.connect() as conn:
        assert conn.execute(text("SELECT client_name, user_id FROM drafts")).all() == [("Old Client", None)]
