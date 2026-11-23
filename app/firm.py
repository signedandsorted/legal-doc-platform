"""Firm desk. Staff and admins only. Clients of the public site cannot open it."""
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, insert, select, update

from .auth import require_admin, require_staff
from .db import drafts, engine, matter_uploads, matters, new_id, now, users
from .documents import find_issues, missing_fields
from .extract import detect_kind, extract_text, suggest
from .firm_books import clean_books, compile_books, letter_text
from .firm_account import account_document, account_html, prepare_asset_search
from .iht400_pdf import fill_iht400, refresh_official_form
from .firm_file import PAPER_KINDS, apply_suggestions, filing_record, pack_document, position
from .firm_work import ITEM_STATUS, MATTER_STATUS, assist, checklist, client_prepare, deadlines, next_item, progress
from .guides import SERVICES
from .pdf import render_pdf
from .security import audit, client_ip, hash_password, normalise_email, check_password_rules

router = APIRouter(prefix="/api/firm")
MAX_PAPERS = 15
MAX_PAPER_BYTES = 10 * 1024 * 1024
PAPER_EXT = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".heic", ".webp"}


class MatterIn(BaseModel):
    kind: str
    title: str = ""
    client_name: str = ""
    client_email: str = ""
    deceased_name: str = ""
    date_of_death: str = ""


class MatterPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    client_name: str | None = None
    client_email: str | None = None
    deceased_name: str | None = None
    date_of_death: str | None = None
    grant_date: str | None = None
    item_id: str | None = None
    item_status: str | None = None
    note: str | None = None
    books: dict | None = None
    assigned_to: str | None = None
    hmrc_code: str | None = None
    hmrc_posted_on: str | None = None
    grant_filed_on: str | None = None
    grant_reference: str | None = None


class ApplyIn(BaseModel):
    suggestion_ids: list[str] = Field(default_factory=list)


class LetterIn(BaseModel):
    kind: str


class AssistIn(BaseModel):
    action: str = "next"


class ColleagueIn(BaseModel):
    email: str
    password: str = Field(min_length=12)


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _load(matter_id: str) -> dict:
    with engine().connect() as conn:
        row = conn.execute(select(matters).where(matters.c.id == matter_id)).mappings().first()
    if not row:
        raise HTTPException(404, "Matter not found")
    return dict(row)


def _public(row: dict, full: bool = False) -> dict:
    kind = row["kind"]
    facts = row["facts"] or {}
    stage, item = next_item(kind, facts)
    compiled = compile_books(row) if kind == "probate" else None
    figures = compiled["figures"] if compiled else None
    out = {
        "id": row["id"],
        "kind": kind,
        "kind_label": SERVICES[kind]["short_title"] if kind in SERVICES else kind,
        "title": row["title"],
        "status": row["status"],
        "client_name": row["client_name"],
        "client_email": row["client_email"],
        "deceased_name": row["deceased_name"],
        "date_of_death": row["date_of_death"],
        "grant_date": row["grant_date"],
        "draft_id": row["draft_id"],
        "assigned_to": facts.get("assigned_to") or "",
        "progress": progress(kind, facts),
        "next": None if not item else {"stage": stage["title"], "title": item["title"], "ask": item["ask"]},
        "deadlines": deadlines(row),
        "figures": figures,
        "updated_at": _iso(row["updated_at"]),
    }
    if full:
        states = facts.get("items") or {}
        stages = []
        for stage in checklist(kind):
            stages.append({**stage, "items": [{**it, "status": states.get(it["id"], "needed")} for it in stage["items"]]})
        out["stages"] = stages
        out["notes"] = facts.get("notes") or []
        if compiled:
            out["books"] = compiled["books"]
            out["accounts"] = compiled["accounts"]
            out["forms"] = compiled["forms"]
            papers = _papers(row["id"])
            out["papers"] = papers
            out["filing"] = position(row, compiled, papers)
    return out


def _papers(matter_id: str) -> list[dict]:
    with engine().connect() as conn:
        rows = conn.execute(select(
            matter_uploads.c.id, matter_uploads.c.filename, matter_uploads.c.kind, matter_uploads.c.size,
            matter_uploads.c.read_as, matter_uploads.c.suggestions, matter_uploads.c.created_at,
        ).where(matter_uploads.c.matter_id == matter_id).order_by(matter_uploads.c.created_at)).mappings().all()
    return [{**dict(r), "created_at": _iso(r["created_at"])} for r in rows]


