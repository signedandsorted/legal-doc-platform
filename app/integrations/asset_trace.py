"""Find and notify: free official tracing and notification services, a details sheet the
executor copies from, and a per-service tracker. The app never submits on their behalf.

Links (checked 2026-11-24 unless stated):
- My Lost Account (banks, building societies, NS&I; free; can take up to 3 months): https://www.mylostaccount.org.uk/start-search
  (site blocks automated checks; link as given in the 23 Nov 2026 brief)
- Gretel (free; the executor uploads the grant to see matches): https://www.gretel.co.uk/faqs/
- Death Notification Service (free; banks reply within 10 working days if an account exists): https://www.deathnotificationservice.co.uk/
- Tell Us Once (use the registrar's reference within 28 days): https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once
- Pension Tracing Service: https://www.gov.uk/find-pension-contact-details
- Statutory credit report request for the deceased (Experian; similar for Equifax and TransUnion): https://www.experian.co.uk/consumer/data-access/thirdparty.html
- Probate records search: https://www.gov.uk/search-will-probate (standing search £4; each copy ordered online £16)
The Experian Unclaimed Assets Register closed in August 2022, so it is deliberately not linked.
"""
from __future__ import annotations

STATUSES = ["Not started", "Submitted", "Reply received"]
SERVICES = [
    {"id": "mylostaccount", "name": "My Lost Account", "url": "https://www.mylostaccount.org.uk/start-search", "cost": "Free",
     "what": "Searches banks, building societies and NS&I for accounts nobody knew about. Replies can take up to 3 months."},
    {"id": "gretel", "name": "Gretel", "url": "https://www.gretel.co.uk/faqs/", "cost": "Free",
     "what": "Looks for lost accounts, pensions and investments. Upload the grant to see matches."},
    {"id": "dns", "name": "Death Notification Service", "url": "https://www.deathnotificationservice.co.uk/", "cost": "Free",
     "what": "Tells many banks and building societies at once. A bank replies within 10 working days if it holds an account."},
    {"id": "tell_us_once", "name": "Tell Us Once", "url": "https://www.gov.uk/after-a-death/organisations-you-need-to-contact-and-tell-us-once", "cost": "Free",
     "what": "Tells government departments (tax, benefits, passport, driving licence). Use the registrar's reference within 28 days."},
    {"id": "pension_tracing", "name": "Pension Tracing Service", "url": "https://www.gov.uk/find-pension-contact-details", "cost": "Free",
     "what": "Finds contact details for workplace and personal pension schemes."},
    {"id": "credit_report", "name": "Credit report for the deceased (Experian, Equifax, TransUnion)", "url": "https://www.experian.co.uk/consumer/data-access/thirdparty.html", "cost": "Free statutory request",
     "what": "Shows accounts and debts in their name. Send the grant, your ID and two proofs of address."},
    {"id": "probate_search", "name": "Probate records search", "url": "https://www.gov.uk/search-will-probate", "cost": "£4 standing search; £16 per copy",
     "what": "Check whether a grant or will is already on record, or set a 6-month standing search."},
]
NOTE = "These services are run by others. You sign up and submit to them yourself; nothing is sent from this website."


def details_sheet(answers: dict) -> dict:
    dec = answers.get("deceased") or {}
    es = answers.get("estatesearch") or {}
    ft = answers.get("discovery") or {}
    prev = ft.get("previous_addresses") or es.get("previous_addresses") or ""
    rows = [
        ("Full name", dec.get("full_name") or ""),
        ("Other or previous names", dec.get("other_names") or ""),
        ("Date of birth", dec.get("date_of_birth") or ""),
        ("Date of death", dec.get("date_of_death") or ""),
        ("Last address", dec.get("address") or ""),
        ("Other addresses in the last 6 years", "; ".join(x.strip() for x in prev.splitlines() if x.strip())),
    ]
    required = {"Full name", "Date of birth", "Date of death", "Last address", "Other addresses in the last 6 years"}
    return {"rows": [{"label": k, "value": v} for k, v in rows], "missing": [k for k, v in rows if k in required and not v]}


def tracker(answers: dict) -> list[dict]:
    ft = answers.get("discovery") or {}
    return [{**s, "status": ft.get("trace_" + s["id"]) if ft.get("trace_" + s["id"]) in STATUSES else "Not started"} for s in SERVICES]


def pack(answers: dict) -> dict:
    return {"details": details_sheet(answers), "services": tracker(answers), "statuses": STATUSES, "note": NOTE}
