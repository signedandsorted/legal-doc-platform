from contextlib import asynccontextmanager
import copy
import hashlib
import os
import re
from pathlib import Path

import re

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import delete, func, insert, select, text, update

from .admin import router as admin_router
from .capacity import router as capacity_router
from .auth import require_user, router as auth_router, seed_admin, seed_staff, set_csrf_cookie
from .firm import public_probate_prepare, router as firm_router
from .probate_tools import router as probate_tools_router, stamp_insolvency_checks
from .db import draft_versions, drafts, engine, init_db, new_id, now, uploads, users
from .security import audit, client_ip, csrf_ok
from .documents import build_document, client_summary, find_issues, missing_fields, summary_text
from .mailer import send as send_mail
from .documents import save_uploaded_file
from .docx_out import render_docx
from .extract import detect_kind, extract_text, fill_from_papers, suggest
from .guides import SERVICES
from .law_updates import UPDATES
from .pdf import render_pdf
from .scheme import LINKS as SCHEME_LINKS
from .scheme import CANNOT as SCHEME_CANNOT
from .source_watch import public_watch, start_background
from .payments import describe, fetch_session, paid_record, quote, require_paid, start_checkout, webhook_event
from .retainer import SECTIONS, clean_retainer, document as retainer_document, effect as retainer_effect

STATIC = Path(__file__).resolve().parent.parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOADS_PER_DRAFT = 15
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".heic", ".webp"}


@asynccontextmanager
async def lifespan(_):
    init_db()
    seed_admin()
    seed_staff()
    start_background()
    yield


app = FastAPI(title="Legal Doc Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    if request.method in UNSAFE and request.url.path.startswith("/api/") and request.url.path != "/api/stripe/webhook" and not csrf_ok(request):
        return JSONResponse({"detail": "Your session has expired. Please refresh the page and try again."}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' blob: data: https://images.unsplash.com; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
    if request.url.path.startswith(("/api/", "/static/app.js", "/static/styles.css")) or request.url.path == "/" or "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    if request.method in {"GET", "HEAD"} and response.status_code == 200 and (
        request.url.path == "/" or request.url.path.startswith("/api/") or "text/html" in response.headers.get("content-type", "")
    ):
        set_csrf_cookie(response, request)
    return response


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(capacity_router)
app.include_router(firm_router)
app.include_router(probate_tools_router)


class DraftIn(BaseModel):
    service: str
    answers: dict = {}


class AnswersIn(BaseModel):
    answers: dict


@app.get("/healthz")
def healthz():
    with engine().connect() as conn:
        conn.execute(text("select 1"))
    return {"ok": True, "database": engine().dialect.name}


def app_shell() -> HTMLResponse:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("app.js", "styles.css"):
        ver = hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:12]
        html = re.sub(rf"/static/{re.escape(name)}(?:\?v=[^\"']*)?", f"/static/{name}?v={ver}", html)
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/")
def index():
    return app_shell()


@app.get("/firm")
def firm_page():
    html = (STATIC / "firm.html").read_text(encoding="utf-8")
    for name in ("firm.js", "firm.css", "styles.css"):
        ver = hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:12]
        html = re.sub(rf"/static/{re.escape(name)}(?:\?v=[^\"']*)?", f"/static/{name}?v={ver}", html)
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/api/services")
def services():
    return [{"id": s["id"], "title": s["title"], "summary": s["summary"], "steps": len(s["steps"]), "category": s.get("category", ""), "country": s.get("country", "gb"), "price": quote(s["id"])["label"]} for s in SERVICES.values() if not s.get("hidden")]


VIDEOS = STATIC / "videos"
MIN_VIDEO_BYTES = 20_000


def _asset(stem: str, ext: str) -> str | None:
    path = VIDEOS / f"{stem}.{ext}"
    if not path.is_file():
        return None
    if ext == "mp4" and path.stat().st_size < MIN_VIDEO_BYTES:
        return None
    stamp = int(path.stat().st_mtime)
    return f"/static/videos/{stem}.{ext}?v={stamp}"