def _draft_check(draft_id: str | None) -> dict | None:
    if not draft_id:
        return None
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row:
        return {"missing": [], "issues": [], "detail": "The linked draft has been deleted. Open a new one."}
    who = ((row["answers"] or {}).get("account") or {}).get("who_files") or ""
    detail = ""
    if who.startswith("I want the firm"):
        detail = "The client has asked the firm to file the grant. A solicitor files it in MyHMCTS, or by post if the online service will not take it. This desk does not send it."
    elif who.startswith("I will file"):
        detail = "The client will file the grant themselves."
    return {"missing": missing_fields(row["service"], row["answers"]), "issues": find_issues(row["service"], row["answers"], ""), "detail": detail, "who_files": who}


@router.get("/kinds")
def kinds(_staff: dict = Depends(require_staff)):
    return [{"id": s["id"], "label": s.get("short_title") or s["title"], "title": s["title"]} for s in SERVICES.values()]


@router.get("/matters")
def list_matters(_staff: dict = Depends(require_staff)):
    with engine().connect() as conn:
        rows = conn.execute(select(matters).order_by(matters.c.updated_at.desc())).mappings().all()
    return [_public(dict(r)) for r in rows]


@router.post("/matters")
def open_matter(body: MatterIn, request: Request, staff: dict = Depends(require_staff)):
    if body.kind not in SERVICES:
        raise HTTPException(400, "Unknown matter type")
    title = body.title.strip() or SERVICES[body.kind]["title"]
    if body.kind == "probate" and body.deceased_name.strip():
        title = title if body.title.strip() else f"Estate of {body.deceased_name.strip()}"
    mid = new_id()
    stamp = now()
    with engine().begin() as conn:
        conn.execute(insert(matters).values(
            id=mid, kind=body.kind, title=title, status="open",
            client_name=body.client_name.strip(), client_email=body.client_email.strip(),
            deceased_name=body.deceased_name.strip(), date_of_death=body.date_of_death.strip(),
            grant_date="", facts={"items": {}, "notes": []}, draft_id=None,
            opened_by=staff["id"], created_at=stamp, updated_at=stamp,
        ))
    audit("matter_opened", staff, "matter", mid, {"kind": body.kind}, client_ip(request))
    return _public(_load(mid), full=True)


@router.get("/matters/{matter_id}")
def get_matter(matter_id: str, _staff: dict = Depends(require_staff)):
    return _public(_load(matter_id), full=True)


@router.patch("/matters/{matter_id}")
def patch_matter(matter_id: str, body: MatterPatch, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    facts = dict(row["facts"] or {"items": {}, "notes": []})
    values = {"updated_at": now()}
    for key in ("title", "client_name", "client_email", "deceased_name", "date_of_death", "grant_date"):
        val = getattr(body, key)
        if val is not None:
            values[key] = val.strip()
    if body.status is not None:
        if body.status not in MATTER_STATUS:
            raise HTTPException(400, "Unknown status")
        values["status"] = body.status
    if body.item_id is not None:
        if body.item_status not in ITEM_STATUS:
            raise HTTPException(400, "Unknown item status")
        known = {it["id"] for it in (it for stage in checklist(row["kind"]) for it in stage["items"])}
        if body.item_id not in known:
            raise HTTPException(400, "Unknown checklist item")
        facts.setdefault("items", {})[body.item_id] = body.item_status
    if body.note is not None:
        text = body.note.strip()
        if text:
            facts.setdefault("notes", []).append({"at": now().isoformat(), "by": staff["email"], "text": text[:4000]})
    if body.assigned_to is not None:
        facts["assigned_to"] = body.assigned_to.strip()[:254]
    if body.books is not None:
        facts["books"] = clean_books(body.books)
        facts.setdefault("activity", []).append({"at": now().isoformat(), "by": staff["email"], "what": "Figures updated"})
        facts["activity"] = facts["activity"][-30:]
    recorded = filing_record(facts)
    for key in ("hmrc_code", "hmrc_posted_on", "grant_filed_on", "grant_reference"):
        val = getattr(body, key)
        if val is not None:
            recorded[key] = val.strip()[:40]
    if any(getattr(body, key) is not None for key in ("hmrc_code", "hmrc_posted_on", "grant_filed_on", "grant_reference")):
        facts["filing"] = recorded
    values["facts"] = facts
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(**values))
        if body.books is not None and row["kind"] == "probate" and row["draft_id"]:
            fresh = dict(row)
            fresh.update(values)
            compiled = compile_books(fresh)
            draft = conn.execute(select(drafts.c.answers).where(drafts.c.id == row["draft_id"])).scalar()
            answers = dict(draft or {})
            answers.update(compiled["answers"])
            conn.execute(update(drafts).where(drafts.c.id == row["draft_id"]).values(answers=answers, updated_at=now()))
    audit("matter_updated", staff, "matter", matter_id, {"item": body.item_id, "status": body.status, "books": body.books is not None}, client_ip(request))
    return _public(_load(matter_id), full=True)


