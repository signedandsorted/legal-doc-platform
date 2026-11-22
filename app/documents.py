from .common import missing_in
from .doc_lpa import build_lpa, lpa_issues
from .doc_poa import build_poa, poa_issues
from .doc_probate import build_probate, probate_issues
from .doc_will import build_will, will_issues
from .doc_agreement import AGREEMENTS, agreement_issues, build_agreement
from .guides import SERVICES

BUILDERS = {"will": build_will, "lpa_property": build_lpa, "lpa_health": build_lpa, "poa_ordinary": build_poa, "probate": build_probate,
            **{sid: build_agreement for sid in AGREEMENTS}}


def missing_fields(service_id: str, answers: dict) -> list[str]:
    missing = []
    for step in SERVICES[service_id]["steps"]:
        section = answers.get(step["id"]) or {}
        for field in step["fields"]:
            missing += missing_in(field, section.get(field["name"]), step["title"], section)
    return missing


def find_issues(service_id: str, answers: dict, uploads_text: str = "") -> list[dict]:
    if service_id.startswith("lpa_"):
        return lpa_issues(service_id, answers, uploads_text)
    if service_id == "poa_ordinary":
        return poa_issues(answers)
    if service_id == "probate":
        return probate_issues(answers)
    if service_id in AGREEMENTS:
        return agreement_issues(service_id, answers)
    return will_issues(answers)


def _dedupe(sources: list) -> list:
    seen, out = set(), []
    for x in sources:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out


def build_document(service_id: str, answers: dict, uploads: list | None = None) -> dict:
    doc = BUILDERS[service_id](service_id, answers, uploads)
    doc["sources"] = _dedupe(doc.get("sources", []))
    doc["issues"] = find_issues(service_id, answers, " ".join(u.get("text", "") for u in uploads or []))
    return doc

# ---------------------------------------------------------------------------
# Helper for generic document uploads (outside of a draft context).
# Stores uploaded files in a per‑user directory under the app's uploads folder.
# Returns the absolute path of the saved file.
# ---------------------------------------------------------------------------
import os
import uuid
from pathlib import Path

def save_uploaded_file(user_id: str, filename: str, data: bytes) -> Path:
    """Save an uploaded file for a given user.

    The file is written to ``uploads/<user_id>/`` inside the project directory.
    A unique filename is generated to avoid collisions while preserving the
    original extension.
    """
    # Ensure a safe filename and keep the original extension
    ext = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    base_dir = Path(__file__).resolve().parent.parent / "uploads" / user_id
    base_dir.mkdir(parents=True, exist_ok=True)
    dest = base_dir / safe_name
    # Write the file atomically
    dest.write_bytes(data)
    # Restrict permissions to the owner only (read/write)
    os.chmod(dest, 0o600)
    return dest
