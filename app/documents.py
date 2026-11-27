from .common import missing_in
from .doc_lpa import build_lpa, lpa_issues
from .doc_poa import build_poa, poa_issues
from .doc_probate import build_probate, probate_issues
from .doc_will import build_will, will_issues
from .doc_agreement import AGREEMENTS, agreement_issues, build_agreement
from .doc_trust import build_trust, trust_issues
from .doc_us import build_us, us_issues
from .guides import SERVICES

BUILDERS = {"will": build_will, "lpa_property": build_lpa, "lpa_health": build_lpa, "poa_ordinary": build_poa, "probate": build_probate,
            **{sid: build_agreement for sid in AGREEMENTS},
            **{sid: build_us for sid in ("us_will", "us_trust", "us_poa", "us_health", "us_probate")},
            "trust_register": build_trust}


def missing_fields(service_id: str, answers: dict) -> list[str]:
    missing = []
    for step in SERVICES[service_id]["steps"]:
        section = answers.get(step["id"]) or {}
        for field in step["fields"]:
            missing += missing_in(field, section.get(field["name"]), step["title"], section)
    return missing


def find_issues(service_id: str, answers: dict, uploads_text: str = "") -> list[dict]:
    if service_id.startswith("us_"):
        return us_issues(service_id, answers, uploads_text)
    if service_id.startswith("lpa_"):
        return lpa_issues(service_id, answers, uploads_text)
    if service_id == "poa_ordinary":
        return poa_issues(answers)
    if service_id == "probate":
        return probate_issues(answers)
    if service_id in AGREEMENTS:
        return agreement_issues(service_id, answers)
    if service_id == "trust_register":
        return trust_issues(answers, uploads_text)
    return will_issues(answers, uploads_text)


def _dedupe(sources: list) -> list:
    seen, out = set(), []
    for x in sources:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out


def _show(value) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        bits = []
        for item in value[:8]:
            if isinstance(item, dict):
                bits.append(str(item.get("full_name") or item.get("beneficiary") or item.get("name") or item.get("gift") or "an entry"))
            else:
                bits.append(str(item))
        return ", ".join(bits)[:400]
    if isinstance(value, dict):
        return str(value.get("full_name") or "")[:200]
    return str(value)[:300]


def asked_paragraphs(service_id: str, answers: dict) -> list[str]:
    lines = []
    for step in SERVICES[service_id]["steps"]:
        section = answers.get(step["id"]) if isinstance(answers.get(step["id"]), dict) else {}
        if not section:
            lines.append(step["title"] + ": not started")
            continue
        bits = []
        for field in step.get("fields") or []:
            value = section.get(field["name"])
            if value in (None, "", [], {}):
                continue
            bits.append(field["label"].rstrip(" ?") + ": " + _show(value))
        lines.append(step["title"] + (": " + "; ".join(bits[:6]) if bits else ": opened"))
    return lines


