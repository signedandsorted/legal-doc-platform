"""Estatesearch order pack (JSON + PDF) and per-estate tracker. Builds on the catalog in
estatesearch_catalog.py. No live calls, no emails to Estatesearch, no credentials; while
ESTATESEARCH_ENABLED is false the Titlefront route only shows "waiting for Titlefront account".

Required evidence (https://www.estatesearch.co.uk/faq/, recorded 2026-11-23): for estate cases a
death certificate (or interim coroner certificate) AND proof of authority (grant, will, or a
signed engagement letter). Pack generation is blocked until both are uploaded.
"""
from __future__ import annotations

from . import estatesearch_catalog as cat

FAQ_URL = "https://www.estatesearch.co.uk/faq/"
TRACKER = ["Not started", "Pack prepared", "Sent", "Report received"]
DEATH_KINDS = ("death certificate", "coroner")
AUTHORITY_KINDS = ("grant", "letters of administration", "engagement letter")


class PackBlocked(Exception):
    def __init__(self, missing: list[str]) -> None:
        super().__init__("Upload these before the order pack can be made: " + "; ".join(missing))
        self.missing = missing


def _kinds(uploads: list[dict]) -> list[str]:
    return [(u.get("kind") or "").strip().lower() for u in uploads or []]


def evidence_missing(uploads: list[dict]) -> list[str]:
    kinds = _kinds(uploads)
    missing = []
    if not any(any(k in x for k in DEATH_KINDS) for x in kinds):
        missing.append("the death certificate (or interim coroner's certificate)")
    if not any(x == "will" or any(k in x for k in AUTHORITY_KINDS) for x in kinds):
        missing.append("proof of authority: the grant, the will, or a signed engagement letter")
    return missing


def selected_packages(answers: dict) -> list[str]:
    es = answers.get("estatesearch") or {}
    return [p["id"] for p in cat.PACKAGES if es.get("pkg_" + p["id"]) is True]


def build_pack(answers: dict, uploads: list[dict]) -> dict:
    missing = evidence_missing(uploads)
    if missing:
        raise PackBlocked(missing)
    dec = answers.get("deceased") or {}
    es = answers.get("estatesearch") or {}
    q = cat.quote(selected_packages(answers))
    route = "titlefront" if cat.enabled() else "yourself"
    return {
        "subject": {
            "full_name": dec.get("full_name") or "", "other_names": dec.get("other_names") or "",
            "date_of_birth": dec.get("date_of_birth") or "", "date_of_death": dec.get("date_of_death") or "",
            "last_address": dec.get("address") or "",
            "addresses_last_6_years": [x.strip() for x in (es.get("previous_addresses") or "").splitlines() if x.strip()],
        },
        "packages": q["lines"], "subtotal": q["subtotal"], "vat": q["vat"], "total": q["total"],
        "evidence": [{"filename": u.get("filename") or "", "kind": u.get("kind") or ""} for u in uploads or []],
        "routes": [
            {"id": "titlefront", "label": "Titlefront orders this search for you", "status": "ready" if cat.enabled() else "waiting for Titlefront account"},
            {"id": "yourself", "label": "You can order this yourself", "url": cat.ORDER_YOURSELF_URL},
        ],
        "route": route,
        "tracker": es.get("tracker") if es.get("tracker") in TRACKER else "Not started",
        "evidence_rules": FAQ_URL,
        "note": "This pack is for you to send. Nothing is ordered, paid for or sent to Estatesearch from this website.",
    }


def pack_document(pack: dict) -> dict:
    """Shape for app.pdf.render_pdf."""
    s = pack["subject"]
    return {
        "title": "Estatesearch order pack: " + (s["full_name"] or "the person who died"),
        "notice": pack["note"],
        "sections": [
            {"heading": "The person who died", "paragraphs": [
                f"Full name: {s['full_name']}", f"Other or previous names: {s['other_names'] or 'none given'}",
                f"Date of birth: {s['date_of_birth'] or 'not given'}", f"Date of death: {s['date_of_death']}",
                f"Last address: {s['last_address']}"] + [f"Earlier address: {a}" for a in s["addresses_last_6_years"]]},
            {"heading": "Packages chosen", "paragraphs": [f"{l['name']}: {l['price_prefix']}£{l['ex_vat']} + VAT" for l in pack["packages"]] or ["None chosen yet"]},
            {"heading": "Total", "paragraphs": [f"£{pack['subtotal']} + VAT £{pack['vat']} = £{pack['total']}"]},
            {"heading": "Evidence uploaded", "paragraphs": [f"{e['filename']} ({e['kind']})" for e in pack["evidence"]]},
            {"heading": "How it is ordered", "paragraphs": [f"{r['label']}: {r.get('status') or r.get('url')}" for r in pack["routes"]]},
        ],
        "next_steps": ["Check every detail.", "Order on Estatesearch's website, or wait until Titlefront's account is switched on.", "When the report arrives, upload it on the documents step as 'Estatesearch report' and set the tracker to Report received."],
        "sources": [{"title": "Estatesearch FAQ (evidence needed)", "url": FAQ_URL}],
    }
