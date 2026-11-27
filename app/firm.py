"""Firm desk. Staff and admins only. Clients of the public site cannot open it."""
import io
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, delete, insert, select, update

from .auth import require_admin, require_staff
from .actionstep import deceased_name, fetch_actions, fetch_people, guess_kind, merge_connection, public_connection, refresh_connection
from .db import draft_versions, drafts, engine, firm_settings, matter_uploads, matters, new_id, now, users
from .documents import build_document, client_summary, find_issues, missing_fields, summary_text
from .extract import detect_kind, extract_text, suggest
from .firm_books import clean_books, compile_books, letter_text
from .docx_out import render_docx
from .mailer import send as send_mail
from .firm_account import account_document, account_html, account_xlsx, prepare_asset_search
from .iht400_pdf import fill_iht400, refresh_official_form
from .iht_schedules import schedule_files
from .firm_file import PAPER_KINDS, apply_suggestions, filing_record, pack_document, position
from .firm_practice import clean_practice, conflicts as name_conflicts, search_names
from .firm_accounts import bill_summary, clean_bill
from .firm_client import clean_client_account, post_entry, reconcile, record_breach, residuals, set_statement, sign_off
from .firm_today import add_appointment, add_task, clean_work, find as find_desk, set_task, today as practice_today
from .outlook import fetch_mailbox, fetch_message, merge_outlook, public_outlook
from .firm_trust import clean_deputy, clean_trust
from .firm_work import FIRM_KINDS, ITEM_STATUS, MATTER_STATUS, assist, checklist, client_prepare, deadlines, next_item, progress
from .guides import SERVICES
from .pdf import render_pdf
from .retainer import clean_retainer, document as retainer_document, effect as retainer_effect
from .lexcel import clean_saved as clean_lexcel
from .lexcel import for_matter as lexcel_for_matter
from .scheme import clean_saved, for_matter
from .source_watch import public_watch, run_check
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
    practice: dict | None = None
    bill: dict | None = None
    trust: dict | None = None
    deputy: dict | None = None


class ApplyIn(BaseModel):
    suggestion_ids: list[str] = Field(default_factory=list)


class LetterIn(BaseModel):
    kind: str


class VersionIn(BaseModel):
    label: str = "Kept"
    note: str = ""


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
        "kind_label": FIRM_KINDS.get(kind) or (SERVICES[kind]["short_title"] if kind in SERVICES else kind),
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
        "bill": bill_summary(clean_bill(facts.get("bill"))),
        "work": clean_work(facts.get("work")),
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
        out["practice"] = clean_practice(facts.get("practice"))
        out["scheme"] = for_matter(kind, facts.get("wiqs"))
        out["lexcel"] = lexcel_for_matter(facts.get("lexcel"))
        record = clean_retainer(facts.get("retainer"))
        out["retainer"] = {**record, "effect": retainer_effect(record, kind if kind in record["sections"] else "will")}
        out["watch"] = public_watch()
        out["bill_entries"] = clean_bill(facts.get("bill"))["entries"]
        if kind == "trust":
            out["trust"] = clean_trust(facts.get("trust"))
        if kind == "deputyship":
            out["deputy"] = clean_deputy(facts.get("deputy"))
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
    return [{"id": s["id"], "label": s.get("short_title") or s["title"], "title": s["title"]} for s in SERVICES.values()] + [
        {"id": key, "label": label, "title": label} for key, label in FIRM_KINDS.items()
    ]


class ClientEntryIn(BaseModel):
    kind: str
    on: str = ""
    matter_id: str = ""
    what: str = ""
    amount: float = 0
    reference: str = ""


class ClientStatementIn(BaseModel):
    on: str = ""
    balance: float = 0
    unpresented: float = 0
    outstanding: float = 0


class OutlookIn(BaseModel):
    access_token: str = ""


class OutlookFileIn(BaseModel):
    message_id: str
    matter_id: str


def _client_book() -> dict:
    with engine().connect() as conn:
        row = conn.execute(select(firm_settings.c.value).where(firm_settings.c.key == "client_account")).scalar()
    return clean_client_account(row if isinstance(row, dict) else {})


