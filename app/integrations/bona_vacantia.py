"""GOV.UK unclaimed estates list (Bona Vacantia Division) lookup.

Source page (Open Government Licence v3.0):
  https://www.gov.uk/government/statistical-data-sets/unclaimed-estates-list
The CSV asset URL changes whenever BVD republishes, so we never hard-code it. We read the
page through the GOV.UK Content API and take the current text/csv attachment:
  https://www.gov.uk/api/content/government/statistical-data-sets/unclaimed-estates-list
Checked 2026-11-24: columns are "BV Reference, Forename, Surname, Date of Death, Place of Death".
How to claim: https://www.gov.uk/guidance/make-a-claim-to-a-deceased-persons-estate

The list is downloaded at most once a day into a cache file under the app data dir. If a
download fails we fall back to the last cached copy and say when it was fetched. This module
never submits a claim; the family or executor does that themselves with BVD.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

PAGE_URL = "https://www.gov.uk/government/statistical-data-sets/unclaimed-estates-list"
CONTENT_API_URL = "https://www.gov.uk/api/content/government/statistical-data-sets/unclaimed-estates-list"
CLAIM_URL = "https://www.gov.uk/guidance/make-a-claim-to-a-deceased-persons-estate"
SOURCE_CHECKED = "2026-11-24"
MAX_AGE_S = 24 * 60 * 60
TIMEOUT_S = 15.0
MAX_RESULTS = 50


class BonaVacantiaUnavailable(RuntimeError):
    """No fresh download and no cached copy."""


def data_dir() -> Path:
    path = Path(os.environ.get("APP_DATA_DIR") or "/tmp/legal-doc-platform-data")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_paths() -> tuple[Path, Path]:
    d = data_dir()
    return d / "unclaimed_estates.csv", d / "unclaimed_estates.meta.json"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()


def parse_csv(text: str) -> list[dict]:
    """Parse the BVD CSV into rows with stable keys. Unknown or blank rows are skipped."""
    text = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for raw in reader:
        r = {(k or "").strip().casefold(): (v or "").strip() for k, v in raw.items() if k}
        surname = r.get("surname", "")
        if not surname:
            continue
        rows.append({
            "bv_reference": r.get("bv reference", ""),
            "forename": r.get("forename", ""),
            "surname": surname,
            "date_of_death": r.get("date of death", ""),
            "place_of_death": re.sub(r"\s+", " ", r.get("place of death", "")),
        })
    return rows


def index_by_surname(rows: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for r in rows:
        idx.setdefault(_norm(r["surname"]), []).append(r)
    return idx


def search(rows: list[dict], surname: str, forename: str = "") -> list[dict]:
    """Case-insensitive exact surname match; optional forename narrows to rows whose forenames
    start with (or contain as a word) what was typed."""
    hits = index_by_surname(rows).get(_norm(surname), [])
    f = _norm(forename)
    if f:
        hits = [r for r in hits if _norm(r["forename"]).startswith(f) or f in _norm(r["forename"]).split(" ")]
    return hits[:MAX_RESULTS]


def current_csv_url(client: httpx.Client) -> str:
    """Find the current CSV attachment on the GOV.UK page (the asset URL changes)."""
    resp = client.get(CONTENT_API_URL)
    resp.raise_for_status()
    details = (resp.json() or {}).get("details") or {}
    for att in details.get("attachments") or []:
        url = att.get("url") or ""
        if (att.get("content_type") == "text/csv" or url.lower().endswith(".csv")) and url.startswith("https://assets.publishing.service.gov.uk/"):
            return url
    found = re.findall(r'href="(https://assets\.publishing\.service\.gov\.uk/[^"]+\.csv)"', details.get("body") or "")
    if found:
        return found[0]
    raise RuntimeError("No CSV link on the GOV.UK unclaimed estates page")


def load(client: httpx.Client | None = None, now: float | None = None) -> dict:
    """Return {"rows", "fetched_at", "source_url", "stale", "note"}. Downloads at most once a day."""
    now = time.time() if now is None else now
    csv_path, meta_path = _cache_paths()
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
    fresh = csv_path.is_file() and (now - float(meta.get("fetched_ts") or 0)) < MAX_AGE_S
    note = ""
    if not fresh:
        owns = client is None
        client = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=True, headers={"User-Agent": "legal-doc-platform/probate-bona-vacantia"})
        try:
            url = current_csv_url(client)
            resp = client.get(url)
            resp.raise_for_status()
            text = resp.text
            if not parse_csv(text):
                raise RuntimeError("The downloaded list was empty")
            csv_path.write_text(text, encoding="utf-8")
            meta = {"fetched_ts": now, "fetched_at": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="minutes"), "source_url": url}
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
        except (httpx.HTTPError, RuntimeError, ValueError):
            if not csv_path.is_file():
                raise BonaVacantiaUnavailable("The GOV.UK unclaimed estates list could not be downloaded just now. Please try again later.")
            note = "GOV.UK could not be reached just now, so this uses the copy we fetched on %s (UTC)." % (meta.get("fetched_at") or "an earlier day")
        finally:
            if owns:
                client.close()
    rows = parse_csv(csv_path.read_text(encoding="utf-8"))
    return {"rows": rows, "fetched_at": meta.get("fetched_at", ""), "source_url": meta.get("source_url", ""), "stale": bool(note), "note": note}


def lookup(surname: str, forename: str = "", client: httpx.Client | None = None, now: float | None = None) -> dict:
    data = load(client=client, now=now)
    return {
        "matches": search(data["rows"], surname, forename),
        "fetched_at": data["fetched_at"],
        "stale": data["stale"],
        "note": data["note"],
        "page_url": PAGE_URL,
        "claim_url": CLAIM_URL,
        "licence": "Contains public sector information licensed under the Open Government Licence v3.0.",
    }
