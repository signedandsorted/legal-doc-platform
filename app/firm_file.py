"""Papers on a firm matter, and how far HMRC and HMCTS will let this desk go.

HMRC's IHT400 is printed and posted. The people named sign it. HMCTS takes the
grant through MyHMCTS, or on paper where that service will not. Neither body
lets this software send the application. The desk prepares the pack and records
what the firm has filed.
"""
from .common import money

PAPER_KINDS = ["Will", "Codicil", "Death certificate", "Bank or valuation letter", "Other"]
IHT400_URL = "https://www.gov.uk/government/publications/inheritance-tax-inheritance-tax-account-iht400"
PAY_URL = "https://www.gov.uk/paying-inheritance-tax"
MYHMCTS_URL = "https://www.gov.uk/government/publications/myhmcts-how-to-apply-for-probate-online/apply-for-probate-with-myhmcts"
MYHMCTS_CASE_URL = "https://manage-case.platform.hmcts.net"
MYHMCTS_ORG_URL = "https://manage-org.platform.hmcts.net"
MYHMCTS_REGISTER_URL = "https://www.gov.uk/guidance/register-for-myhmcts-online-case-management-for-professionals"
APPLY_URL = "https://www.gov.uk/apply-for-probate"


def filing_record(facts: dict) -> dict:
    raw = (facts or {}).get("filing") or {}
    return {
        "hmrc_code": str(raw.get("hmrc_code") or "")[:40],
        "hmrc_posted_on": str(raw.get("hmrc_posted_on") or "")[:10],
        "grant_filed_on": str(raw.get("grant_filed_on") or "")[:10],
        "grant_reference": str(raw.get("grant_reference") or "")[:40],
    }


def position(matter: dict, compiled: dict | None, uploads: list[dict]) -> dict:
    filing = filing_record(matter.get("facts") or {})
    forms = (compiled or {}).get("forms") or {}
    figures = (compiled or {}).get("figures") or {}
    blockers = list(forms.get("blockers") or [])
    kinds = {u.get("kind") for u in uploads}
    if matter.get("kind") == "probate":
        if "Death certificate" not in kinds:
            blockers.append("Upload the death certificate.")
        if not (compiled and compiled["books"]["lines"]):
            blockers.append("The estate list is empty. Add the assets or apply them from a bank letter.")
        will = (compiled or {}).get("books", {}).get("case", {}).get("has_will") or ""
        if will.startswith("Yes") and "Will" not in kinds and "Codicil" not in kinds:
            blockers.append("Upload the will. The original still has to be sent to HMCTS. This copy is for the file.")
    excepted = bool(figures.get("excepted")) if figures else True
    code = filing["hmrc_code"]
    hmcts_ready = not blockers and (excepted or bool(code))
    steps = []
    if not excepted and figures:
        steps.append("Print the pack, complete the official IHT400 in Adobe Reader, and post it. HMRC does not accept this form from other software.")
        if figures.get("tax"):
            steps.append("Pay the tax on GOV.UK. Apply for an Inheritance Tax reference at least three weeks before you pay.")
        steps.append("When HMRC sends the code, type it here. The grant application needs that code.")
    if hmcts_ready and "Online" in (figures.get("route") or ""):
        steps.append("File the grant in MyHMCTS. Copy the five figures from this file. Send the original will to the address MyHMCTS gives you. Do not send a paper PA form as well.")
    elif hmcts_ready:
        steps.append("MyHMCTS will not take this application. Use the paper PA form named below and post it with the original will.")
    elif blockers:
        steps.append("Finish the points below before anyone files.")
    return {
        "blockers": blockers,
        "excepted": excepted,
        "hmrc": {"needed": not excepted, "url": IHT400_URL, "pay_url": PAY_URL, **filing},
        "hmcts": {
            "url": MYHMCTS_URL, "case_url": MYHMCTS_CASE_URL, "org_url": MYHMCTS_ORG_URL,
            "register_url": MYHMCTS_REGISTER_URL, "public_url": APPLY_URL,
            "ready": hmcts_ready, "route": figures.get("route") or "", "fee": figures.get("fee"),
        },
        "steps": steps,
        "notice": "Nothing on this page is sent to HMRC or to HMCTS. A solicitor files it, then records the date and the code here.",
    }


