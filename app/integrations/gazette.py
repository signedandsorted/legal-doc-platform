"""The Gazette: search published deceased estates notices (notice code 2903) and prepare a
Trustee Act 1925 section 27 notice pack the executor places themselves.

Sources (checked 2026-11-24):
- Notice feed (free JSON): https://www.thegazette.co.uk/wills-and-probate/notice/data.json?noticetype=2903
  docs: https://github.com/TheGazette/DevDocs/blob/master/notice/notice-feed.md
- How to place a deceased estates notice: https://www.thegazette.co.uk/all-notices/content/103403
- Price list: https://www.thegazette.co.uk/place-notice/pricing (deceased estates notice by web form
  £96.55 + VAT; forwarding service for deceased estates £87.55 + VAT; newspaper placement for
  deceased estates £240.00 + VAT).

Fair use: results are cached for a day, and each user action makes at most one request. The app
never places, pays for or submits a notice.
"""
from __future__ import annotations

import calendar
import re
import time
from datetime import date, timedelta
from typing import Any

import httpx

FEED_URL = "https://www.thegazette.co.uk/wills-and-probate/notice/data.json"
NOTICE_CODE = "2903"
PLACE_URL = "https://www.thegazette.co.uk/all-notices/content/103403"
PRICING_URL = "https://www.thegazette.co.uk/place-notice/pricing"
FEES_CHECKED = "2026-11-24"
FEES = [
    {"item": "Deceased estates notice in The Gazette (web form)", "ex_vat": "96.55"},
    {"item": "Forwarding service for deceased estates (optional)", "ex_vat": "87.55"},
    {"item": "Newspaper placement for deceased estates (needed if the estate includes land)", "ex_vat": "240.00"},
]
TIMEOUT_S = 10.0
CACHE_TTL_S = 24 * 60 * 60
PAGE_SIZE = 20
_cache: dict[tuple, tuple[float, list]] = {}


def clear_cache() -> None:
    _cache.clear()


def _text(v: Any) -> str:
    if isinstance(v, dict):
        v = v.get("#text") or v.get("$") or ""
    return re.sub(r"<[^>]+>", " ", str(v or "")).strip()


def parse_feed(data: dict) -> list[dict]:
    """Turn the Gazette JSON feed into simple notices. An empty result has no "entry" key."""
    entries = (data or {}).get("entry") or []
    if isinstance(entries, dict):
        entries = [entries]
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        nid = str(e.get("id") or "")
        link = ""
        for lk in e.get("link") or []:
            href = (lk or {}).get("@href", "")
            if "/notice/" in href and not lk.get("@rel") and not lk.get("@type"):
                link = href
                break
        notice_id = nid.rsplit("/", 1)[-1] if nid else ""
        out.append({
            "notice_id": notice_id,
            "name": _text(e.get("title")),
            "published": str(e.get("published") or "")[:10],
            "url": link or (f"https://www.thegazette.co.uk/notice/{notice_id}" if notice_id else ""),
            "notice_code": str(e.get("f:notice-code") or ""),
        })
    return out


def search(name: str, date_from: str = "", date_to: str = "", client: httpx.Client | None = None, now: float | None = None) -> list[dict]:
    """One feed request per call at most; repeated searches within a day come from the cache."""
    name = re.sub(r"\s+", " ", (name or "").strip())
    if len(name) < 2:
        return []
    now = time.time() if now is None else now
    key = (name.casefold(), date_from, date_to)
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL_S:
        return hit[1]
    params = {"noticetype": NOTICE_CODE, "text": name, "results-page-size": str(PAGE_SIZE)}
    if date_from:
        params["start-publish-date"] = date_from
    if date_to:
        params["end-publish-date"] = date_to
    owns = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S, headers={"User-Agent": "legal-doc-platform/probate-gazette", "Accept": "application/json"})
    try:
        resp = client.get(FEED_URL, params=params)
        resp.raise_for_status()
        notices = parse_feed(resp.json())
    finally:
        if owns:
            client.close()
    _cache[key] = (now, notices)
    return notices


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def claim_deadline(publication: str) -> str:
    """Last date for claims: at least two months plus one day after publication (s.27 requires
    not less than two months). Returns "" for a missing or invalid date."""
    try:
        d = date.fromisoformat((publication or "")[:10])
    except ValueError:
        return ""
    return (_add_months(d, 2) + timedelta(days=1)).isoformat()


def s27_pack(answers: dict) -> dict:
    """Pre-filled notice fields and a checklist. The executor places and pays for the notice."""
    dec = answers.get("deceased") or {}
    will = answers.get("will") or {}
    applicant = will.get("applicant") or {}
    n = answers.get("notice_s27") or {}
    pub = n.get("publication_date") or ""
    fields = {
        "deceased_name": dec.get("full_name") or "",
        "other_names": dec.get("other_names") or "",
        "last_address": dec.get("address") or "",
        "date_of_death": dec.get("date_of_death") or "",
        "executor_name": applicant.get("full_name") or "",
        "claims_address": n.get("claims_to") or applicant.get("address") or "",
        "publication_date": pub,
        "claim_deadline": claim_deadline(pub),
    }
    labels = {"deceased_name": "Name of the person who died", "last_address": "Their last address", "date_of_death": "Date of death",
              "executor_name": "Executor or administrator", "claims_address": "Where claims should be sent", "publication_date": "Planned publication date"}
    missing = [labels[k] for k in labels if not fields[k]]
    land = n.get("has_land") == "Yes"
    checklist = [
        "Check every detail against the death certificate and the will.",
        f"Place the notice yourself on The Gazette: {PLACE_URL}",
        "Give a claim deadline at least two months after the notice is published." + (f" For publication on {pub}, use {fields['claim_deadline']} or later." if fields["claim_deadline"] else ""),
        ("The estate includes land, so place the same notice in a newspaper local to the land as well." if land else "If the estate includes land, also place the notice in a newspaper local to the land."),
        "Keep a copy of the published notice for the estate file. Wait until the deadline has passed before paying everyone in full.",
    ]
    return {"fields": fields, "missing": missing, "checklist": checklist, "fees": FEES, "fees_source": PRICING_URL, "fees_checked": FEES_CHECKED,
            "place_url": PLACE_URL, "note": "This helper prepares the wording only. You place and pay for the notice yourself; nothing is sent to The Gazette from here."}
