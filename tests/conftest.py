import os

if "DATABASE_URL" not in os.environ:
    # Start each local run from an empty SQLite file: some firm-wide totals are
    # asserted exactly, so rows left by an earlier run would make them fail.
    for leftover in ("test.db", "test.db-journal", "test.db-wal", "test.db-shm"):
        if os.path.exists(leftover):
            os.remove(leftover)
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["COOKIE_SECURE"] = "0"  # TestClient talks plain http
os.environ["MAIL_BACKEND"] = "memory"
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "test-only-admin-password")

os.environ.setdefault("STATEMENT_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