class SearchIn(BaseModel):
    fee: float = 0
    paid: bool = False
    targets: list[str] = Field(default_factory=list)


@router.post("/matters/{matter_id}/asset-search")
def order_asset_search(matter_id: str, body: SearchIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if row["kind"] != "probate":
        raise HTTPException(400, "An asset search is for a probate matter")
    facts = dict(row["facts"] or {})
    books = clean_books(facts.get("books"))
    try:
        books = prepare_asset_search(row, books, body.targets, body.fee, body.paid)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    books = clean_books(books)
    facts["books"] = books
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("asset_search", staff, "matter", matter_id, {"targets": len(body.targets), "fee": books["asset_search"]["fee"]}, client_ip(request))
    return _public(_load(matter_id), full=True)


@router.post("/matters/{matter_id}/assist")
def matter_assist(matter_id: str, body: AssistIn, _staff: dict = Depends(require_staff)):
    if body.action not in ("next", "request", "check"):
        raise HTTPException(400, "Unknown assistant action")
    row = _load(matter_id)
    draft = _draft_check(row["draft_id"]) if body.action == "check" else None
    return assist(row, body.action, draft)


@router.post("/matters/{matter_id}/letters")
def keep_letter(matter_id: str, body: LetterIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if body.kind not in ("bank", "beneficiary", "grant", "notice", "credit"):
        raise HTTPException(400, "Unknown letter")
    compiled = compile_books(row)
    letter = letter_text(body.kind, row, compiled)
    if not letter:
        raise HTTPException(400, "That letter needs a probate matter")
    facts = dict(row["facts"] or {})
    books = clean_books(facts.get("books"))
    books["letters"].append({"id": new_id()[:8], "title": letter["title"], "body": letter["body"], "at": now().isoformat(), "by": staff["email"]})
    facts["books"] = books
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("matter_letter", staff, "matter", matter_id, {"kind": body.kind}, client_ip(request))
    return {"letter": letter, "matter": _public(_load(matter_id), full=True)}


@router.get("/matters/{matter_id}/export")
def export_matter(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row) if row["kind"] == "probate" else None
    return {
        "matter": _public(row, full=True),
        "answers": None if not compiled else compiled["answers"],
        "notice": "Export for the firm's own file. It is not a filing with the court or with HMRC.",
    }


@router.post("/matters/{matter_id}/uploads")
async def upload_paper(matter_id: str, request: Request, file: UploadFile = File(...), kind: str = Form(""), staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if len(_papers(matter_id)) >= MAX_PAPERS:
        raise HTTPException(400, f"You can keep up to {MAX_PAPERS} papers on a matter")
    filename = re.sub(r"[^\w.\- ]", "_", Path(file.filename or "document").name)[:120] or "document"
    if Path(filename).suffix.lower() not in PAPER_EXT:
        raise HTTPException(400, "Upload a PDF, Word file, text file or photo")
    data = await file.read(MAX_PAPER_BYTES + 1)
    if not data or len(data) > MAX_PAPER_BYTES:
        raise HTTPException(400, "The file is empty or over 10 MB")
    text_, read_as = extract_text(filename, file.content_type or "", data)
    detected = detect_kind(text_)
    kind_map = {"Old will": "Will", "Death certificate": "Death certificate", "Codicil": "Codicil"}
    chosen = kind if kind in PAPER_KINDS else kind_map.get(detected or "", "Other")
    upload_id = new_id()
    found = suggest("probate" if row["kind"] == "probate" else row["kind"], text_, upload_id, filename)
    with engine().begin() as conn:
        conn.execute(insert(matter_uploads).values(
            id=upload_id, matter_id=matter_id, filename=filename, content_type=file.content_type or "application/octet-stream",
            kind=chosen, size=len(data), data=data, text=text_, read_as=read_as, suggestions=found, created_at=now(),
        ))
    audit("matter_upload", staff, "matter", matter_id, {"filename": filename, "kind": chosen}, client_ip(request))
    return [p for p in _papers(matter_id) if p["id"] == upload_id][0]


@router.get("/matters/{matter_id}/uploads/{upload_id}")
def download_paper(matter_id: str, upload_id: str, _staff: dict = Depends(require_staff)):
    _load(matter_id)
    with engine().connect() as conn:
        row = conn.execute(select(matter_uploads).where(matter_uploads.c.id == upload_id, matter_uploads.c.matter_id == matter_id)).mappings().first()
    if not row:
        raise HTTPException(404, "Paper not found")
    return Response(row["data"], media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{row["filename"]}"', "X-Content-Type-Options": "nosniff"})


@router.delete("/matters/{matter_id}/uploads/{upload_id}")
def delete_paper(matter_id: str, upload_id: str, request: Request, staff: dict = Depends(require_staff)):
    _load(matter_id)
    with engine().begin() as conn:
        n = conn.execute(delete(matter_uploads).where(matter_uploads.c.id == upload_id, matter_uploads.c.matter_id == matter_id)).rowcount
    if not n:
        raise HTTPException(404, "Paper not found")
    audit("matter_upload_deleted", staff, "matter", matter_id, {"upload_id": upload_id}, client_ip(request))
    return {"ok": True}


@router.post("/matters/{matter_id}/apply")
def apply_papers(matter_id: str, body: ApplyIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if not body.suggestion_ids:
        raise HTTPException(400, "Choose what to add to the estate")
    wanted = set(body.suggestion_ids)
    chosen = []
    for paper in _papers(matter_id):
        for item in paper.get("suggestions") or []:
            if not wanted or item.get("id") in wanted:
                if item.get("mode") != "note" or str(item.get("label") or "").startswith("Executor named"):
                    chosen.append(item)
    if wanted:
        chosen = [item for item in chosen if item.get("id") in wanted]
    facts = dict(row["facts"] or {})
    books, fields = apply_suggestions(row, clean_books(facts.get("books")), chosen)
    facts["books"] = clean_books(books)
    values = {"facts": facts, "updated_at": now(), **{k: v for k, v in fields.items() if k in ("deceased_name", "date_of_death")}}
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(**values))
        fresh = dict(row)
        fresh.update(values)
        if fresh["kind"] == "probate" and fresh["draft_id"]:
            compiled = compile_books(fresh)
            draft = conn.execute(select(drafts.c.answers).where(drafts.c.id == fresh["draft_id"])).scalar()
            answers = dict(draft or {})
            answers.update(compiled["answers"])
            conn.execute(update(drafts).where(drafts.c.id == fresh["draft_id"]).values(answers=answers, updated_at=now()))
    audit("matter_applied", staff, "matter", matter_id, {"count": len(chosen)}, client_ip(request))
    return _public(_load(matter_id), full=True)


@router.get("/matters/{matter_id}/pack")
def matter_pack(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if row["kind"] != "probate":
        raise HTTPException(400, "The working pack is for a probate matter")
    compiled = compile_books(row)
    papers = _papers(matter_id)
    where = position(row, compiled, papers)
    pdf = render_pdf(pack_document(row, compiled, papers, where))
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name} working pack.pdf"'})


@router.get("/matters/{matter_id}/account.pdf")
def account_pdf(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row)
    if not compiled.get("accounts"):
        raise HTTPException(400, "The estate account is for a probate matter")
    pdf = render_pdf(account_document(row, compiled["accounts"]))
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name} estate account.pdf"'})


@router.get("/matters/{matter_id}/iht400.pdf")
def iht400_pdf(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row)
    figures = compiled.get("figures") or {}
    if not figures or figures.get("excepted"):
        raise HTTPException(400, "These answers do not ask for an IHT400")
    try:
        pdf, _missing = fill_iht400(row, compiled)
    except FileNotFoundError as exc:
        raise HTTPException(500, str(exc)) from exc
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name} IHT400.pdf"'})


@router.post("/iht400/refresh")
def refresh_iht400(_admin: dict = Depends(require_admin)):
    try:
        url = refresh_official_form()
    except Exception as exc:
        raise HTTPException(502, "GOV.UK did not return a new IHT400") from exc
    return {"ok": True, "source": url}


@router.get("/matters/{matter_id}/account.html")
def account_edit(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row)
    if not compiled.get("accounts"):
        raise HTTPException(400, "The estate account is for a probate matter")
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    html = account_html(row, compiled["accounts"])
    return HTMLResponse(html, headers={"Content-Disposition": f'attachment; filename="{name} estate account.html"'})


@router.get("/matters/{matter_id}/search")
def search_matter(matter_id: str, q: str = "", _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    needle = q.strip().lower()
    if len(needle) < 2:
        raise HTTPException(400, "Type at least two letters")
    compiled = compile_books(row)
    items = []
    for line in (compiled["books"].get("lines") or []):
        blob = f"{line['name']} {line['holder']}".lower()
        if needle in blob:
            items.append({"where": "The list", "label": line["name"], "detail": line["holder"]})
    papers = []
    with engine().connect() as conn:
        stored = conn.execute(select(matter_uploads.c.filename, matter_uploads.c.kind, matter_uploads.c.text).where(matter_uploads.c.matter_id == matter_id)).mappings().all()
    for paper in stored:
        text = paper["text"] or ""
        at = text.lower().find(needle)
        if at < 0:
            continue
        start = max(0, at - 40)
        papers.append({"filename": paper["filename"], "kind": paper["kind"], "snippet": text[start:at + 80].replace("\n", " ")})
    return {"items": items, "papers": papers}


@router.post("/matters/{matter_id}/draft")
def matter_draft(matter_id: str, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if row["draft_id"]:
        with engine().connect() as conn:
            existing = conn.execute(select(drafts.c.id).where(drafts.c.id == row["draft_id"])).first()
        if existing:
            return {"draft_id": row["draft_id"]}
    did = new_id()
    stamp = now()
    name = row["client_name"] or row["deceased_name"] or "Client"
    with engine().begin() as conn:
        conn.execute(insert(drafts).values(
            id=did, service=row["kind"], client_name=name, client_email=row["client_email"] or None,
            answers={}, status="draft", created_at=stamp, updated_at=stamp, user_id=staff["id"],
        ))
        conn.execute(update(matters).where(matters.c.id == matter_id).values(draft_id=did, updated_at=stamp))
    audit("matter_draft", staff, "matter", matter_id, {"draft_id": did}, client_ip(request))
    return {"draft_id": did}


@router.get("/colleagues")
def colleagues(_staff: dict = Depends(require_staff)):
    with engine().connect() as conn:
        rows = conn.execute(select(users.c.id, users.c.email, users.c.role).where(users.c.role.in_(("staff", "admin"))).order_by(users.c.email)).mappings().all()
    return [dict(r) for r in rows]


@router.post("/colleagues")
def add_colleague(body: ColleagueIn, request: Request, admin: dict = Depends(require_admin)):
    email = normalise_email(body.email)
    check_password_rules(body.password, email)
    with engine().begin() as conn:
        if conn.execute(select(users.c.id).where(users.c.email == email)).first():
            raise HTTPException(409, "That email already has an account. An admin can change the role from the admin page.")
        uid = new_id()
        conn.execute(insert(users).values(id=uid, email=email, password_hash=hash_password(body.password), role="staff", created_at=now()))
    audit("staff_created", admin, "user", uid, {"email": email}, client_ip(request))
    return {"id": uid, "email": email, "role": "staff"}


def public_probate_prepare():
    return client_prepare("probate")