def apply_suggestions(matter: dict, books: dict, chosen: list[dict]) -> tuple[dict, dict]:
    """Turn chosen readings into ledger lines and names. Returns (books, matter fields)."""
    fields = {}
    lines = list(books.get("lines") or [])
    people = list(books.get("people") or [])
    known = {ln.get("name") for ln in lines}
    known_people = {p.get("name") for p in people}
    for item in chosen:
        mode, field, value = item.get("mode"), item.get("field"), item.get("value")
        if mode == "set" and field == "full_name" and item.get("step") == "deceased" and isinstance(value, str):
            fields["deceased_name"] = value.strip()[:160]
        elif mode == "set" and field == "date_of_death" and isinstance(value, str):
            fields["date_of_death"] = value.strip()[:10]
        elif mode == "append" and field == "assets" and isinstance(value, dict):
            name = str(value.get("description") or "Asset from a paper")[:160]
            if name in known:
                continue
            try:
                amount = float(str(value.get("value") or "0").replace(",", ""))
            except ValueError:
                continue
            if amount < 0:
                continue
            lines.append({"name": name, "holder": "", "side": "asset", "ownership": "sole", "value": amount})
            known.add(name)
        elif mode == "note" and isinstance(item.get("label"), str) and item["label"].startswith("Executor named"):
            name = item["label"].split(":", 1)[-1].strip()
            if name and name not in known_people:
                people.append({"name": name, "relationship": "Executor", "share": 0})
                known_people.add(name)
    books = {**books, "lines": lines, "people": people}
    return books, fields


def pack_document(matter: dict, compiled: dict, uploads: list[dict], where: dict) -> dict:
    figures = compiled.get("figures") or {}
    accounts = compiled.get("accounts") or {}
    totals = accounts.get("totals") or {}
    estate = matter.get("deceased_name") or matter.get("title") or "the estate"
    sections = [
        {"heading": "The five figures", "paragraphs": [
            f"Gross for Inheritance Tax: {money(figures.get('gross_iht'))}",
            f"Net for Inheritance Tax: {money(figures.get('net_iht'))}",
            f"Net qualifying value: {money(figures.get('net_qualifying'))}",
            f"Gross for probate: {money(figures.get('gross_probate'))}",
            f"Net for probate: {money(figures.get('net_probate'))}",
            f"Tax estimate: {money(figures.get('tax'))}. Fee: {money(figures.get('fee'))}.",
            figures.get("route") or "",
        ]},
        {"heading": "The account", "paragraphs": [
            f"Collected {money(totals.get('collected'))}. Still to collect {money(totals.get('still_to_collect'))}.",
            f"Income {money(totals.get('income'))}. Costs {money(totals.get('costs'))}. Debts {money(totals.get('debts'))}. Funeral {money(totals.get('funeral'))}.",
            f"Left to share {money(totals.get('expected_net'))}. Cash held {money(totals.get('cash_in_hand'))}.",
        ] + [f"{p['name']}: share {money(p['entitlement'])}, paid {money(p['paid'])}, due {money(p['due'])}" for p in accounts.get("people") or []]},
    ]
    for form in (compiled.get("forms") or {}).get("schedule") or []:
        sections.append({"heading": f"{form['code']} — {form['label']}", "paragraphs": [f"{row[0]}: {row[1]}" for row in form["rows"][:40]]})
    if uploads:
        sections.append({"heading": "Papers on the file", "paragraphs": [f"{u['filename']} ({u['kind']})" for u in uploads]})
    sections.append({"heading": "How this is filed", "paragraphs": where["steps"] or ["Nothing to file yet."]})
    return {
        "title": f"Estate of {estate} — working pack",
        "notice": where["notice"],
        "sections": sections,
        "next_steps": where["steps"] or ["A solicitor reviews the pack before anything is posted or filed."],
        "sources": [
            {"title": "IHT400", "url": IHT400_URL},
            {"title": "Pay Inheritance Tax", "url": PAY_URL},
            {"title": "MyHMCTS probate", "url": MYHMCTS_URL},
            {"title": "Apply for probate", "url": APPLY_URL},
        ],
    }
