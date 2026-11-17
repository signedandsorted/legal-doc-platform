import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, LargeBinary, MetaData, String, Table, Text, create_engine

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
    metadata.create_all(engine())


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())