def _presenter(video_id: str, presenter: str) -> dict | None:
    stem = f"{video_id}_{presenter}"
    src = _asset(stem, "mp4")
    poster = _asset(stem, "jpg")
    captions = _asset(stem, "vtt")
    if presenter == "female" and not src:
        src = _asset(video_id, "mp4")
        poster = poster or _asset(video_id, "jpg")
        captions = captions or _asset(video_id, "vtt")
    if not src:
        return None
    return {
        "id": presenter,
        "label": "Woman" if presenter == "female" else "Man",
        "src": src,
        "poster": poster or "",
        "captions": captions or "",
    }


def _video_obj(video_id):
    if not isinstance(video_id, str) or not video_id:
        return None
    presenters = [p for p in (_presenter(video_id, "female"), _presenter(video_id, "male")) if p]
    if not presenters:
        return None
    chosen = next((p for p in presenters if p["id"] == "female"), presenters[0])
    return {
        "id": video_id,
        "src": chosen["src"],
        "poster": chosen["poster"],
        "captions": chosen["captions"],
        "default_presenter": chosen["id"],
        "presenters": presenters,
    }


def _public_service(spec: dict) -> dict:
    out = copy.deepcopy(spec)
    for step in out.get("steps") or []:
        step["video"] = _video_obj(step.get("video"))
    if out.get("review_video"):
        out["review_video"] = _video_obj(out["review_video"])
    if spec.get("id") == "probate":
        out["prepare"] = public_probate_prepare()
    return out


@app.get("/api/services/{service_id}")
def service(service_id: str):
    if service_id not in SERVICES:
        raise HTTPException(404, "Unknown service")
    return _public_service(SERVICES[service_id])


def _client(answers: dict) -> tuple[str, str | None]:
    for key in ("about_you", "donor"):
        if answers.get(key):
            return answers[key].get("full_name") or "", answers[key].get("email")
    parties = answers.get("parties") or {}
    party = parties.get("party_a_name") or parties.get("employee_name") or ""
    if party:
        return party, parties.get("email")
    applicant = (answers.get("will") or {}).get("applicant") or {}
    return applicant.get("full_name") or "", applicant.get("email")


def _row(draft_id: str, user: dict):
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row or row["user_id"] != user["id"]:
        raise HTTPException(404, "Draft not found")
    return row


def _uploads(draft_id: str, with_text: bool = False) -> list[dict]:
    cols = [uploads.c.id, uploads.c.filename, uploads.c.content_type, uploads.c.kind, uploads.c.size, uploads.c.read_as, uploads.c.suggestions, uploads.c.created_at] + ([uploads.c.text] if with_text else [])
    with engine().connect() as conn:
        rows = conn.execute(select(*cols).where(uploads.c.draft_id == draft_id).order_by(uploads.c.created_at)).mappings().all()
    return [{**dict(r), "created_at": r["created_at"].isoformat()} for r in rows]


def _uploads_text(draft_id: str) -> str:
    return " ".join(u["text"] for u in _uploads(draft_id, True))


def _out(row) -> dict:
    ups = _uploads(row["id"])
    return {"id": row["id"], "service": row["service"], "answers": row["answers"], "status": row["status"], "missing": missing_fields(row["service"], row["answers"]),
            "issues": find_issues(row["service"], row["answers"], _uploads_text(row["id"]) if ups else ""), "uploads": ups, "updated_at": row["updated_at"].isoformat(),
            "payment": describe(row)}


@app.get("/api/drafts")
def my_drafts(user: dict = Depends(require_user)):
    with engine().connect() as conn:
        rows = conn.execute(select(drafts.c.id, drafts.c.service, drafts.c.client_name, drafts.c.status, drafts.c.updated_at)
                            .where(drafts.c.user_id == user["id"]).order_by(drafts.c.updated_at.desc())).mappings().all()
    return [{**dict(r), "title": SERVICES.get(r["service"], {}).get("title", r["service"]), "updated_at": r["updated_at"].isoformat()} for r in rows]


