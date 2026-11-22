import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, MetaData, String, Table, Text, create_engine

metadata = MetaData()

drafts = Table(
    "drafts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("service", String(32), nullable=False),
    Column("client_name", Text, nullable=False),
    Column("client_email", Text),
    Column("answers", JSON, nullable=False),
    Column("status", String(32), nullable=False, default="draft"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("user_id", String(36), index=True),  # added by migration 2; NULL only for drafts made before logins existed
)

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("role", String(16), nullable=False, default="client"),  # client | staff | admin
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_login_at", DateTime(timezone=True)),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("ip", String(64)),
)

password_resets = Table(
    "password_resets",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used", Boolean, nullable=False, default=False),
)

login_attempts = Table(
    "login_attempts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("bucket", String(300), nullable=False, index=True),  # e.g. "login:ip:1.2.3.4" or "login:email:a@b.c"
    Column("at", DateTime(timezone=True), nullable=False, index=True),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False, index=True),
    Column("actor_id", String(36)),
    Column("actor_email", String(254)),
    Column("action", String(64), nullable=False),
    Column("target_type", String(32)),
    Column("target_id", String(64)),
    Column("detail", JSON),
    Column("ip", String(64)),
)

schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("applied_at", DateTime(timezone=True), nullable=False),
)

uploads = Table(
    "uploads",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("draft_id", String(36), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("filename", Text, nullable=False),
    Column("content_type", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("size", Integer, nullable=False),
    Column("data", LargeBinary, nullable=False),
    Column("text", Text, nullable=False, default=""),
    Column("read_as", String(16), nullable=False),
    Column("suggestions", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


capacity_statements = Table(
    "capacity_statements",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("draft_id", String(36), ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("service", String(32), nullable=False),
    Column("document_version_hash", String(64), nullable=False),
    Column("content_sha256", String(64), nullable=False),
    Column("filename", Text, nullable=False),
    Column("content_type", Text, nullable=False),
    Column("size", Integer, nullable=False),
    Column("duration_seconds", Integer),
    Column("source", String(16), nullable=False),
    Column("prompt_set_id", String(64), nullable=False),
    Column("consent_text_hash", String(64), nullable=False),
    Column("medical_assessment_interest", Boolean, nullable=False, default=False),
    Column("is_current", Boolean, nullable=False, default=True),
    Column("encrypted_data", LargeBinary, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("user_agent", Text),
    Column("ip", String(64)),
)


matters = Table(
    "matters",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("kind", String(32), nullable=False),
    Column("title", Text, nullable=False),
    Column("status", String(32), nullable=False, default="open"),
    Column("client_name", Text, nullable=False, default=""),
    Column("client_email", Text, nullable=False, default=""),
    Column("deceased_name", Text, nullable=False, default=""),
    Column("date_of_death", String(10), nullable=False, default=""),
    Column("grant_date", String(10), nullable=False, default=""),
    Column("facts", JSON, nullable=False),
    Column("draft_id", String(36)),
    Column("opened_by", String(36), ForeignKey("users.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def init_db() -> None:
    from .migrations import migrate
    migrate(engine())


def reset_engine() -> None:
    """Tests only: drop the cached engine so a new DATABASE_URL takes effect."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())