def _save_client_book(book: dict) -> None:
    with engine().begin() as conn:
        exists = conn.execute(select(firm_settings.c.key).where(firm_settings.c.key == "client_account")).first()
        if exists:
            conn.execute(update(firm_settings).where(firm_settings.c.key == "client_account").values(value=book))
        else:
            conn.execute(insert(firm_settings).values(key="client_account", value=book))


def _matter_titles() -> dict[str, str]:
    with engine().connect() as conn:
        rows = conn.execute(select(matters.c.id, matters.c.title)).mappings().all()
    return {row["id"]: row["title"] for row in rows}


def _outlook() -> dict:
    with engine().connect() as conn:
        row = conn.execute(select(firm_settings.c.value).where(firm_settings.c.key == "outlook")).scalar()
    return row if isinstance(row, dict) else {}


def _save_outlook(value: dict) -> None:
    with engine().begin() as conn:
        exists = conn.execute(select(firm_settings.c.key).where(firm_settings.c.key == "outlook")).first()
        if exists:
            conn.execute(update(firm_settings).where(firm_settings.c.key == "outlook").values(value=value))
        else:
            conn.execute(insert(firm_settings).values(key="outlook", value=value))


@router.get("/client-account")
def client_account(_staff: dict = Depends(require_staff)):
    titles = _matter_titles()
    return {"matters": [{"id": key, "title": title} for key, title in titles.items()], **reconcile(_client_book(), titles)}


@router.post("/client-account/entries")
def client_entry(body: ClientEntryIn, request: Request, staff: dict = Depends(require_staff)):
    titles = _matter_titles()
    try:
        book = post_entry(_client_book(), body.model_dump(), set(titles))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_client_book(book)
    posted = book["entries"][-1]
    if posted["kind"] == "transfer":
        row = _load(posted["matter_id"])
        facts = dict(row["facts"] or {})
        bill = clean_bill(facts.get("bill"))
        bill["entries"].append({
            "id": posted["id"],
            "kind": "paid",
            "on": posted["on"],
            "what": "From the client account: " + posted["what"],
            "hours": 0,
            "rate": 0,
            "amount": posted["amount"],
        })
        facts["bill"] = bill
        with engine().begin() as conn:
            conn.execute(update(matters).where(matters.c.id == posted["matter_id"]).values(facts=facts, updated_at=now()))
    audit("client_money", staff, "matter", posted["matter_id"], {"kind": posted["kind"], "amount": posted["amount"]}, client_ip(request))
    return reconcile(book, titles)


@router.put("/client-account/statement")
def client_statement(body: ClientStatementIn, request: Request, staff: dict = Depends(require_staff)):
    book = set_statement(_client_book(), body.model_dump())
    _save_client_book(book)
    audit("client_statement", staff, "firm", "client_account", {"balance": book["statement"]["balance"]}, client_ip(request))
    return reconcile(book, _matter_titles())


class NoteIn(BaseModel):
    note: str = ""


