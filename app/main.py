from contextlib import asynccontextmanager
from pathlib import Path

import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, text, update

from .db import drafts, engine, init_db, new_id, now, uploads
from .documents import build_document, find_issues, missing_fields
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
    yield


app = FastAPI(title="Legal Doc Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


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


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/services")
def services():
    return [{"id": s["id"], "title": s["title"], "summary": s["summary"], "steps": len(s["steps"])} for s in SERVICES.values()]


@app.get("/api/services/{service_id}")
def service(service_id: str):
    if service_id not in SERVICES:
        raise HTTPException(404, "Unknown service")
    return _with_videos(SERVICES[service_id])


def _video(vid: str | None) -> dict | None:
    if not vid or not (STATIC / "videos" / f"{vid}.mp4").exists():
        return None
    out = {"id": vid, "src": f"/static/videos/{vid}.mp4"}
    for ext, key in (("vtt", "captions"), ("jpg", "poster")):
        if (STATIC / "videos" / f"{vid}.{ext}").exists():
            out[key] = f"/static/videos/{vid}.{ext}"
    return out


def _with_videos(s: dict) -> dict:
    return {**s, "review_video": _video(s.get("review_video")), "steps": [{**st, "video": _video(st.get("video"))} for st in s["steps"]]}


def _client(answers: dict) -> tuple[str, str | None]:
    for key in ("about_you", "donor"):
        if answers.get(key):
            return answers[key].get("full_name") or "", answers[key].get("email")
    applicant = (answers.get("will") or {}).get("applicant") or {}
    return applicant.get("full_name") or "", applicant.get("email")


def _row(draft_id: str):
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row:
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


@app.post("/api/drafts")
def create_draft(body: DraftIn):
    if body.service not in SERVICES:
        raise HTTPException(400, "Unknown service")
    name, email = _client(body.answers)
    draft_id = new_id()
    with engine().begin() as conn:
        conn.execute(insert(drafts).values(id=draft_id, service=body.service, client_name=name, client_email=email, answers=body.answers, status="draft", created_at=now(), updated_at=now()))
    return _out(_row(draft_id))


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    return _out(_row(draft_id))


@app.put("/api/drafts/{draft_id}")
def save_draft(draft_id: str, body: AnswersIn):
    row = _row(draft_id)
    if row["status"] != "draft":
        raise HTTPException(409, "This draft has been sent for review and can no longer be changed")
    name, email = _client(body.answers)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(answers=body.answers, client_name=name, client_email=email, updated_at=now()))
    return _out(_row(draft_id))


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
def preview(draft_id: str):
    return _complete(_row(draft_id))


@app.get("/api/drafts/{draft_id}/pdf")
def pdf(draft_id: str):
    row = _row(draft_id)
    document = _complete(row)
    filename = f"{row['service']}-{(row['client_name'] or 'draft').replace(' ', '-')}.pdf"
    return Response(render_pdf(document), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/drafts/{draft_id}/submit")
def submit(draft_id: str):
    row = _row(draft_id)
    _complete(row)
    with engine().begin() as conn:
        conn.execute(update(drafts).where(drafts.c.id == draft_id).values(status="submitted_for_review", updated_at=now()))
    return _out(_row(draft_id))


def _editable(draft_id: str):
    row = _row(draft_id)
    if row["status"] != "draft":
        raise HTTPException(409, "This draft has been sent for review and can no longer be changed")
    return row


@app.post("/api/drafts/{draft_id}/uploads")
async def upload(draft_id: str, file: UploadFile = File(...), kind: str = Form("")):
    row = _editable(draft_id)
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
    return [u for u in _uploads(draft_id) if u["id"] == upload_id][0]


@app.get("/api/drafts/{draft_id}/uploads")
def list_uploads(draft_id: str):
    _row(draft_id)
    return _uploads(draft_id)


@app.get("/api/drafts/{draft_id}/uploads/{upload_id}")
def download_upload(draft_id: str, upload_id: str):
    with engine().connect() as conn:
        r = conn.execute(select(uploads).where(uploads.c.id == upload_id, uploads.c.draft_id == draft_id)).mappings().first()
    if not r:
        raise HTTPException(404, "Document not found")
    return Response(r["data"], media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{r["filename"]}"', "X-Content-Type-Options": "nosniff"})


@app.delete("/api/drafts/{draft_id}/uploads/{upload_id}")
def delete_upload(draft_id: str, upload_id: str):
    _editable(draft_id)
    with engine().begin() as conn:
        n = conn.execute(delete(uploads).where(uploads.c.id == upload_id, uploads.c.draft_id == draft_id)).rowcount
    if not n:
        raise HTTPException(404, "Document not found")
    return {"ok": True}
