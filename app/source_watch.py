"""Daily check of the official pages this desk relies on.

A change is recorded for a person to read. The check does not rewrite a will,
an LPA or a tax figure. GOV.UK and the Law Society do not push updates into
this software.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "var" / "source_watch.json"
INTERVAL = timedelta(hours=24)
_LOCK = threading.Lock()
_RUNNING = False

PAGES = [
    {"id": "lexcel", "title": "Law Society: Lexcel", "url": "https://www.lawsociety.org.uk/topics/firm-accreditations/lexcel"},
    {"id": "lexcel-apply", "title": "Law Society: how to apply for Lexcel v6.1", "url": "https://www.lawsociety.org.uk/topics/firm-accreditations/lexcel/how-to-apply-for-lexcel-england-and-wales-v6-1"},
    {"id": "wiqs", "title": "Law Society: Wills and Inheritance Quality Scheme", "url": "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme"},
    {"id": "wiqs-apply", "title": "Law Society: how to apply for the scheme", "url": "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme/how-to-apply"},
    {"id": "wiqs-training", "title": "Law Society: scheme training", "url": "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme/training"},
    {"id": "wiqs-protocol", "title": "Wills and Inheritance Protocol PDF", "url": "https://tls-sc104-prd-glo-fde-01-duatf0eka4hpcxe6.a03.azurefd.net/-/media/files/accreditations/wiqs/wills-and-inheritance-protocol.pdf?rev=a7a352c41cbd4f58b38c9ab40443afe4&hash=A390E01065FCEE60FDD8DB84CC524417"},
    {"id": "wiqs-core", "title": "Core practice management standards PDF", "url": "https://tls-sc104-prd-glo-fde-01-duatf0eka4hpcxe6.a03.azurefd.net/-/media/files/accreditations/wiqs/wiqs-core-practice-management-standards.pdf?rev=ce10ee03ef87441b952db535ae8c8e47&hash=3A948F2B528497D171D6DA2593932F9F"},
    {"id": "make-will", "title": "GOV.UK: Making a will", "url": "https://www.gov.uk/make-will"},
    {"id": "will-legal", "title": "GOV.UK: Make sure your will is legal", "url": "https://www.gov.uk/make-will/make-sure-your-will-is-legal"},
    {"id": "probate-fees", "title": "GOV.UK: Probate fees", "url": "https://www.gov.uk/applying-for-probate/fees"},
    {"id": "iht", "title": "GOV.UK: Inheritance Tax", "url": "https://www.gov.uk/inheritance-tax"},
    {"id": "iht-pensions", "title": "GOV.UK: Inheritance Tax on pensions", "url": "https://www.gov.uk/government/publications/inheritance-tax-on-pensions-technical-note/technical-note-inheritance-tax-on-pensions"},
    {"id": "iht400", "title": "GOV.UK: IHT400", "url": "https://www.gov.uk/government/publications/inheritance-tax-inheritance-tax-account-iht400"},
    {"id": "lpa", "title": "GOV.UK: Lasting power of attorney", "url": "https://www.gov.uk/power-of-attorney"},
    {"id": "lp12", "title": "GOV.UK: LP12", "url": "https://www.gov.uk/government/publications/lasting-power-of-attorney-forms/lp12-make-and-register-your-lasting-power-of-attorney-a-guide-web-version"},
    {"id": "sra-wills", "title": "SRA: Drafting and preparation of wills", "url": "https://www.sra.org.uk/solicitors/guidance/drafting-preparation-wills/"},
    {"id": "trust-register", "title": "GOV.UK: Register a trust as a trustee", "url": "https://www.gov.uk/guidance/register-a-trust-as-a-trustee"},
    {"id": "trust-check", "title": "GOV.UK: check if you need to register a trust", "url": "https://www.gov.uk/guidance/check-if-you-need-to-register-a-trust"},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> dict:
    if not STORE.is_file():
        return {"checked_at": "", "pages": {}, "changes": []}
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"checked_at": "", "pages": {}, "changes": []}


def _save(data: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def fingerprint(body: bytes, content_type: str) -> str:
    if body.startswith(b"%PDF") or "pdf" in (content_type or "").lower():
        return hashlib.sha256(body).hexdigest()
    text = body.decode("utf-8", "ignore")
    text = re.sub(r"(?is)<script\b.*?</script>", " ", text)
    text = re.sub(r"(?is)<style\b.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch(url: str, timeout: int = 20) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "SignedAndSorted source check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(2_000_000)
            kind = response.headers.get("Content-Type", "")
            return response.status, fingerprint(body, kind), ""
    except urllib.error.HTTPError as exc:
        return exc.code, "", f"HTTP {exc.code}"
    except Exception as exc:
        return 0, "", exc.__class__.__name__


def run_check(fetcher=fetch) -> dict:
    """Compare each official page with the last reading. Does not edit the desk."""
    previous = _load()
    known = previous.get("pages") or {}
    changes = list(previous.get("changes") or [])
    pages = {}
    found = []
    failed = []
    when = _now().isoformat()
    for page in PAGES:
        status, digest, error = fetcher(page["url"])
        row = {"title": page["title"], "url": page["url"], "status": status, "hash": digest, "error": error, "at": when}
        pages[page["id"]] = row
        before = known.get(page["id"]) or {}
        if error or status >= 400 or not digest:
            failed.append({"id": page["id"], "title": page["title"], "url": page["url"], "error": error or f"HTTP {status}"})
            continue
        if before.get("hash") and before["hash"] != digest:
            item = {
                "id": page["id"], "title": page["title"], "url": page["url"], "at": when,
                "note": "The page changed. A person reads it and updates the desk. This check does not rewrite a clause.",
            }
            found.append(item)
            changes.insert(0, item)
    data = {"checked_at": when, "pages": pages, "changes": changes[:40]}
    _save(data)
    data["found"] = found
    data["failed"] = failed
    return data


def public_watch() -> dict:
    data = _load()
    failed = []
    for key, row in (data.get("pages") or {}).items():
        if row.get("error") or (row.get("status") or 0) >= 400:
            failed.append({"id": key, "title": row.get("title") or key, "url": row.get("url") or "", "error": row.get("error") or f"HTTP {row.get('status')}"})
    return {
        "checked_at": data.get("checked_at") or "",
        "changes": data.get("changes") or [],
        "failed": failed,
        "pages": len(PAGES),
        "note": "The desk reads these pages once a day. A change is listed here for a person. Nothing in a will, an LPA or a tax figure is rewritten by the check.",
    }


def due(now: datetime | None = None) -> bool:
    checked = _load().get("checked_at") or ""
    if not checked:
        return True
    try:
        when = datetime.fromisoformat(checked)
    except ValueError:
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now or _now()) - when >= INTERVAL


def start_background() -> None:
    """Start the daily loop unless tests, or SOURCE_WATCH=0, have switched it off."""
    if os.environ.get("SOURCE_WATCH") == "0" or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    global _RUNNING
    with _LOCK:
        if _RUNNING:
            return
        _RUNNING = True

    def loop():
        while True:
            try:
                if due():
                    run_check()
            except Exception:
                pass
            threading.Event().wait(6 * 60 * 60)

    threading.Thread(target=loop, name="source-watch", daemon=True).start()