@router.post("/client-account/sign-off")
def client_sign_off(body: NoteIn, request: Request, staff: dict = Depends(require_staff)):
    titles = _matter_titles()
    try:
        book = sign_off(_client_book(), titles, staff["email"], now().isoformat(), body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_client_book(book)
    audit("client_signoff", staff, "firm", "client_account", {}, client_ip(request))
    return reconcile(book, titles)


@router.post("/client-account/breach")
def client_breach(body: NoteIn, request: Request, staff: dict = Depends(require_staff)):
    titles = _matter_titles()
    try:
        book = record_breach(_client_book(), titles, staff["email"], now().isoformat(), body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_client_book(book)
    audit("client_breach", staff, "firm", "client_account", {}, client_ip(request))
    return reconcile(book, titles)


def _rows():
    with engine().connect() as conn:
        rows = conn.execute(select(matters).order_by(matters.c.updated_at.desc())).mappings().all()
    return [_public(dict(row)) for row in rows]


@router.get("/today")
def firm_today(_staff: dict = Depends(require_staff)):
    rows = _rows()
    titles = {row["id"]: row["title"] for row in rows}
    client = reconcile(_client_book(), titles)
    left = residuals(client["ledgers"], {row["id"]: row["status"] for row in rows})
    return practice_today(rows, client, left)


@router.get("/find")
def firm_find(q: str = "", _staff: dict = Depends(require_staff)):
    return {"hits": find_desk(q, _rows())}


class TaskIn(BaseModel):
    title: str = ""
    due: str = ""
    who: str = ""
    done: bool = False


class AppointmentIn(BaseModel):
    title: str
    on: str = ""
    time: str = ""
    where: str = ""


def _save_work(matter_id: str, work: dict) -> dict:
    row = _load(matter_id)
    facts = dict(row["facts"] or {})
    facts["work"] = work
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    return _public(_load(matter_id), full=True)


@router.post("/matters/{matter_id}/tasks")
def matter_task(matter_id: str, body: TaskIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    try:
        work = add_task((row["facts"] or {}).get("work"), body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit("task", staff, "matter", matter_id, {"title": body.title[:80]}, client_ip(request))
    return {"matter": _save_work(matter_id, work)}


@router.post("/matters/{matter_id}/tasks/{task_id}")
def matter_task_done(matter_id: str, task_id: str, body: TaskIn, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    try:
        work = set_task((row["facts"] or {}).get("work"), task_id, body.done)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"matter": _save_work(matter_id, work)}


@router.post("/matters/{matter_id}/appointments")
def matter_appointment(matter_id: str, body: AppointmentIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    try:
        work = add_appointment((row["facts"] or {}).get("work"), body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit("appointment", staff, "matter", matter_id, {"title": body.title[:80]}, client_ip(request))
    return {"matter": _save_work(matter_id, work)}


@router.get("/outlook")
def outlook_status(_staff: dict = Depends(require_staff)):
    return public_outlook(_outlook())


@router.put("/outlook")
def outlook_save(body: OutlookIn, request: Request, admin: dict = Depends(require_admin)):
    try:
        saved = merge_outlook(_outlook(), body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_outlook(saved)
    audit("outlook_connected", admin, "firm", "outlook", {}, client_ip(request))
    return public_outlook(saved)


@router.post("/outlook/mailbox")
def outlook_mailbox(_staff: dict = Depends(require_staff)):
    saved = _outlook()
    if not saved.get("access_token"):
        raise HTTPException(400, "Outlook is not connected")
    try:
        return fetch_mailbox(saved["access_token"])
    except PermissionError as exc:
        raise HTTPException(401, "Outlook refused the token. An admin needs to paste a new one.") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/outlook/file")
def outlook_file(body: OutlookFileIn, request: Request, staff: dict = Depends(require_staff)):
    saved = _outlook()
    if not saved.get("access_token"):
        raise HTTPException(400, "Outlook is not connected")
    matter_id = body.matter_id.strip()
    if matter_id not in _matter_titles():
        raise HTTPException(404, "Choose a matter")
    try:
        message = fetch_message(saved["access_token"], body.message_id)
    except PermissionError as exc:
        raise HTTPException(401, "Outlook refused the token. An admin needs to paste a new one.") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc
    row = _load(matter_id)
    facts = dict(row["facts"] or {"items": {}, "notes": []})
    text = f"Outlook: {message['subject']} from {message['from']} on {message['on']}. {message['preview']}".strip()
    facts.setdefault("notes", []).append({"at": now().isoformat(), "by": staff["email"], "text": text[:4000]})
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("outlook_filed", staff, "matter", matter_id, {"subject": message["subject"][:120]}, client_ip(request))
    return {"filed": True, "subject": message["subject"]}


@router.get("/accounts")
def firm_accounts(_staff: dict = Depends(require_staff)):
    with engine().connect() as conn:
        rows = conn.execute(select(matters).order_by(matters.c.updated_at.desc())).mappings().all()
    matters_out = []
    totals = {"unbilled": 0.0, "billed": 0.0, "paid": 0.0, "outstanding": 0.0}
    for row in rows:
        item = _public(dict(row))
        matters_out.append({"id": item["id"], "title": item["title"], "client_name": item["client_name"], "kind_label": item["kind_label"], "bill": item["bill"]})
        for key in totals:
            totals[key] = round(totals[key] + item["bill"][key], 2)
    return {"totals": totals, "matters": matters_out}


class ActionstepIn(BaseModel):
    api_endpoint: str = ""
    access_token: str = ""
    refresh_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    orgkey: str = ""


class ActionstepImport(BaseModel):
    action_id: str


def _actionstep() -> dict:
    with engine().connect() as conn:
        row = conn.execute(select(firm_settings.c.value).where(firm_settings.c.key == "actionstep")).scalar()
    return row if isinstance(row, dict) else {}


def _save_actionstep(value: dict) -> None:
    with engine().begin() as conn:
        exists = conn.execute(select(firm_settings.c.key).where(firm_settings.c.key == "actionstep")).first()
        if exists:
            conn.execute(update(firm_settings).where(firm_settings.c.key == "actionstep").values(value=value))
        else:
            conn.execute(insert(firm_settings).values(key="actionstep", value=value))


def _matter_for_action(action_id: str) -> str | None:
    with engine().connect() as conn:
        rows = conn.execute(select(matters.c.id, matters.c.facts)).mappings().all()
    for row in rows:
        link = ((row["facts"] or {}).get("actionstep") or {})
        if str(link.get("id") or "") == str(action_id):
            return row["id"]
    return None


@router.get("/actionstep")
def actionstep_status(_staff: dict = Depends(require_staff)):
    return public_connection(_actionstep())


@router.put("/actionstep")
def actionstep_save(body: ActionstepIn, request: Request, admin: dict = Depends(require_admin)):
    try:
        saved = merge_connection(_actionstep(), body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_actionstep(saved)
    audit("actionstep_connected", admin, "firm", "actionstep", {"endpoint": saved.get("api_endpoint")}, client_ip(request))
    return public_connection(saved)


def _actions_or_refresh(saved: dict) -> tuple[dict, list]:
    try:
        return saved, fetch_actions(saved)
    except PermissionError:
        if not (saved.get("refresh_token") and saved.get("client_id") and saved.get("client_secret")):
            raise
        saved = refresh_connection(saved)
        _save_actionstep(saved)
        return saved, fetch_actions(saved)


@router.post("/actionstep/matters")
def actionstep_matters(_staff: dict = Depends(require_staff)):
    saved = _actionstep()
    if not saved.get("access_token"):
        raise HTTPException(400, "Actionstep is not connected")
    try:
        _saved, rows = _actions_or_refresh(saved)
    except PermissionError as exc:
        raise HTTPException(401, "Actionstep refused the token. An admin needs to paste a new one.") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"matters": rows}


@router.post("/actionstep/import")
def actionstep_import(body: ActionstepImport, request: Request, staff: dict = Depends(require_staff)):
    action_id = body.action_id.strip()
    if not action_id:
        raise HTTPException(400, "Choose a matter")
    already = _matter_for_action(action_id)
    if already:
        return _public(_load(already), full=True)
    saved = _actionstep()
    if not saved.get("access_token"):
        raise HTTPException(400, "Actionstep is not connected")
    try:
        saved, rows = _actions_or_refresh(saved)
        match = next((row for row in rows if row["id"] == action_id), None)
        if not match:
            raise HTTPException(404, "That matter is not in the Actionstep list")
        people = fetch_people(saved, action_id)
    except PermissionError as exc:
        raise HTTPException(401, "Actionstep refused the token. An admin needs to paste a new one.") from exc
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc
    kind = guess_kind(match["name"])
    client = people[0] if people else {"name": "", "email": ""}
    died = deceased_name(match["name"], people) if kind == "probate" else ""
    title = match["name"] or (f"Estate of {died}" if died else "Matter from Actionstep")
    mid = new_id()
    stamp = now()
    facts = {"items": {}, "notes": [], "actionstep": {"id": action_id, "reference": match["reference"], "status": match["status"]}}
    with engine().begin() as conn:
        conn.execute(insert(matters).values(
            id=mid, kind=kind, title=title[:160], status="open",
            client_name=client.get("name") or "", client_email=client.get("email") or "",
            deceased_name=died, date_of_death="", grant_date="", facts=facts, draft_id=None,
            opened_by=staff["id"], created_at=stamp, updated_at=stamp,
        ))
    audit("actionstep_imported", staff, "matter", mid, {"action_id": action_id}, client_ip(request))
    return _public(_load(mid), full=True)


@router.get("/matters")
def list_matters(_staff: dict = Depends(require_staff)):
    with engine().connect() as conn:
        rows = conn.execute(select(matters).order_by(matters.c.updated_at.desc())).mappings().all()
    return [_public(dict(r)) for r in rows]


@router.post("/matters")
def open_matter(body: MatterIn, request: Request, staff: dict = Depends(require_staff)):
    if body.kind not in SERVICES and body.kind not in FIRM_KINDS:
        raise HTTPException(400, "Unknown matter type")
    title = body.title.strip() or (SERVICES[body.kind]["title"] if body.kind in SERVICES else FIRM_KINDS[body.kind])
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


@router.get("/matters/{matter_id}/conflicts")
def matter_conflicts(matter_id: str, q: str = "", _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    with engine().connect() as conn:
        others = conn.execute(select(matters.c.id, matters.c.title, matters.c.kind, matters.c.client_name, matters.c.deceased_name)).mappings().all()
    people = [dict(other) for other in others]
    matches = search_names(q, row, people) if q.strip() else name_conflicts(row, people)
    return {"matches": matches, "q": q}


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
    if body.practice is not None:
        facts["practice"] = clean_practice(body.practice)
    if body.bill is not None:
        facts["bill"] = clean_bill(body.bill)
    if body.trust is not None:
        facts["trust"] = clean_trust(body.trust)
    if body.deputy is not None:
        facts["deputy"] = clean_deputy(body.deputy)
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


class SchemeIn(BaseModel):
    done: list[str] = []
    last_report: str = ""


@router.post("/matters/{matter_id}/scheme")
def save_scheme(matter_id: str, body: SchemeIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    facts = dict(row["facts"] or {})
    facts["wiqs"] = clean_saved(body.done, body.last_report)
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("scheme", staff, "matter", matter_id, {"done": len(facts["wiqs"]["done"])}, client_ip(request))
    return {"matter": _public(_load(matter_id), full=True)}


class LexcelIn(BaseModel):
    done: list[str] | None = None
    quote: dict | None = None
    conflict_q: str | None = None


@router.post("/matters/{matter_id}/lexcel")
def save_lexcel(matter_id: str, body: LexcelIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    facts = dict(row["facts"] or {})
    facts["lexcel"] = clean_lexcel(body.done, body.quote, facts.get("lexcel"), body.conflict_q)
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("lexcel", staff, "matter", matter_id, {"done": len(facts["lexcel"]["done"])}, client_ip(request))
    return {"matter": _public(_load(matter_id), full=True)}


class MatterRetainerIn(BaseModel):
    place: str = ""
    signed_on: str = ""
    signed_name: str = ""
    finished: bool = False


@router.post("/matters/{matter_id}/retainer")
def save_matter_retainer(matter_id: str, body: MatterRetainerIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    facts = dict(row["facts"] or {})
    existing = clean_retainer(facts.get("retainer"))
    finished = [item for item in existing["finished"] if item != row["kind"]]
    if body.finished and row["kind"] not in finished:
        finished.append(row["kind"])
    record = clean_retainer({**body.model_dump(), "finished": finished})
    if not record["signed"]:
        raise HTTPException(400, "Enter the client’s name, the date, and where the retainer was signed.")
    facts["retainer"] = record
    with engine().begin() as conn:
        conn.execute(update(matters).where(matters.c.id == matter_id).values(facts=facts, updated_at=now()))
    audit("matter_retainer", staff, "matter", matter_id, {"place": record["place"], "finished": body.finished}, client_ip(request))
    return {"matter": _public(_load(matter_id), full=True)}


@router.post("/source-check")
def source_check(_staff: dict = Depends(require_staff)):
    """Read the official pages now. A change is recorded. Clauses are not rewritten."""
    result = run_check()
    return {
        "checked_at": result.get("checked_at"),
        "found": result.get("found") or [],
        "failed": result.get("failed") or [],
        "watch": public_watch(),
    }


@router.post("/matters/{matter_id}/letters")
def keep_letter(matter_id: str, body: LetterIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    if body.kind not in ("bank", "beneficiary", "grant", "notice", "credit", "estatesearch", "will_ipw", "will_sww", "will_probate", "will_local", "pension", "act1975", "golden", "couple", "file_summary", "old_will", "retainer", "lex_care", "lex_quote", "lex_progress", "lex_change", "lex_complaint", "lex_review", "lex_undertaking", "lex_conflict"):
        raise HTTPException(400, "Unknown letter")
    compiled = compile_books(row)
    if body.kind == "lex_conflict":
        saved = (row.get("facts") or {}).get("lexcel") or {}
        with engine().connect() as conn:
            others = conn.execute(select(matters.c.id, matters.c.title, matters.c.kind, matters.c.client_name, matters.c.deceased_name)).mappings().all()
        row = {**row, "_conflict_matches": search_names(saved.get("conflict_q") or row.get("client_name") or "", row, [dict(other) for other in others])}
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


def _as_document(title: str, body: str) -> dict:
    paragraphs = [line for line in body.splitlines() if line.strip()]
    return {
        "title": title,
        "notice": "Draft for the file. Nothing has been sent from this desk. It does not stop a claim and it does not make the firm immune.",
        "sections": [{"heading": title, "paragraphs": paragraphs or [body]}],
        "next_steps": ["The firm checks this and sends it, if it is a letter. The desk does not send it."],
        "sources": [],
    }


def _letter_file(matter_id: str, letter_id: str, kind: str):
    row = _load(matter_id)
    books = clean_books((row.get("facts") or {}).get("books"))
    letter = next((item for item in books["letters"] if item["id"] == letter_id), None)
    if not letter:
        raise HTTPException(404, "That letter is not on the file")
    stem = f"letter-{letter_id}"
    document = _as_document(letter["title"], letter["body"])
    if kind == "docx":
        return Response(render_docx(document), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'})
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'})


@router.get("/matters/{matter_id}/letters/{letter_id}.pdf")
def letter_pdf(matter_id: str, letter_id: str, _staff: dict = Depends(require_staff)):
    return _letter_file(matter_id, letter_id, "pdf")


@router.get("/matters/{matter_id}/letters/{letter_id}.docx")
def letter_docx(matter_id: str, letter_id: str, _staff: dict = Depends(require_staff)):
    return _letter_file(matter_id, letter_id, "docx")


def _linked_draft(row: dict):
    if not row.get("draft_id"):
        raise HTTPException(400, "This matter has no client draft yet. Start the draft from the file first.")
    with engine().connect() as conn:
        draft = conn.execute(select(drafts).where(drafts.c.id == row["draft_id"])).mappings().first()
    if not draft:
        raise HTTPException(404, "The linked draft is not on the file")
    return draft


def _draft_document(row: dict):
    draft = _linked_draft(row)
    if draft["service"] not in SERVICES:
        raise HTTPException(400, "This matter is not linked to a will, lasting power, probate or agreement draft.")
    with engine().connect() as conn:
        stored = conn.execute(select(matter_uploads.c.text).where(matter_uploads.c.matter_id == row["id"])).scalars().all()
    from .db import uploads as upload_table
    with engine().connect() as conn:
        texts = conn.execute(select(upload_table.c.filename, upload_table.c.kind, upload_table.c.text).where(upload_table.c.draft_id == draft["id"])).mappings().all()
    ups = [{"filename": item["filename"], "kind": item["kind"], "text": item["text"] or ""} for item in texts]
    ups += [{"filename": "matter paper", "kind": "Other", "text": text or ""} for text in stored]
    return draft, build_document(draft["service"], draft["answers"] or {}, ups)


@router.get("/matters/{matter_id}/draft.pdf")
def matter_draft_pdf(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    _, document = _draft_document(row)
    name = (row.get("client_name") or "draft").replace(" ", "-")
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})


@router.get("/matters/{matter_id}/draft.docx")
def matter_draft_docx(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    _, document = _draft_document(row)
    name = (row.get("client_name") or "draft").replace(" ", "-")
    return Response(render_docx(document), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{name}.docx"'})


@router.get("/matters/{matter_id}/summary.pdf")
def matter_summary_pdf(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    draft, document = _draft_document(row)
    summary = client_summary(draft["service"], draft["answers"] or {}, document, document.get("issues") or [])
    name = (row.get("client_name") or "client").replace(" ", "-")
    return Response(render_pdf(summary), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="summary-{name}.pdf"'})


@router.post("/matters/{matter_id}/summary-email")
def matter_summary_email(matter_id: str, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    to = (row.get("client_email") or "").strip()
    draft, document = _draft_document(row)
    summary = client_summary(draft["service"], draft["answers"] or {}, document, document.get("issues") or [])
    if "@" not in to:
        return {"sent": False, "how": "none", "message": "There is no client email on this matter. Download the summary and send it yourself. Nothing was sent."}
    how = send_mail(to, summary["title"], summary_text(summary))
    audit("summary_email", staff, "matter", matter_id, {"how": how}, client_ip(request))
    if how in ("resend", "smtp"):
        return {"sent": True, "how": how, "message": f"The summary was emailed to {to}. Sending it does not stop a claim."}
    return {"sent": False, "how": how, "message": f"Email is not switched on, so nothing was sent to {to}. Download the summary PDF and send it from the firm’s own email."}


@router.get("/matters/{matter_id}/versions")
def matter_versions(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    draft = _linked_draft(row)
    with engine().connect() as conn:
        rows = conn.execute(select(draft_versions.c.id, draft_versions.c.number, draft_versions.c.label, draft_versions.c.note, draft_versions.c.created_at)
                            .where(draft_versions.c.draft_id == draft["id"]).order_by(draft_versions.c.number)).mappings().all()
    return [{"id": item["id"], "number": item["number"], "label": item["label"], "note": item["note"], "at": item["created_at"].isoformat()} for item in rows]


@router.post("/matters/{matter_id}/versions")
def matter_keep_version(matter_id: str, body: VersionIn, request: Request, staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    draft = _linked_draft(row)
    _, document = _draft_document(row)
    with engine().begin() as conn:
        current = conn.execute(select(func.max(draft_versions.c.number)).where(draft_versions.c.draft_id == draft["id"])).scalar() or 0
        number = int(current) + 1
        vid = new_id()
        conn.execute(insert(draft_versions).values(
            id=vid, draft_id=draft["id"], number=number, label=(body.label or "Kept")[:80], note=(body.note or "")[:1000],
            document=document, created_at=now(),
        ))
    audit("draft_version", staff, "matter", matter_id, {"number": number, "label": body.label}, client_ip(request))
    return {"id": vid, "number": number, "label": body.label or "Kept"}


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


@router.get("/matters/{matter_id}/account.xlsx")
def account_excel(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row)
    if not compiled.get("accounts"):
        raise HTTPException(400, "The estate account is for a probate matter")
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    return Response(account_xlsx(row, compiled["accounts"]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{name} estate account.xlsx"'})


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


@router.get("/matters/{matter_id}/schedules.zip")
def schedules_zip(matter_id: str, _staff: dict = Depends(require_staff)):
    row = _load(matter_id)
    compiled = compile_books(row)
    forms = compiled.get("forms") or {}
    if not forms or forms.get("excepted"):
        raise HTTPException(400, "These answers do not ask for the extra Inheritance Tax schedules")
    files = schedule_files(row, compiled["books"], choose_rows(compiled))
    if not files:
        raise HTTPException(400, "No extra schedule was chosen")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for code, pdf in files:
            archive.writestr(f"{code}.pdf", pdf)
    name = re.sub(r"[^\w.\- ]", "_", row["title"])[:80] or "estate"
    return Response(buf.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name} schedules.zip"'})


def choose_rows(compiled: dict) -> list[dict]:
    return [{"code": item["code"], "why": item["why"], "ready": item["ready"]} for item in (compiled.get("forms") or {}).get("chosen") or []]


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
