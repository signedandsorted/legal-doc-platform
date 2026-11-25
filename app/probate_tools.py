"""Small read-only lookup endpoints used by probate guide steps. Nothing here files or submits
anything for the family; they search official lists and the family acts on the result."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_user
from sqlalchemy import select

from .db import drafts, engine
from .integrations import bona_vacantia, gazette

router = APIRouter(prefix="/api/probate", tags=["probate-tools"])


@router.get("/bona-vacantia")
def bona_vacantia_search(surname: str = Query(..., min_length=2, max_length=80), forename: str = Query("", max_length=80), _user=Depends(require_user)):
    try:
        return bona_vacantia.lookup(surname, forename)
    except bona_vacantia.BonaVacantiaUnavailable as exc:
        raise HTTPException(503, str(exc))


@router.get("/gazette")
def gazette_search(name: str = Query(..., min_length=2, max_length=120), date_from: str = Query("", max_length=10), date_to: str = Query("", max_length=10), _user=Depends(require_user)):
    for d in (date_from, date_to):
        if d and not (len(d) == 10 and d[4] == "-" and d[7] == "-"):
            raise HTTPException(400, "Dates must look like 2026-01-31")
    try:
        notices = gazette.search(name, date_from, date_to)
    except Exception:
        raise HTTPException(503, "The Gazette could not be reached just now. Please try again later.")
    return {"notices": notices, "source": gazette.FEED_URL, "note": "Deceased estates notices (code 2903) from The Gazette's public feed."}


@router.get("/drafts/{draft_id}/s27-pack")
def s27_pack(draft_id: str, user=Depends(require_user)):
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row or row["user_id"] != user["id"] or row["service"] != "probate":
        raise HTTPException(404, "Draft not found")
    return gazette.s27_pack(row["answers"] or {})


INSOLVENCY_SEARCH_URL = "https://www.gov.uk/search-bankruptcy-insolvency-register"  # checked 2026-11-24; no public API, never called from here
CHECKED_RESULTS = {"Clear: no entry found", "Possible match found"}


def stamp_insolvency_checks(old_answers: dict | None, new_answers: dict, now: datetime | None = None) -> dict:
    """Give each recorded insolvency result a server-side UTC timestamp. A result that has not
    changed keeps its first timestamp; a changed result gets a new one. Makes no outbound calls."""
    block = new_answers.get("insolvency")
    if not isinstance(block, dict) or not isinstance(block.get("checks"), list):
        return new_answers
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    before = {}
    for c in ((old_answers or {}).get("insolvency") or {}).get("checks") or []:
        if isinstance(c, dict):
            before[((c.get("name") or "").strip().casefold(), c.get("result"))] = c.get("recorded_at")
    checks = []
    for c in block["checks"]:
        if not isinstance(c, dict):
            continue
        c = dict(c)
        if c.get("result") in CHECKED_RESULTS:
            c["recorded_at"] = before.get(((c.get("name") or "").strip().casefold(), c.get("result"))) or stamp
        else:
            c.pop("recorded_at", None)
        checks.append(c)
    out = dict(new_answers)
    out["insolvency"] = {**block, "checks": checks}
    return out
