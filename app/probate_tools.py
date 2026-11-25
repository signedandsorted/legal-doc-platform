"""Small read-only lookup endpoints used by probate guide steps. Nothing here files or submits
anything for the family; they search official lists and the family acts on the result."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from .auth import require_admin, require_user
from sqlalchemy import select

from .db import drafts, engine, uploads
from .integrations import asset_trace, bona_vacantia, estatesearch_catalog, estatesearch_pack, gazette, hmlr
from .security import audit

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


def _probate_draft(conn, draft_id: str, user: dict):
    row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row or row["user_id"] != user["id"] or row["service"] != "probate":
        raise HTTPException(404, "Draft not found")
    return row


class HmlrIn(BaseModel):
    search_type: str
    names: list[str] = []
    confirm: bool = False


@router.get("/hmlr/status")
def hmlr_status(_user=Depends(require_user)):
    st = hmlr.Settings.from_env()
    return {"switched_on": st.switched_on, "message": "" if st.switched_on else hmlr.NOT_ON,
            "fees": {k: v / 100 for k, v in hmlr.FEES_PENCE.items()}, "fee_sources": hmlr.FEE_SOURCES, "fees_checked": hmlr.FEES_CHECKED}


@router.post("/drafts/{draft_id}/hmlr/quote")
def hmlr_quote(draft_id: str, body: HmlrIn, user=Depends(require_user)):
    with engine().connect() as conn:
        _probate_draft(conn, draft_id, user)
        try:
            return hmlr.quote(conn, body.search_type, body.names)
        except hmlr.HmlrError as exc:
            raise HTTPException(exc.status, str(exc))


@router.post("/drafts/{draft_id}/hmlr/order")
def hmlr_order(draft_id: str, body: HmlrIn, user=Depends(require_user)):
    with engine().begin() as conn:
        _probate_draft(conn, draft_id, user)
        ups = [dict(r) for r in conn.execute(select(uploads.c.kind).where(uploads.c.draft_id == draft_id)).mappings()]
        try:
            results = hmlr.order(conn, body.search_type, body.names, confirm=body.confirm, uploads=ups, draft_id=draft_id, user_id=user["id"])
        except hmlr.HmlrError as exc:
            raise HTTPException(exc.status, str(exc))
    audit("hmlr_search_ordered", user, "draft", draft_id, {"type": body.search_type, "names": len(results)}, None)
    return {"results": results}


@router.get("/admin/hmlr-ledger")
def hmlr_ledger(_admin=Depends(require_admin)):
    with engine().connect() as conn:
        day = hmlr.today_utc()
        return {"today": day, "spent_today": hmlr.spent_today_pence(conn, day) / 100, "daily_cap": hmlr.Settings.from_env().daily_cap_pence / 100, "rows": hmlr.ledger(conn)}


@router.get("/estatesearch/catalog")
def estatesearch_catalog_view(_user=Depends(require_user)):
    return estatesearch_catalog.catalog()


@router.get("/estatesearch/quote")
def estatesearch_quote(ids: str = Query("", max_length=400), _user=Depends(require_user)):
    return estatesearch_catalog.quote([x for x in ids.split(",") if x])


def _estatesearch_pack(draft_id: str, user: dict) -> dict:
    with engine().connect() as conn:
        row = _probate_draft(conn, draft_id, user)
        ups = [dict(r) for r in conn.execute(select(uploads.c.filename, uploads.c.kind).where(uploads.c.draft_id == draft_id)).mappings()]
    try:
        return estatesearch_pack.build_pack(row["answers"] or {}, ups)
    except estatesearch_pack.PackBlocked as exc:
        raise HTTPException(400, {"message": str(exc), "missing": exc.missing})


@router.get("/drafts/{draft_id}/estatesearch/pack")
def estatesearch_pack_json(draft_id: str, user=Depends(require_user)):
    return _estatesearch_pack(draft_id, user)


@router.get("/drafts/{draft_id}/estatesearch/pack.pdf")
def estatesearch_pack_pdf(draft_id: str, user=Depends(require_user)):
    from .pdf import render_pdf
    pdf = render_pdf(estatesearch_pack.pack_document(_estatesearch_pack(draft_id, user)))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="estatesearch-order-pack.pdf"'})


@router.get("/drafts/{draft_id}/find-notify")
def find_notify(draft_id: str, user=Depends(require_user)):
    with engine().connect() as conn:
        row = _probate_draft(conn, draft_id, user)
    return asset_trace.pack(row["answers"] or {})


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
