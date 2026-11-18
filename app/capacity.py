"""Optional supporting video statement for a will or lasting power of attorney.

The prompts are original wording based on the legal tests in Banks v Goodfellow
(wills) and the Mental Capacity Act 2005 sections 2 and 3 (LPAs). This is not a
copy of any third-party product. A recording supports, but does not prove, capacity.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import insert, select, update

from .auth import require_user
from .db import capacity_statements, drafts, engine, new_id, now
from .security import audit, client_ip
from .statement_crypto import decrypt, encrypt

router = APIRouter()

# Conservative defaults. These can be changed later without a migration.
MAX_STATEMENT_BYTES = 40 * 1024 * 1024
MAX_STATEMENT_SECONDS = 8 * 60
ALLOWED_EXT = {".webm", ".mp4", ".mov", ".mkv", ".ogv", ".ogg"}
ALLOWED_TYPES = {
    "video/webm",
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/ogg",
    "application/octet-stream",
}
WILL_SERVICES = {"will"}
LPA_SERVICES = {"lpa_property", "lpa_health"}
SUPPORTED = WILL_SERVICES | LPA_SERVICES

DISCLAIMER = (
    "This recording can support, but does not prove, that you had capacity to make this document. "
    "It is not a medical or legal assessment of capacity, and it is not a substitute for advice from "
    "a solicitor or a doctor. Nothing in this recording formally certifies capacity."
)

GOLDEN_RULE = (
    "If you are older, unwell, or you think anyone might later question whether you had capacity, "
    "the usual professional practice sometimes called the golden rule is to ask a doctor or another "
    "suitable professional to assess and record your capacity, rather than relying on a video alone. "
    "This is optional. Tick the box if you would like the solicitor who reviews your draft to talk "
    "with you about arranging a medical capacity assessment."
)

RETENTION = (
    "We keep the recording, its SHA-256 fingerprint and the audit entry for as long as this document "
    "and your account are kept, unless a different retention period is later set. If you ask us to "
    "delete it, we will do so unless we must keep a copy because it forms part of the record of how "
    "the document was prepared."
)

CONSENT = (
    "I agree that Signed and Sorted may record, encrypt and store this short video, together with "
    "the time, my user account, the document it relates to, a digital fingerprint of the file, and "
    "basic technical details (IP address and browser), for the purpose of keeping a supporting "
    "record of the circumstances in which I made this will or lasting power of attorney. "
    "I understand that a video of me speaking about my capacity and personal circumstances can be "
    "special category personal data under the UK GDPR and the Data Protection Act 2018, and I give "
    "my explicit consent to this processing. "
    "Access is limited to me and to authorised administrators (including a solicitor reviewing this "
    "draft). The file is encrypted before it is stored. It is not sent to a third-party video service. "
    "I can ask for a copy or to withdraw my consent later; withdrawing consent does not affect the "
    "lawfulness of storing the recording up to that point, and a copy may still need to be kept if "
    "it forms part of the record of how this document was prepared. " + RETENTION
)

WILL_PROMPTS = [
    {
        "id": "identity",
        "title": "Who you are",
        "text": (
            "Please look at the camera and say your full name and today's date. "
            "Please also say that you are making this recording of your own free will, "
            "and that nobody is telling you what to say."
        ),
    },
    {
        "id": "nature_and_effect",
        "title": "What a will does",
        "text": (
            "In your own words, please explain what a will is and what this will is meant to do "
            "when you die. For example, you might talk about who will deal with your estate and "
            "how you want your property to be given away."
        ),
    },
    {
        "id": "property",
        "title": "What you own",
        "text": (
            "Please give a rough picture of what you own and what this will deals with. You do not "
            "need exact values or a complete list. It is enough to show that you have a general "
            "idea of your property, money and anything else that matters."
        ),
    },
    {
        "id": "claims",
        "title": "Who might expect to be provided for",
        "text": (
            "Please say who would normally be expected to be provided for in your situation — for "
            "example a spouse or civil partner, children, or others you support — and, in your own "
            "words, why you have chosen the people named in this will. If you have left out someone "
            "who might have expected to benefit, please say so and briefly why."
        ),
    },
    {
        "id": "free_choice",
        "title": "Your free choice",
        "text": (
            "Please confirm that the decisions in this will are yours, that you understand you can "
            "change a will while you still have capacity, and that you are not being pressured, "
            "hurried or unduly influenced by anyone."
        ),
    },
]

LPA_PROMPTS = [
    {
        "id": "identity",
        "title": "Who you are",
        "text": (
            "Please look at the camera and say your full name and today's date. "
            "Please also say that you are making this recording of your own free will, "
            "and that nobody is telling you what to say."
        ),
    },
    {
        "id": "nature_and_effect",
        "title": "What this lasting power of attorney does",
        "text": (
            "In your own words, please explain what this lasting power of attorney is and what it "
            "will allow your attorney or attorneys to do. Please say whether it is for property and "
            "financial decisions, or for health and care decisions."
        ),
    },
    {
        "id": "when_used",
        "title": "When it can be used and what that means for you",
        "text": (
            "Please explain, in your own words, when you want this lasting power of attorney to be "
            "used, and what that will mean for your own decision-making."
        ),
    },
    {
        "id": "understand_retain_weigh",
        "title": "Understanding and weighing the decision",
        "text": (
            "The law looks at whether you can understand the information that matters for this "
            "decision, remember it long enough to use it, weigh it up, and communicate your choice. "
            "In your own words, please say what you have taken into account in deciding to make this "
            "lasting power of attorney, and that you are making the decision yourself."
        ),
    },
    {
        "id": "free_choice",
        "title": "Your free choice",
        "text": (
            "Please confirm that you want to appoint the attorney or attorneys named in this "
            "document, that you understand you can cancel a lasting power of attorney while you "
            "still have capacity, and that you are not being pressured, hurried or unduly influenced "
            "by anyone."
        ),
    },
]

PROMPT_SETS = {
    "will-banks-v-goodfellow-2026-11": {
        "services": WILL_SERVICES,
        "legal_basis": "The prompts are based on the test in Banks v Goodfellow (1870) LR 5 QB 549.",
        "prompts": WILL_PROMPTS,
    },
    "lpa-mca-2005-ss2-3-2026-11": {
        "services": LPA_SERVICES,
        "legal_basis": "The prompts are based on the Mental Capacity Act 2005, sections 2 and 3.",
        "prompts": LPA_PROMPTS,
    },
}


def consent_hash() -> str:
    return hashlib.sha256(CONSENT.encode()).hexdigest()


def prompt_set_for(service: str) -> tuple[str, dict]:
    for set_id, spec in PROMPT_SETS.items():
        if service in spec["services"]:
            return set_id, spec
    raise HTTPException(404, "A supporting video statement is only available for a will or a lasting power of attorney")


def document_version_hash(answers) -> str:
    payload = json.dumps(answers or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def content_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def looks_like_video(data: bytes, content_type: str, filename: str) -> bool:
    if len(data) < 12:
        return False
    if data[:4] == b"\x1aE\xdf\xa3":  # EBML / WebM / Matroska
        return True
    if data[4:8] == b"ftyp":
        return True
    if data[:4] == b"OggS":
        return True
    ext = Path(filename).suffix.lower()
    # Some browsers send a bare WebM or MP4 without a clear header until a little later;
    # still require a known type or extension so we do not store arbitrary files.
    return ext in ALLOWED_EXT and (not content_type or content_type.split(";")[0].strip() in ALLOWED_TYPES)


def public_row(row, current_version: str | None = None) -> dict:
    version = row["document_version_hash"]
    out = {
        "id": row["id"],
        "draft_id": row["draft_id"],
        "user_id": row["user_id"],
        "service": row["service"],
        "document_version_hash": version,
        "content_sha256": row["content_sha256"],
        "filename": row["filename"],
        "content_type": row["content_type"],
        "size": row["size"],
        "duration_seconds": row["duration_seconds"],
        "source": row["source"],
        "prompt_set_id": row["prompt_set_id"],
        "consent_text_hash": row["consent_text_hash"],
        "medical_assessment_interest": bool(row["medical_assessment_interest"]),
        "is_current": bool(row["is_current"]),
        "matches_current_document": (current_version is None) or version == current_version,
        "recorded_at": row["recorded_at"].isoformat() if row["recorded_at"] else None,
        "user_agent": row["user_agent"],
        "ip": row["ip"],
    }
    return out


META_COLS = [
    capacity_statements.c.id,
    capacity_statements.c.draft_id,
    capacity_statements.c.user_id,
    capacity_statements.c.service,
    capacity_statements.c.document_version_hash,
    capacity_statements.c.content_sha256,
    capacity_statements.c.filename,
    capacity_statements.c.content_type,
    capacity_statements.c.size,
    capacity_statements.c.duration_seconds,
    capacity_statements.c.source,
    capacity_statements.c.prompt_set_id,
    capacity_statements.c.consent_text_hash,
    capacity_statements.c.medical_assessment_interest,
    capacity_statements.c.is_current,
    capacity_statements.c.recorded_at,
    capacity_statements.c.user_agent,
    capacity_statements.c.ip,
]


def list_for_draft(draft_id: str, current_version: str | None = None) -> list[dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            select(*META_COLS).where(capacity_statements.c.draft_id == draft_id).order_by(capacity_statements.c.recorded_at.desc())
        ).mappings().all()
    return [public_row(r, current_version) for r in rows]


def guide_payload(row) -> dict:
    service = row["service"]
    set_id, spec = prompt_set_for(service)
    version = document_version_hash(row["answers"])
    history = list_for_draft(row["id"], version)
    current = next((s for s in history if s["is_current"]), None)
    return {
        "available": True,
        "title": "Supporting video statement",
        "service": service,
        "disclaimer": DISCLAIMER,
        "consent": CONSENT,
        "consent_text_hash": consent_hash(),
        "retention": RETENTION,
        "golden_rule": GOLDEN_RULE,
        "legal_basis": spec["legal_basis"],
        "prompt_set_id": set_id,
        "prompts": spec["prompts"],
        "max_bytes": MAX_STATEMENT_BYTES,
        "max_seconds": MAX_STATEMENT_SECONDS,
        "allowed_types": sorted(t for t in ALLOWED_TYPES if t != "application/octet-stream"),
        "document_version_hash": version,
        "current": current,
        "history": history,
    }


def _owned_draft(draft_id: str, user: dict):
    with engine().connect() as conn:
        row = conn.execute(select(drafts).where(drafts.c.id == draft_id)).mappings().first()
    if not row or row["user_id"] != user["id"]:
        raise HTTPException(404, "Draft not found")
    return row


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _client_filename(name: str, content_type: str) -> str:
    filename = re.sub(r"[^\w.\- ]", "_", Path(name or "statement").name)[:120] or "statement"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        guessed = { "video/webm": ".webm", "video/mp4": ".mp4", "video/quicktime": ".mov",
                    "video/x-matroska": ".mkv", "video/ogg": ".ogv" }.get((content_type or "").split(";")[0].strip(), ".webm")
        filename = (filename if filename != "statement" else "statement") + guessed
    return filename


@router.get("/api/drafts/{draft_id}/capacity-statement")
def get_guide(draft_id: str, user: dict = Depends(require_user)):
    row = _owned_draft(draft_id, user)
    if row["service"] not in SUPPORTED:
        raise HTTPException(404, "A supporting video statement is only available for a will or a lasting power of attorney")
    return guide_payload(row)


@router.get("/api/drafts/{draft_id}/capacity-statements")
def list_statements(draft_id: str, user: dict = Depends(require_user)):
    row = _owned_draft(draft_id, user)
    return list_for_draft(row["id"], document_version_hash(row["answers"]))


@router.post("/api/drafts/{draft_id}/capacity-statements")
async def confirm_statement(
    draft_id: str,
    request: Request,
    file: UploadFile = File(...),
    consent: str = Form(""),
    confirmed: str = Form(""),
    prompt_set_id: str = Form(""),
    source: str = Form("camera"),
    duration_seconds: str = Form(""),
    medical_assessment_interest: str = Form(""),
    user: dict = Depends(require_user),
):
    row = _owned_draft(draft_id, user)
    if row["service"] not in SUPPORTED:
        raise HTTPException(404, "A supporting video statement is only available for a will or a lasting power of attorney")
    if not _truthy(consent):
        raise HTTPException(400, "Please confirm that you agree to the recording and data-retention wording")
    if not _truthy(confirmed):
        raise HTTPException(400, "Please confirm this is the recording you want to keep")
    expected_set, _ = prompt_set_for(row["service"])
    if (prompt_set_id or expected_set) != expected_set:
        raise HTTPException(400, "The prompts for this document have changed. Please refresh the page and record again.")
    if source not in {"camera", "upload"}:
        raise HTTPException(400, "How the recording was made must be camera or upload")
    duration = None
    if (duration_seconds or "").strip():
        try:
            duration = int(duration_seconds)
        except ValueError:
            raise HTTPException(400, "Duration must be a whole number of seconds")
        if duration < 1 or duration > MAX_STATEMENT_SECONDS + 15:
            raise HTTPException(400, f"Please keep the recording to {MAX_STATEMENT_SECONDS // 60} minutes or less")
    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
    filename = _client_filename(file.filename or "statement", content_type)
    if Path(filename).suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(400, "Please record or upload a short video (WebM, MP4, MOV or Ogg)")
    data = await file.read(MAX_STATEMENT_BYTES + 1)
    if not data:
        raise HTTPException(400, "That recording is empty")
    if len(data) > MAX_STATEMENT_BYTES:
        raise HTTPException(400, "That recording is over 40 MB. Please try a shorter video.")
    if not looks_like_video(data, content_type, filename):
        raise HTTPException(400, "That file does not look like a video we can store")
    if content_type not in ALLOWED_TYPES:
        content_type = "video/webm" if filename.endswith(".webm") else "video/mp4"
    digest = content_sha256(data)
    version = document_version_hash(row["answers"])
    statement_id = new_id()
    recorded = now()
    ip = client_ip(request)
    user_agent = (request.headers.get("user-agent") or "")[:500]
    blob = encrypt(data)
    with engine().begin() as conn:
        conn.execute(
            update(capacity_statements)
            .where(capacity_statements.c.draft_id == draft_id, capacity_statements.c.is_current.is_(True))
            .values(is_current=False)
        )
        conn.execute(insert(capacity_statements).values(
            id=statement_id,
            draft_id=draft_id,
            user_id=user["id"],
            service=row["service"],
            document_version_hash=version,
            content_sha256=digest,
            filename=filename,
            content_type=content_type,
            size=len(data),
            duration_seconds=duration,
            source=source,
            prompt_set_id=expected_set,
            consent_text_hash=consent_hash(),
            medical_assessment_interest=_truthy(medical_assessment_interest),
            is_current=True,
            encrypted_data=blob,
            recorded_at=recorded,
            user_agent=user_agent,
            ip=ip,
        ))
    audit(
        "capacity_statement_added",
        user,
        "capacity_statement",
        statement_id,
        {
            "draft_id": draft_id,
            "document_version_hash": version,
            "content_sha256": digest,
            "size": len(data),
            "source": source,
            "prompt_set_id": expected_set,
            "user_agent": user_agent,
        },
        ip,
    )
    return guide_payload(_owned_draft(draft_id, user))


def _load_owned(draft_id: str, statement_id: str, user: dict):
    _owned_draft(draft_id, user)
    with engine().connect() as conn:
        row = conn.execute(
            select(capacity_statements).where(
                capacity_statements.c.id == statement_id,
                capacity_statements.c.draft_id == draft_id,
            )
        ).mappings().first()
    if not row:
        raise HTTPException(404, "Statement not found")
    return row


def video_response(row, actor: dict, request: Request, action: str) -> Response:
    try:
        plain = decrypt(row["encrypted_data"])
    except ValueError as exc:
        raise HTTPException(500, "This recording could not be read") from exc
    if content_sha256(plain) != row["content_sha256"]:
        audit("capacity_statement_hash_mismatch", actor, "capacity_statement", row["id"], {"draft_id": row["draft_id"]}, client_ip(request))
        raise HTTPException(500, "This recording does not match its saved fingerprint")
    audit(action, actor, "capacity_statement", row["id"], {"draft_id": row["draft_id"]}, client_ip(request))
    filename = row["filename"] or "statement.webm"
    return Response(
        plain,
        media_type=row["content_type"] or "video/webm",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "X-Content-SHA256": row["content_sha256"],
        },
    )


@router.get("/api/drafts/{draft_id}/capacity-statements/{statement_id}")
def get_statement(draft_id: str, statement_id: str, user: dict = Depends(require_user)):
    row = _owned_draft(draft_id, user)
    with engine().connect() as conn:
        stmt = conn.execute(
            select(*META_COLS).where(
                capacity_statements.c.id == statement_id,
                capacity_statements.c.draft_id == draft_id,
            )
        ).mappings().first()
    if not stmt:
        raise HTTPException(404, "Statement not found")
    return public_row(stmt, document_version_hash(row["answers"]))


@router.get("/api/drafts/{draft_id}/capacity-statements/{statement_id}/video")
def play_statement(draft_id: str, statement_id: str, request: Request, user: dict = Depends(require_user)):
    return video_response(_load_owned(draft_id, statement_id, user), user, request, "capacity_statement_played")
