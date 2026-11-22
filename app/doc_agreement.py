"""Draft text for prenup, postnup, cohabitation and employment settlement.
DRAFT WORDING: a solicitor must check it before anyone signs. Not legal advice."""
from .common import DRAFT_NOTICE, issue
from .guides import SERVICES

AGREEMENTS = ("prenup", "postnup", "cohabitation", "employment_settlement")


def _value(field: dict, value) -> str:
    if value is None or value is False or value == "":
        return ""
    if field["type"] == "checkbox":
        return "Yes" if value is True else ""
    if field["type"] == "list":
        lines = []
        for i, item in enumerate(value or [], 1):
            bits = []
            for sub in field["fields"]:
                bit = _value(sub, (item or {}).get(sub["name"]))
                if bit:
                    bits.append(f"{sub['label']}: {bit}")
            if bits:
                lines.append(f"{i}. " + "; ".join(bits))
        return "\n".join(lines)
    if field["type"] == "group":
        bits = []
        for sub in field["fields"]:
            bit = _value(sub, (value or {}).get(sub["name"]))
            if bit:
                bits.append(f"{sub['label']}: {bit}")
        return "; ".join(bits)
    return str(value).strip()


def agreement_issues(service_id: str, answers: dict) -> list[dict]:
    notes = {
        "prenup": "A prenuptial agreement is not automatically binding in England and Wales. Both people need independent legal advice and full financial disclosure before anyone signs.",
        "postnup": "A postnuptial agreement is not automatically binding. Both people need independent legal advice and full financial disclosure before anyone signs.",
        "cohabitation": "A cohabitation agreement should be checked by a solicitor. Unmarried couples do not have the same automatic rights as married couples.",
        "employment_settlement": "The employee must receive independent legal advice on a settlement agreement before it can settle claims. Do not sign until that advice is given.",
    }
    return [issue("info", notes.get(service_id, "A solicitor must check this draft before anyone signs."))]


def build_agreement(service_id: str, answers: dict, uploads: list | None = None) -> dict:
    spec = SERVICES[service_id]
    paragraphs, notes = [], []
    paragraphs.append(
        "This is a record of the answers given in Signed and Sorted. It is not the signed agreement. "
        "A solicitor will turn it into the formal document."
    )
    notes.append("The questions collect instructions. They are not the operative clauses.")
    for step in spec["steps"]:
        section = answers.get(step["id"]) or {}
        lines = []
        for field in step["fields"]:
            text = _value(field, section.get(field["name"]))
            if text:
                lines.append(f"{field['label']}: {text}")
        if lines:
            paragraphs.append(step["title"] + ". " + " ".join(lines))
            notes.append(f"{step['title']}: taken from the answers on that step. A solicitor will rewrite this in the proper form.")
    if uploads:
        paragraphs.append("Documents uploaded: " + ", ".join(u.get("filename") or "file" for u in uploads) + ".")
    sources = []
    seen = set()
    for step in spec["steps"]:
        for src in step.get("sources") or []:
            if src.get("url") not in seen:
                seen.add(src["url"])
                sources.append(src)
    return {
        "title": spec["title"],
        "notice": DRAFT_NOTICE,
        "sections": [{"heading": spec["title"], "paragraphs": paragraphs, "notes": notes}],
        "next_steps": spec.get("next_steps") or [
            "A solicitor reviews these answers and prepares the formal agreement.",
            "Each person who needs independent advice speaks to their own solicitor before signing.",
            "Nothing in this draft is signed or filed from this website.",
        ],
        "sources": sources,
    }
