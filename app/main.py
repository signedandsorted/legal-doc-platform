from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import insert, select, text, update

from .db import drafts, engine, init_db, new_id, now
from .documents import build_document, missing_fields
from .guides import SERVICES
from .pdf import render_pdf

STATIC = Path(__file__).resolve().parent.parent / "static"


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
    return SERVICES[service_id]


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


def _out(row) -> dict:
    return {"id": row["id"], "service": row["service"], "answers": row["answers"], "status": row["status"], "missing": missing_fields(row["service"], row["answers"]), "updated_at": row["updated_at"].isoformat()}


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
    return build_document(row["service"], row["answers"])


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
