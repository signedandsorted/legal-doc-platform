import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["COOKIE_SECURE"] = "0"  # TestClient talks plain http
os.environ["MAIL_BACKEND"] = "memory"
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "test-only-admin-password")

os.environ.setdefault("STATEMENT_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
