"""AES-256-GCM encryption for supporting video statements.

Videos are stored in the database like other uploads, but the bytes are encrypted
before they are written. The key comes from STATEMENT_ENCRYPTION_KEY (url-safe
base64 of 32 random bytes). In local SQLite development only, a key is created
in gitignored local.statement_key if the environment variable is not set.
"""
from __future__ import annotations

import base64
import logging
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("legal-doc")
PREFIX = b"SAS1"
NONCE_LEN = 12
KEY_LEN = 32
DEV_KEY_FILE = Path("local.statement_key")


class EncryptionNotConfigured(RuntimeError):
    pass


def generate_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(KEY_LEN)).decode()


def _decode_key(raw: str) -> bytes:
    text = (raw or "").strip()
    if not text:
        raise EncryptionNotConfigured("STATEMENT_ENCRYPTION_KEY is missing")
    try:
        key = base64.urlsafe_b64decode(text)
    except Exception as exc:
        raise EncryptionNotConfigured("STATEMENT_ENCRYPTION_KEY is not valid url-safe base64") from exc
    if len(key) != KEY_LEN:
        raise EncryptionNotConfigured("STATEMENT_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def _dev_key() -> str | None:
    """Only for local SQLite. Never invent a key when DATABASE_URL points at Postgres."""
    url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    if "sqlite" not in url:
        return None
    if DEV_KEY_FILE.exists():
        return DEV_KEY_FILE.read_text(encoding="utf-8")
    key = generate_key()
    DEV_KEY_FILE.write_text(key + "\n", encoding="utf-8")
    try:
        os.chmod(DEV_KEY_FILE, 0o600)
    except OSError:
        pass
    log.warning("Wrote a local development key to %s. Set STATEMENT_ENCRYPTION_KEY in production.", DEV_KEY_FILE)
    return key


def load_key() -> bytes:
    raw = os.getenv("STATEMENT_ENCRYPTION_KEY", "")
    if not raw:
        raw = _dev_key() or ""
    return _decode_key(raw)


def encrypt(plain: bytes) -> bytes:
    if not plain:
        raise ValueError("Cannot encrypt an empty recording")
    nonce = secrets.token_bytes(NONCE_LEN)
    ct = AESGCM(load_key()).encrypt(nonce, plain, None)
    return PREFIX + nonce + ct


def decrypt(blob: bytes) -> bytes:
    if not blob or not blob.startswith(PREFIX):
        raise ValueError("This recording is not in a recognised encrypted format")
    nonce = blob[len(PREFIX):len(PREFIX) + NONCE_LEN]
    ct = blob[len(PREFIX) + NONCE_LEN:]
    if len(nonce) != NONCE_LEN or not ct:
        raise ValueError("This recording is damaged")
    try:
        return AESGCM(load_key()).decrypt(nonce, ct, None)
    except Exception as exc:
        raise ValueError("This recording could not be decrypted") from exc