@app.post("/api/drafts")
def create_draft(body: DraftIn, request: Request, user: dict = Depends(require_user)):
    if body.service not in SERVICES:
        raise HTTPException(400, "Unknown service")
    name, email = _client(body.answers)
    draft_id = new_id()
    with engine().begin() as conn:
        conn.execute(insert(drafts).values(id=draft_id, user_id=user["id"], service=body.service, client_name=name, client_email=email, answers=body.answers, status="draft", created_at=now(), updated_at=now()))
    audit("draft_created", user, "draft", draft_id, {"service": body.service}, client_ip(request))
    return _out(_row(draft_id, user))


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str, user: dict = Depends(require_user)):
    return _out(_row(draft_id, user))


@app.put("/api/drafts/{draft_id}")
def save_draft(draft_id: str, body: AnswersIn, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    if row["status"] != "draft":
        raise HTTPException(409, "This draft has been sent for review and can no longer be changed")
    answers = stamp_insolvency_checks(row["answers"], body.answers) if row["service"] == "probate" else body.answers
    name, email = _client(answers)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(answers=answers, client_name=name, client_email=email, updated_at=now()))
    return _out(_row(draft_id, user))


def _complete(row):
    missing = missing_fields(row["service"], row["answers"])
    if missing:
        raise HTTPException(400, {"message": "Some answers are missing", "missing": missing})
    ups = _uploads(row["id"], True)
    errors = [i["message"] for i in find_issues(row["service"], row["answers"], " ".join(u["text"] for u in ups)) if i["level"] == "error"]
    if errors:
        raise HTTPException(400, {"message": "Some answers need changing", "missing": errors})
    return build_document(row["service"], row["answers"], ups)


@app.get("/api/drafts/{draft_id}/document")
def preview(draft_id: str, user: dict = Depends(require_user)):
    return _complete(_row(draft_id, user))


class VersionIn(BaseModel):
    label: str = "Kept"
    note: str = ""


