from datetime import date

from .common import DRAFT_NOTICE, missing_in
from .common import money as _money
from .common import names as _names  # noqa: F401
from .common import person as _person
from .doc_lpa import build_lpa, lpa_issues
from .guides import SERVICES


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
    return []


def _dedupe(sources: list) -> list:
    seen, out = set(), []
    for x in sources:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out


def build_document(service_id: str, answers: dict, uploads: list | None = None) -> dict:
    if service_id.startswith("lpa_"):
        doc = build_lpa(service_id, answers, uploads)
    else:
        doc = {"will": _will, "probate": _probate}[service_id](service_id, answers)
        doc["sources"] = [x for st in SERVICES[service_id]["steps"] for x in st.get("sources", [])]
    doc["sources"] = _dedupe(doc.get("sources", []))
    doc["issues"] = find_issues(service_id, answers, " ".join(u.get("text", "") for u in uploads or []))
    return doc


def _will(_, a: dict) -> dict:
    me = a.get("about_you", {})
    ex = a.get("executors", {})
    gd = a.get("guardians", {})
    gifts = a.get("gifts", {}).get("gifts") or []
    res = a.get("residue", {})
    wishes = a.get("wishes", {})
    clauses = []
    clauses.append(f"I, {_person(me)}, revoke all my earlier wills and codicils and declare this to be my last will.")
    executors = ex.get("executors") or []
    clauses.append(f"I appoint {'; '.join(_person(p) for p in executors)} to be my executor{'s' if len(executors) > 1 else ''}.")
    rep = ex.get("replacement_executor") or {}
    if rep.get("full_name"):
        clauses.append(f"If any executor named above dies before me, or is unable or unwilling to act, I appoint {_person(rep)} in their place.")
    if gd.get("guardians"):
        clauses.append(f"If no parent with parental responsibility survives me, I appoint {'; '.join(_person(p) for p in gd['guardians'])} to be the guardian{'s' if len(gd['guardians']) > 1 else ''} of any of my children who are under 18.")
    for gift in gifts:
        clauses.append(f"I give {gift.get('gift', '')} to {gift.get('beneficiary', '')}, if they survive me, free of inheritance tax.")
    people = res.get("residuary_beneficiaries") or []
    total = sum(float(p.get("share") or 0) for p in people) or 1
    shares = "; ".join(f"{p.get('full_name')} ({p.get('relationship') or 'beneficiary'}): {float(p.get('share') or 0) / total:.0%}" for p in people)
    clauses.append("I give the rest of my estate, after payment of my debts, funeral and testamentary expenses and any gifts above (my residuary estate), to my trustees to hold on trust to sell or keep, and to divide among the following people who survive me by 28 days, in these shares: " + shares + ".")
    if res.get("substitution", "").startswith("Their children"):
        clauses.append("If any of them dies before me, or within 28 days of me, leaving children who survive me, those children take equally the share their parent would have taken.")
    else:
        clauses.append("If any of them dies before me, or within 28 days of me, their share is added to the shares of the others in proportion.")
    if res.get("ultimate_beneficiary"):
        clauses.append(f"If none of the gifts of my residuary estate take effect, I give my residuary estate to {res['ultimate_beneficiary']}.")
    clauses.append("My trustees have the powers given to trustees by law, including the Trustee Act 2000, and may appropriate assets in or towards any share without the consent of any beneficiary.")
    if wishes.get("funeral_wishes") and wishes["funeral_wishes"] != "No preference":
        clauses.append(f"I would like my body to be {'buried' if wishes['funeral_wishes'] == 'Burial' else 'cremated'}. {wishes.get('funeral_notes') or ''}".strip())
    elif wishes.get("funeral_notes"):
        clauses.append("My funeral wishes are: " + wishes["funeral_notes"])
    sections = [{"heading": "Last will and testament of " + me.get("full_name", ""), "paragraphs": [f"{i}. {c}" for i, c in enumerate(clauses, 1)]}]
    sections.append({"heading": "Signature", "paragraphs": [
        "Signed by the testator in our presence, both present at the same time, and then signed by each of us in the testator's presence.",
        "Testator signature: ______________________   Date: ____________",
        "Witness 1 signature, full name, address and occupation: ______________________________________________",
        "Witness 2 signature, full name, address and occupation: ______________________________________________",
    ]})
    return {"title": "Will: " + me.get("full_name", ""), "notice": DRAFT_NOTICE, "sections": sections, "next_steps": SERVICES["will"]["next_steps"]}


def _probate(_, a: dict) -> dict:
    d = a.get("deceased", {})
    w = a.get("will", {})
    e = a.get("estate", {})
    assets = e.get("assets") or []
    debts = e.get("debts") or []
    gross = sum(float(x.get("value") or 0) for x in assets)
    owed = sum(float(x.get("value") or 0) for x in debts)
    sections = [
        {"heading": "The person who died", "paragraphs": [_person(d), "Date of death: " + d.get("date_of_death", ""), "Death registered: " + d.get("death_registered", "")]},
        {"heading": "Will and applicant", "paragraphs": ["Will: " + w.get("has_will", ""), "Applicant: " + _person(w.get("applicant") or {}), "Likely application: " + ("grant of probate (form PA1P)" if str(w.get("has_will", "")).startswith("Yes") else "letters of administration (form PA1A)")]},
        {"heading": "Assets", "paragraphs": [f"{x.get('description')}: {_money(x.get('value'))}{' (jointly owned)' if x.get('jointly_owned') == 'Yes' else ''}" for x in assets] or ["None listed yet"]},
        {"heading": "Debts and funeral costs", "paragraphs": [f"{x.get('description')}: {_money(x.get('value'))}" for x in debts] or ["None listed yet"]},
        {"heading": "Estimated estate", "paragraphs": [f"Gross estate: {_money(gross)}", f"Debts: {_money(owed)}", f"Net estate: {_money(gross - owed)}", "These are estimates. A solicitor will check whether Inheritance Tax is due and which HMRC forms are needed."]},
    ]
    if e.get("gifts_in_last_7_years"):
        sections.append({"heading": "Gifts in the 7 years before death", "paragraphs": [e["gifts_in_last_7_years"]]})
    return {"title": "Probate summary: " + d.get("full_name", ""), "notice": "Prepared " + date.today().strftime("%d %B %Y") + ". " + DRAFT_NOTICE, "sections": sections, "next_steps": SERVICES["probate"]["next_steps"]}