def _limits(service_id: str) -> list[str]:
    if str(service_id).startswith("us_"):
        return [
            "It does not make the document valid. It still has to be signed the way that state requires. Louisiana does not use a common-law will.",
            "It does not transfer a house or a bank account into a trust, and it does not file a probate petition.",
            "It does not calculate federal estate tax. That tax applies only above the exemption for the year of death.",
            "Retirement accounts and life insurance pass by their own beneficiary forms unless those forms are changed.",
            "A lawyer licensed in that state is optional. This is not legal advice.",
        ]
    lines = [
        "It does not stop a court claim. Where the Inheritance (Provision for Family and Dependants) Act 1975 can apply, a person who is left out, or left less than they expected, may still ask the court for reasonable financial provision. A claim is normally brought within six months of the grant.",
        "It does not make the document valid. The right people still have to sign the paper copy, in the right order, with the right witnesses.",
        "A tick on a screen is not a doctor's note, an attendance note, or independent legal advice. The golden rule is a file practice, not a guarantee that the will is valid.",
        "It does not remove a solicitor's duties under the SRA Code of Conduct or the SRA wills guidance, where a solicitor is acting. It does not make the firm immune from a claim.",
    ]
    if service_id == "will":
        lines.append("A mirror will can still be changed by each person. A mutual will may bind the survivor after the first death, by a constructive trust. The answers say which was chosen. Choosing one on this form does not create that promise by itself.")
    if service_id.startswith("lpa_"):
        lines.append("An LPA is not registered, and the Office of the Public Guardian will not register it, unless it is signed in the LP12 order: donor, then certificate provider, then attorneys, then the applicant at section 15.")
    if service_id == "poa_ordinary":
        lines.append("An ordinary power of attorney ends if the donor loses capacity. It is not a lasting power of attorney.")
    if service_id == "probate":
        lines.append("Nothing here is filed with HMCTS or HMRC. The firm still sends the application. Unused pension funds count for Inheritance Tax only for deaths on or after 6 April 2027, and only once the scheme has given the figures.")
    if service_id == "trust_register":
        lines.append("It does not register the trust with HMRC. The lead trustee does that on the Trust Registration Service. Until HMRC gives a reference, it is not registered.")
    if service_id in AGREEMENTS:
        lines.append("A nuptial or cohabitation agreement is not automatically binding. An employment settlement that waives claims needs the employee's own independent advice.")
    return lines


def client_summary(service_id: str, answers: dict, document: dict, issues: list[dict]) -> dict:
    """What the client was asked, what is still a risk, and what this draft does not decide."""
    risks = [item["message"] for item in issues if item.get("level") in ("warning", "error")]
    return {
        "title": "Summary — " + (document.get("title") or SERVICES[service_id]["title"]),
        "notice": "This tells the client what was asked and which risks are still open. It is not the signed document and it is not legal advice."
        if not str(service_id).startswith("us_") else
        "This is a United States draft for the state named in the answers. It is not legal advice, and it is not valid until it is signed as that state requires.",
        "sections": [
            {"heading": "What was asked", "paragraphs": asked_paragraphs(service_id, answers)},
            {"heading": "Risks and possible claims", "paragraphs": risks or ["No warning is outstanding on the answers currently saved. That is not a promise that no claim can be made."]},
            {"heading": "What this does not do", "paragraphs": _limits(service_id)},
        ],
        "next_steps": document.get("next_steps") or [],
        "sources": [],
    }


def summary_text(summary: dict) -> str:
    parts = [summary.get("title") or "Summary", "", summary.get("notice") or "", ""]
    for section in summary.get("sections") or []:
        parts.append(section.get("heading") or "")
        parts.extend("- " + paragraph for paragraph in section.get("paragraphs") or [])
        parts.append("")
    if summary.get("next_steps"):
        parts.append("What happens next")
        parts.extend(f"{i}. {step}" for i, step in enumerate(summary["next_steps"], 1))
        parts.append("")
    parts.append("Sending this summary does not mean the document has been signed, and it does not stop a claim.")
    return "\n".join(parts)


def build_document(service_id: str, answers: dict, uploads: list | None = None) -> dict:
    doc = BUILDERS[service_id](service_id, answers, uploads)
    doc["sources"] = _dedupe(doc.get("sources", []))
    doc["issues"] = find_issues(service_id, answers, " ".join(u.get("text", "") for u in uploads or []))
    sections = list(doc.get("sections") or [])
    if not any(section.get("notes") or "Commentary" in (section.get("heading") or "") for section in sections):
        notes = [
            f"{section.get('heading')}: this part records what was entered under that heading. It is draft wording until a solicitor has checked it."
            for section in sections if section.get("heading")
        ]
        sections.append({"heading": "Commentary: what each part is for (not part of the signed document)", "paragraphs": notes or ["A solicitor checks this draft before anyone signs."]})
    if not any((section.get("heading") or "").startswith("What you asked") for section in sections):
        sections.append({
            "heading": "What you asked for (summary only, not part of the signed document)",
            "paragraphs": asked_paragraphs(service_id, answers),
        })
    doc["sections"] = sections
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