def _file(document: dict, stem: str, kind: str):
    if kind == "docx":
        return Response(render_docx(document), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'})
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'})


def _keep_version(row: dict, label: str, note: str) -> dict:
    ups = _uploads(row["id"], True)
    try:
        document = build_document(row["service"], row["answers"], ups)
    except Exception:
        document = {"title": row["service"], "notice": "Incomplete draft", "sections": [], "next_steps": []}
    with engine().begin() as conn:
        current = conn.execute(select(func.max(draft_versions.c.number)).where(draft_versions.c.draft_id == row["id"])).scalar() or 0
        number = int(current) + 1
        vid = new_id()
        conn.execute(insert(draft_versions).values(
            id=vid, draft_id=row["id"], number=number, label=label[:80] or "Kept", note=(note or "")[:1000],
            document=document, created_at=now(),
        ))
    return {"id": vid, "number": number, "label": label}


class RetainerIn(BaseModel):
    place: str = ""
    signed_on: str = ""
    signed_name: str = ""


@app.get("/api/retainer")
def read_retainer(user: dict = Depends(require_user)):
    record = clean_retainer(user.get("retainer") or {})
    return {"retainer": record, "sections": [{"id": sid, "label": label, "effect": retainer_effect(record, sid)} for sid, label in SECTIONS]}


@app.post("/api/retainer")
def save_retainer(body: RetainerIn, request: Request, user: dict = Depends(require_user)):
    existing = clean_retainer(user.get("retainer") or {})
    record = clean_retainer({**body.model_dump(), "finished": existing["finished"]})
    if not record["signed"]:
        raise HTTPException(400, "Enter your name, the date, and where you are signing. The request is not recorded until all three are there.")
    with engine().begin() as conn:
        conn.execute(update(users).where(users.c.id == user["id"]).values(retainer=record))
    audit("retainer_signed", user, "user", user["id"], {"place": record["place"]}, client_ip(request))
    return {"retainer": record, "sections": [{"id": sid, "label": label, "effect": retainer_effect(record, sid)} for sid, label in SECTIONS]}


@app.get("/api/retainer.pdf")
def retainer_pdf(user: dict = Depends(require_user)):
    record = clean_retainer(user.get("retainer") or {})
    return _file(retainer_document(record, user.get("email") or ""), "request-to-start", "pdf")


@app.get("/api/law")
def law_updates():
    return {
        "updates": UPDATES,
        "note": "This is the firm’s own register. It is not updated by Parliament. A daily check reads the official pages and lists a change. A person then updates the desk. The check does not rewrite a clause.",
        "watch": public_watch(),
        "scheme": {
            "title": "Wills and Inheritance Quality Scheme",
            "cannot": SCHEME_CANNOT,
            "links": SCHEME_LINKS,
        },
    }


@app.get("/api/drafts/{draft_id}/summary.pdf")
def summary_pdf(draft_id: str, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    ups = _uploads(row["id"], True)
    document = build_document(row["service"], row["answers"], ups)
    issues = find_issues(row["service"], row["answers"], " ".join(u.get("text") or "" for u in ups))
    require_paid(row)
    name = (row["client_name"] or "client").replace(" ", "-")
    return _file(client_summary(row["service"], row["answers"], document, issues), f"summary-{name}", "pdf")


@app.post("/api/drafts/{draft_id}/summary-email")
def summary_email(draft_id: str, request: Request, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    ups = _uploads(row["id"], True)
    document = build_document(row["service"], row["answers"], ups)
    summary = client_summary(row["service"], row["answers"], document, document.get("issues") or [])
    require_paid(row)
    to = (row["client_email"] or "").strip()
    if "@" not in to:
        return {"sent": False, "how": "none", "message": "There is no email address on this draft. Download the summary and send it yourself. Nothing was sent."}
    how = send_mail(to, summary["title"], summary_text(summary))
    audit("summary_email", user, "draft", draft_id, {"how": how}, client_ip(request))
    if how in ("resend", "smtp"):
        return {"sent": True, "how": how, "message": f"The summary was emailed to {to}. Sending it does not stop a claim."}
    return {"sent": False, "how": how, "message": f"Email is not switched on for this desk, so nothing was sent to {to}. Download the summary PDF and send it from your own email."}


@app.get("/api/drafts/{draft_id}/docx")
def docx(draft_id: str, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    document = _complete(row)
    require_paid(row)
    return _file(document, f"{row['service']}-{(row['client_name'] or 'draft').replace(' ', '-')}", "docx")


@app.get("/api/drafts/{draft_id}/versions")
def list_versions(draft_id: str, user: dict = Depends(require_user)):
    _row(draft_id, user)
    with engine().connect() as conn:
        rows = conn.execute(select(draft_versions.c.id, draft_versions.c.number, draft_versions.c.label, draft_versions.c.note, draft_versions.c.created_at)
                            .where(draft_versions.c.draft_id == draft_id).order_by(draft_versions.c.number)).mappings().all()
    return [{"id": r["id"], "number": r["number"], "label": r["label"], "note": r["note"], "at": r["created_at"].isoformat()} for r in rows]


@app.post("/api/drafts/{draft_id}/versions")
def keep_version(draft_id: str, body: VersionIn, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    return _keep_version(row, body.label or "Kept", body.note)


@app.get("/api/drafts/{draft_id}/versions/{version_id}.pdf")
def version_pdf(draft_id: str, version_id: str, user: dict = Depends(require_user)):
    draft = _row(draft_id, user)
    require_paid(draft)
    with engine().connect() as conn:
        row = conn.execute(select(draft_versions).where(draft_versions.c.id == version_id, draft_versions.c.draft_id == draft_id)).mappings().first()
    if not row:
        raise HTTPException(404, "That version is not on the file")
    return _file(row["document"], f"version-{row['number']}", "pdf")


@app.get("/api/drafts/{draft_id}/versions/{version_id}.docx")
def version_docx(draft_id: str, version_id: str, user: dict = Depends(require_user)):
    draft = _row(draft_id, user)
    require_paid(draft)
    with engine().connect() as conn:
        row = conn.execute(select(draft_versions).where(draft_versions.c.id == version_id, draft_versions.c.draft_id == draft_id)).mappings().first()
    if not row:
        raise HTTPException(404, "That version is not on the file")
    return _file(row["document"], f"version-{row['number']}", "docx")


@app.get("/api/drafts/{draft_id}/pdf")
def pdf(draft_id: str, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    document = _complete(row)
    require_paid(row)
    filename = f"{row['service']}-{(row['client_name'] or 'draft').replace(' ', '-')}.pdf"
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/drafts/{draft_id}/submit")
def submit(draft_id: str, request: Request, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    _complete(row)
    require_paid(row)
    _keep_version(row, "Sent for solicitor review", "The client sent this version. Earlier versions stay on the file.")
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(status="submitted_for_review", updated_at=now()))
    audit("draft_submitted", user, "draft", draft_id, ip=client_ip(request))
    return _out(_row(draft_id, user))


class PayIn(BaseModel):
    session_id: str = ""


def _save_payment(draft_id: str, record: dict) -> None:
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(payment=record, updated_at=now()))


@app.post("/api/drafts/{draft_id}/checkout")
def checkout(draft_id: str, request: Request, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    _complete(row)
    if describe(row)["status"] == "paid":
        return {"url": "", "paid": True}
    base = os.environ.get("APP_BASE_URL", str(request.base_url).rstrip("/"))
    email = row["client_email"] or user.get("email") or ""
    return {"url": start_checkout(row, base, email), "paid": False}


@app.post("/api/drafts/{draft_id}/payment")
def confirm_payment(draft_id: str, body: PayIn, request: Request, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    session = fetch_session(body.session_id)
    record = paid_record(session, row["service"])
    if record["draft_id"] != draft_id:
        raise HTTPException(400, "That payment is for a different document.")
    _save_payment(draft_id, record)
    audit("draft_paid", user, "draft", draft_id, {"amount": record["amount"]}, client_ip(request))
    return _out(_row(draft_id, user))


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    event = webhook_event(await request.body(), request.headers.get("stripe-signature", ""))
    if event.get("type") == "checkout.session.completed":
        session = (event.get("data") or {}).get("object") or {}
        draft_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("draft_id")
        service = (session.get("metadata") or {}).get("service")
        if draft_id and service:
            record = paid_record(session, service)
            if record["draft_id"] == draft_id:
                _save_payment(draft_id, record)
    return {"ok": True}


@app.get("/paid")
def paid_return(draft: str, session_id: str):
    safe_draft = "".join(ch for ch in draft if ch.isalnum() or ch == "-")
    safe_session = "".join(ch for ch in session_id if ch.isalnum() or ch == "_")
    target = f"/#/d/{safe_draft}/review?session_id={safe_session}"
    return HTMLResponse(f'<!doctype html><meta http-equiv="refresh" content="0;url={target}"><p><a href="{target}">Back to your document</a></p>')


def _editable(draft_id: str, user: dict):
    row = _row(draft_id, user)
    if row["status"] != "draft":
        raise HTTPException(409, "This draft has been sent for review and can no longer be changed")
    return row


@app.post("/api/drafts/{draft_id}/uploads")
async def upload(draft_id: str, request: Request, file: UploadFile = File(...), kind: str = Form(""), user: dict = Depends(require_user)):
    row = _editable(draft_id, user)
    if len(_uploads(draft_id)) >= MAX_UPLOADS_PER_DRAFT:
        raise HTTPException(400, f"You can upload up to {MAX_UPLOADS_PER_DRAFT} documents")
    filename = re.sub(r"[^\w.\- ]", "_", Path(file.filename or "document").name)[:120] or "document"
    if Path(filename).suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(400, "Please upload a PDF, Word (.docx), text file or photo (JPG, PNG, HEIC)")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "That file is over 10 MB")
    if not data:
        raise HTTPException(400, "That file is empty")
    text_, read_as = extract_text(filename, file.content_type or "", data)
    kind = (kind or detect_kind(text_) or "Other")[:60]
    upload_id = new_id()
    sugg = suggest(row["service"], text_, upload_id, filename)
    with engine().begin() as conn:
        conn.execute(insert(uploads).values(id=upload_id, draft_id=draft_id, filename=filename, content_type=file.content_type or "application/octet-stream", kind=kind,
                                            size=len(data), data=data, text=text_, read_as=read_as, suggestions=sugg, created_at=now()))
    audit("upload_added", user, "upload", upload_id, {"draft_id": draft_id, "filename": filename, "size": len(data)}, client_ip(request))
    return [u for u in _uploads(draft_id) if u["id"] == upload_id][0]


@app.post("/api/drafts/{draft_id}/fill")
def fill_draft(draft_id: str, request: Request, user: dict = Depends(require_user)):
    """The point where uploaded papers are written into the draft. Does not send or file anything."""
    row = _editable(draft_id, user)
    suggestions = [item for upload in _uploads(draft_id) for item in (upload.get("suggestions") or [])]
    if not suggestions:
        raise HTTPException(400, "Nothing on the uploaded papers could be read. A photo or a scan has to be typed in.")
    answers, filled, notes = fill_from_papers(row["answers"], suggestions)
    if not filled:
        raise HTTPException(400, "The papers were read, but they did not add anything new. What is already typed has been left as it is.")
    name, email = _client(answers)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(answers=answers, client_name=name or row["client_name"], client_email=email or row["client_email"], updated_at=now()))
    audit("draft_filled", user, "draft", draft_id, {"filled": len(filled)}, client_ip(request))
    out = _out(_row(draft_id, user))
    out["filled_from_papers"] = filled
    out["paper_notes"] = notes
    return out


# ---------------------------------------------------------------------------
# Generic upload endpoint (not tied to a draft). Allows a user to upload a file
# and have it stored securely. Uses the same validation rules as the draft
# upload endpoint.
# ---------------------------------------------------------------------------
@app.post("/upload")
async def generic_upload(file: UploadFile = File(...), user_id: str = Form(...)):
    # Validate file size and type using the same constants as the draft upload.
    filename = re.sub(r"[^\w.\- ]", "_", Path(file.filename or "document").name)[:120] or "document"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Please upload a PDF, Word (.docx), text file or photo (JPG, PNG, HEIC)")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "That file is over 10 MB")
    if not data:
        raise HTTPException(400, "That file is empty")
    saved_path = save_uploaded_file(user_id, filename, data)
    return {"filename": filename, "saved_path": str(saved_path)}


@app.get("/api/drafts/{draft_id}/uploads")
def list_uploads(draft_id: str, user: dict = Depends(require_user)):
    _row(draft_id, user)
    return _uploads(draft_id)


@app.get("/api/drafts/{draft_id}/uploads/{upload_id}")
def download_upload(draft_id: str, upload_id: str, user: dict = Depends(require_user)):
    _row(draft_id, user)
    return upload_response(draft_id, upload_id)


def upload_response(draft_id: str, upload_id: str) -> Response:
    with engine().connect() as conn:
        r = conn.execute(select(uploads).where(uploads.c.id == upload_id, uploads.c.draft_id == draft_id)).mappings().first()
    if not r:
        raise HTTPException(404, "Document not found")
    return Response(r["data"], media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{r["filename"]}"', "X-Content-Type-Options": "nosniff"})


@app.delete("/api/drafts/{draft_id}/uploads/{upload_id}")
def delete_upload(draft_id: str, upload_id: str, request: Request, user: dict = Depends(require_user)):
    _editable(draft_id, user)
    with engine().begin() as conn:
        n = conn.execute(delete(uploads).where(uploads.c.id == upload_id, uploads.c.draft_id == draft_id)).rowcount
    if not n:
        raise HTTPException(404, "Document not found")
    audit("upload_deleted", user, "upload", upload_id, {"draft_id": draft_id}, client_ip(request))
    return {"ok": True}


@app.get("/{path:path}")
def spa(path: str):
    first = path.split("/", 1)[0]
    if first in {"api", "static", "docs", "redoc", "openapi.json", "healthz"}:
        raise HTTPException(404, "Not Found")
    return app_shell()
