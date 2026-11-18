"""Small, ordered, idempotent schema migrations. Safe on the existing Render Postgres
(legal-doc-db, which already has `drafts` and possibly `uploads`) and on SQLite in tests.
Each step is recorded in `schema_migrations` and never runs twice. Only additive changes."""
from sqlalchemy import Index, inspect, text

from .db import audit_log, capacity_statements, drafts, login_attempts, now, password_resets, schema_migrations, sessions, uploads, users


def _create(conn, *tables):
    for t in tables:
        t.create(conn, checkfirst=True)


def m1_base(conn):
    """drafts and uploads (as on main and the overhaul branch before logins)."""
    if not inspect(conn).has_table("drafts"):
        # Create drafts without user_id first, exactly as the live table looks; migration 2 adds the column.
        conn.execute(text("CREATE TABLE drafts (id VARCHAR(36) PRIMARY KEY, service VARCHAR(32) NOT NULL, client_name TEXT NOT NULL, client_email TEXT, "
                          "answers JSON NOT NULL, status VARCHAR(32) NOT NULL, created_at TIMESTAMP WITH TIME ZONE NOT NULL, updated_at TIMESTAMP WITH TIME ZONE NOT NULL)"))
    _create(conn, uploads)


def m2_accounts(conn):
    """Users, sessions, password resets, rate-limit log, audit log; drafts.user_id."""
    _create(conn, users, sessions, password_resets, login_attempts, audit_log)
    cols = {c["name"] for c in inspect(conn).get_columns("drafts")}
    if "user_id" not in cols:
        conn.execute(text("ALTER TABLE drafts ADD COLUMN user_id VARCHAR(36)"))
    idx = {i["name"] for i in inspect(conn).get_indexes("drafts")}
    if "ix_drafts_user_id" not in idx:
        Index("ix_drafts_user_id", drafts.c.user_id).create(conn)


def m3_capacity_statements(conn):
    """Encrypted supporting video statements for a will or LPA."""
    _create(conn, capacity_statements)


MIGRATIONS = [
    (1, "base drafts and uploads", m1_base),
    (2, "accounts, sessions, audit log, drafts.user_id", m2_accounts),
    (3, "capacity video statements", m3_capacity_statements),
]


def migrate(engine) -> list[int]:
    applied_now = []
    with engine.begin() as conn:
        schema_migrations.create(conn, checkfirst=True)
        done = {r[0] for r in conn.execute(schema_migrations.select().with_only_columns(schema_migrations.c.version))}
    for version, name, fn in MIGRATIONS:
        if version in done:
            continue
        with engine.begin() as conn:
            fn(conn)
            conn.execute(schema_migrations.insert().values(version=version, name=name, applied_at=now()))
        applied_now.append(version)
    return applied_now
