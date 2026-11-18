from .common import missing_in
from .doc_lpa import build_lpa, lpa_issues
from .doc_poa import build_poa, poa_issues
from .doc_probate import build_probate, probate_issues
from .doc_will import build_will, will_issues
from .guides import SERVICES

BUILDERS = {"will": build_will, "lpa_property": build_lpa, "lpa_health": build_lpa, "poa_ordinary": build_poa, "probate": build_probate}


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
