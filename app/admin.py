"""Admin area: clients, drafts, uploads (view/download/delete), roles, and the audit log.
Every admin read of client data and every change is written to the audit log."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update

from .auth import require_admin
from .capacity import META_COLS, document_version_hash, public_row, video_response
from .db import audit_log, capacity_statements, drafts, engine, password_resets, sessions, uploads, users
from .documents import find_issues, missing_fields
from .guides import SERVICES
from .security import audit, client_ip

router = APIRouter(prefix="/api/admin")


class RoleIn(BaseModel):
    role: str


def _iso(v):
    return v.isoformat() if v else None


@router.get("/summary")
def summary(admin: dict = Depends(require_admin)):
    with engine().connect() as conn:
        count = lambda t, *w: conn.execute(select(func.count()).select_from(t).where(*w)).scalar_one()
        return {"clients": count(users, users.c.role == "client"), "admins": count(users, users.c.role == "admin"), "drafts": count(drafts),
                "submitted": count(drafts, drafts.c.status == "submitted_for_review"), "uploads": count(uploads),
                "capacity_statements": count(capacity_statements), "unowned_drafts": count(drafts, drafts.c.user_id.is_(None))}


@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    with engine().connect() as conn:
        n = select(drafts.c.user_id, func.count().label("n")).group_by(drafts.c.user_id).subquery()
        rows = conn.execute(select(users.c.id, users.c.email, users.c.role, users.c.created_at, users.c.last_login_at, func.coalesce(n.c.n, 0).label("drafts"))
                            .outerjoin(n, n.c.user_id == users.c.id).order_by(users.c.created_at.desc())).mappings().all()
    return [{**dict(r), "created_at": _iso(r["created_at"]), "last_login_at": _iso(r["last_login_at"])} for r in rows]


@router.patch("/users/{user_id}")
def set_role(user_id: str, body: RoleIn, request: Request, admin: dict = Depends(require_admin)):
    if body.role not in ("client", "admin"):
        raise HTTPException(400, "Role must be client or admin")
    if user_id == admin["id"] and body.role != "admin":
        raise HTTPException(400, "You can't remove your own admin access")
    with engine().begin() as conn:
        if not conn.execute(update(users).where(users.c.id == user_id).values(role=body.role)).rowcount:
            raise HTTPException(404, "User not found")
    audit("admin_set_role", admin, "user", user_id, {"role": body.role}, client_ip(request))
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(400, "You can't delete your own account here")
    with engine().begin() as conn:
        u = conn.execute(select(users.c.email).where(users.c.id == user_id)).first()
        if not u:
            raise HTTPException(404, "User not found")
        ids = [r[0] for r in conn.execute(select(drafts.c.id).where(drafts.c.user_id == user_id))]
        if ids:
            conn.execute(delete(capacity_statements).where(capacity_statements.c.draft_id.in_(ids)))
            conn.execute(delete(uploads).where(uploads.c.draft_id.in_(ids)))
            conn.execute(delete(drafts).where(drafts.c.id.in_(ids)))
        conn.execute(delete(capacity_statements).where(capacity_statements.c.user_id == user_id))
        conn.execute(delete(sessions).where(sessions.c.user_id == user_id))
        conn.execute(delete(password_resets).where(password_resets.c.user_id == user_id))
        conn.execute(delete(users).where(users.c.id == user_id))
    audit("admin_delete_user", admin, "user", user_id, {"email": u[0], "drafts_deleted": len(ids)}, client_ip(request))
    return {"ok": True, "drafts_deleted": len(ids)}


@router.get("/drafts")
def list_drafts(admin: dict = Depends(require_admin), user_id: str | None = None):
    with engine().connect() as conn:
        n = select(uploads.c.draft_id, func.count().label("n")).group_by(uploads.c.draft_id).subquery()
        q = (select(drafts.c.id, drafts.c.service, drafts.c.client_name, drafts.c.status, drafts.c.created_at, drafts.c.updated_at, drafts.c.user_id,
                    users.c.email.label("owner_email"), func.coalesce(n.c.n, 0).label("uploads"))
             .outerjoin(users, users.c.id == drafts.c.user_id).outerjoin(n, n.c.draft_id == drafts.c.id).order_by(drafts.c.updated_at.desc()))
        if user_id:
            q = q.where(drafts.c.user_id == user_id)
        rows = conn.execute(q).mappings().all()
    return [{**dict(r), "title": SERVICES.get(r["service"], {}).get("title", r["service"]), "created_at": _iso(r["created_at"]), "updated_at": _iso(r["updated_at"])} for r in rows]


def _upload_rows(where):
    with engine().connect() as conn:
        rows = conn.execute(select(uploads.c.id, uploads.c.draft_id, uploads.c.filename, uploads.c.kind, uploads.c.size, uploads.c.read_as, uploads.c.created_at,
                                   users.c.email.label("owner_email"))
                            .join(drafts, drafts.c.id == uploads.c.draft_id).outerjoin(users, users.c.id == drafts.c.user_id).where(*where)
                            .order_by(uploads.c.created_at.desc())).mappings().all()
    return [{**dict(r), "created_at": _iso(r["created_at"])} for r in rows]


@router.get("/drafts/{draft_id}")
def view_draft(draft_id: str, request: Request, admin: dict = Depends(require_admin)):
    with engine().connect() as conn:
        row = conn.execute(select(drafts, users.c.email.label("owner_email")).outerjoin(users, users.c.id == drafts.c.user_id).where(drafts.c.id == draft_id)).mappings().first()
    if not row:
        raise HTTPException(404, "Draft not found")
    audit("admin_view_draft", admin, "draft", draft_id, ip=client_ip(request))
    with engine().connect() as conn:
        text_ = " ".join(r[0] or "" for r in conn.execute(select(uploads.c.text).where(uploads.c.draft_id == draft_id)))
    version = document_version_hash(row["answers"])
    with engine().connect() as conn:
        stmts = conn.execute(select(*META_COLS).where(capacity_statements.c.draft_id == draft_id).order_by(capacity_statements.c.recorded_at.desc())).mappings().all()
    return {"id": row["id"], "service": row["service"], "title": SERVICES.get(row["service"], {}).get("title", row["service"]), "status": row["status"],
            "owner_email": row["owner_email"], "client_name": row["client_name"], "answers": row["answers"], "missing": missing_fields(row["service"], row["answers"]),
            "issues": find_issues(row["service"], row["answers"], text_), "uploads": _upload_rows([uploads.c.draft_id == draft_id]),
            "capacity_statements": [public_row(s, version) for s in stmts],
            "created_at": _iso(row["created_at"]), "updated_at": _iso(row["updated_at"])}


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str, request: Request, admin: dict = Depends(require_admin)):
    with engine().begin() as conn:
        conn.execute(delete(capacity_statements).where(capacity_statements.c.draft_id == draft_id))
        conn.execute(delete(uploads).where(uploads.c.draft_id == draft_id))
        if not conn.execute(delete(drafts).where(drafts.c.id == draft_id)).rowcount:
            raise HTTPException(404, "Draft not found")
    audit("admin_delete_draft", admin, "draft", draft_id, ip=client_ip(request))
    return {"ok": True}


@router.get("/uploads")
def list_uploads(admin: dict = Depends(require_admin)):
    return _upload_rows([])


@router.get("/uploads/{upload_id}/download")
def download(upload_id: str, request: Request, admin: dict = Depends(require_admin)):
    with engine().connect() as conn:
        r = conn.execute(select(uploads).where(uploads.c.id == upload_id)).mappings().first()
    if not r:
        raise HTTPException(404, "Document not found")
    audit("admin_download_upload", admin, "upload", upload_id, {"draft_id": r["draft_id"], "filename": r["filename"]}, client_ip(request))
    return Response(r["data"], media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{r["filename"]}"'})


@router.delete("/uploads/{upload_id}")
def delete_upload(upload_id: str, request: Request, admin: dict = Depends(require_admin)):
    with engine().begin() as conn:
        if not conn.execute(delete(uploads).where(uploads.c.id == upload_id)).rowcount:
            raise HTTPException(404, "Document not found")
    audit("admin_delete_upload", admin, "upload", upload_id, ip=client_ip(request))
    return {"ok": True}


@router.get("/audit")
def audit_entries(admin: dict = Depends(require_admin), limit: int = 200, action: str | None = None):
    limit = max(1, min(limit, 1000))
    with engine().connect() as conn:
        q = select(audit_log).order_by(audit_log.c.id.desc()).limit(limit)
        if action:
            q = q.where(audit_log.c.action == action)
        rows = conn.execute(q).mappings().all()
    return [{**dict(r), "at": _iso(r["at"])} for r in rows]


def _statement(statement_id: str):
    with engine().connect() as conn:
        row = conn.execute(select(capacity_statements).where(capacity_statements.c.id == statement_id)).mappings().first()
    if not row:
        raise HTTPException(404, "Statement not found")
    return row


@router.get("/capacity-statements")
def list_capacity_statements(admin: dict = Depends(require_admin)):
    with engine().connect() as conn:
        rows = conn.execute(
            select(*META_COLS, users.c.email.label("owner_email"), drafts.c.client_name, drafts.c.status)
            .join(drafts, drafts.c.id == capacity_statements.c.draft_id)
            .outerjoin(users, users.c.id == capacity_statements.c.user_id)
            .order_by(capacity_statements.c.recorded_at.desc())
        ).mappings().all()
    out = []
    for r in rows:
        item = public_row(r)
        item["owner_email"] = r["owner_email"]
        item["client_name"] = r["client_name"]
        item["draft_status"] = r["status"]
        out.append(item)
    return out


@router.get("/capacity-statements/{statement_id}")
def view_capacity_statement(statement_id: str, request: Request, admin: dict = Depends(require_admin)):
    row = _statement(statement_id)
    audit("admin_view_capacity_statement", admin, "capacity_statement", statement_id, {"draft_id": row["draft_id"]}, client_ip(request))
    with engine().connect() as conn:
        owner = conn.execute(
            select(users.c.email, drafts.c.client_name, drafts.c.answers)
            .select_from(capacity_statements)
            .join(drafts, drafts.c.id == capacity_statements.c.draft_id)
            .outerjoin(users, users.c.id == capacity_statements.c.user_id)
            .where(capacity_statements.c.id == statement_id)
        ).mappings().first()
    item = public_row(row, document_version_hash(owner["answers"]) if owner else None)
    item["owner_email"] = owner["email"] if owner else None
    item["client_name"] = owner["client_name"] if owner else None
    return item


@router.get("/capacity-statements/{statement_id}/video")
def play_capacity_statement(statement_id: str, request: Request, admin: dict = Depends(require_admin)):
    return video_response(_statement(statement_id), admin, request, "admin_play_capacity_statement")
