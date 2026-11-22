"""Firm desk. Staff and admins only. Clients of the public site cannot open it."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import insert, select, update

from .auth import require_admin, require_staff
from .db import drafts, engine, matters, new_id, now, users
from .documents import find_issues, missing_fields
from .firm_books import clean_books, compile_books, letter_text
from .firm_work import ITEM_STATUS, MATTER_STATUS, assist, checklist, client_prepare, deadlines, next_item, progress
from .guides import SERVICES
from .security import audit, client_ip, hash_password, normalise_email, check_password_rules

router = APIRouter(prefix="/api/firm")


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
    return out


def _draft_check(draft_id: str | None) -> dict | None:
    if not draft_id:
        return None
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row:
        return {"missing": [], "issues": [], "detail": "The linked draft has been deleted. Open a new one."}
    return {"missing": missing_fields(row["service"], row["answers"]), "issues": find_issues(row["service"], row["answers"], ""), "detail": ""}


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
    if body.kind not in ("bank", "beneficiary", "grant"):
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
