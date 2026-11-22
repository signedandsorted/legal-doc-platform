from contextlib import asynccontextmanager
import copy
import hashlib
import re
from pathlib import Path

import re

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, text, update

from .admin import router as admin_router
from .capacity import router as capacity_router
from .auth import require_user, router as auth_router, seed_admin, seed_staff, set_csrf_cookie
from .firm import public_probate_prepare, router as firm_router
from .db import drafts, engine, init_db, new_id, now, uploads
from .security import audit, client_ip, csrf_ok
from .documents import build_document, find_issues, missing_fields
from .documents import save_uploaded_file
from .extract import detect_kind, extract_text, suggest
from .guides import SERVICES
from .pdf import render_pdf

STATIC = Path(__file__).resolve().parent.parent / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOADS_PER_DRAFT = 15
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".heic", ".webp"}


@asynccontextmanager
async def lifespan(_):
    init_db()
    seed_admin()
    seed_staff()
    yield


app = FastAPI(title="Legal Doc Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    if request.method in UNSAFE and request.url.path.startswith("/api/") and not csrf_ok(request):
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
    return [{"id": s["id"], "title": s["title"], "summary": s["summary"], "steps": len(s["steps"]), "category": s.get("category", "")} for s in SERVICES.values()]


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
            "issues": find_issues(row["service"], row["answers"], _uploads_text(row["id"]) if ups else ""), "uploads": ups, "updated_at": row["updated_at"].isoformat()}


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
    name, email = _client(body.answers)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(answers=body.answers, client_name=name, client_email=email, updated_at=now()))
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


@app.get("/api/drafts/{draft_id}/pdf")
def pdf(draft_id: str, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    document = _complete(row)
    filename = f"{row['service']}-{(row['client_name'] or 'draft').replace(' ', '-')}.pdf"
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/drafts/{draft_id}/submit")
def submit(draft_id: str, request: Request, user: dict = Depends(require_user)):
    row = _row(draft_id, user)
    _complete(row)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(status="submitted_for_review", updated_at=now()))
    audit("draft_submitted", user, "draft", draft_id, ip=client_ip(request))
    return _out(_row(draft_id, user))


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
