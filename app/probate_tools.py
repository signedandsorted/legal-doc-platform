"""Small read-only lookup endpoints used by probate guide steps. Nothing here files or submits
anything for the family; they search official lists and the family acts on the result."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_user
from .integrations import bona_vacantia

router = APIRouter(prefix="/api/probate", tags=["probate-tools"])


@router.get("/bona-vacantia")
def bona_vacantia_search(surname: str = Query(..., min_length=2, max_length=80), forename: str = Query("", max_length=80), _user=Depends(require_user)):
    try:
        return bona_vacantia.lookup(surname, forename)
    except bona_vacantia.BonaVacantiaUnavailable as exc:
        raise HTTPException(503, str(exc))


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
