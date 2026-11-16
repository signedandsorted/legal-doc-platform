from datetime import date

from .guides import SERVICES

DRAFT_NOTICE = "DRAFT FOR SOLICITOR REVIEW. This document has not been checked by a solicitor and must not be signed until it has."


def missing_fields(service_id: str, answers: dict) -> list[str]:
    missing = []
    for step in SERVICES[service_id]["steps"]:
        section = answers.get(step["id"]) or {}
        for field in step["fields"]:
            missing += _missing(field, section.get(field["name"]), step["title"])
    return missing


def _missing(field: dict, value, where: str) -> list[str]:
    label = f"{where}: {field['label']}"
    if field["type"] == "list":
        items = value or []
        out = [f"{label} (at least {field['min']})"] if len(items) < field.get("min", 0) else []
        for i, item in enumerate(items, 1):
            for sub in field["fields"]:
                out += _missing(sub, (item or {}).get(sub["name"]), f"{label} {i}")
        return out
    if field["type"] == "group":
        return [m for sub in field["fields"] for m in _missing(sub, (value or {}).get(sub["name"]), label)]
    if field.get("required") and (value is None or str(value).strip() == ""):
        return [label]
    return []


def _names(people) -> str:
    names = [p.get("full_name", "").strip() for p in people or [] if p and p.get("full_name")]
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _person(p: dict) -> str:
    parts = [p.get("full_name", "")]
    if p.get("address"):
        parts.append("of " + " ".join(p["address"].split()))
    return " ".join(parts)


def _money(value) -> str:
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def build_document(service_id: str, answers: dict) -> dict:
    return {"will": _will, "lpa_property": _lpa, "lpa_health": _lpa, "probate": _probate}[service_id](service_id, answers)


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


def _lpa(service_id: str, a: dict) -> dict:
    s = SERVICES[service_id]
    donor = a.get("donor", {})
    att = a.get("attorneys", {})
    rows = [
        {"heading": "Section 1: the donor", "paragraphs": [_person(donor), "Date of birth: " + donor.get("date_of_birth", "")]},
        {"heading": "Section 2: the attorneys", "paragraphs": [f"{_person(p)} (born {p.get('date_of_birth', '')})" for p in att.get("attorneys") or []]},
        {"heading": "Section 3: how decisions are made", "paragraphs": [att.get("decisions", "")] + ([att["joint_decisions"]] if att.get("joint_decisions") else [])},
        {"heading": "Section 4: replacement attorneys", "paragraphs": [f"{_person(p)} (born {p.get('date_of_birth', '')})" for p in a.get("replacements", {}).get("replacement_attorneys") or []] or ["None"]},
    ]
    if service_id == "lpa_property":
        rows.append({"heading": "Section 5: when the LPA can be used", "paragraphs": [a.get("when", {}).get("when_used", "")]})
    else:
        rows.append({"heading": "Section 5: life-sustaining treatment", "paragraphs": [a.get("life_sustaining", {}).get("life_sustaining", "")]})
    notify = a.get("notify", {})
    rows.append({"heading": "Section 6: people to notify", "paragraphs": [_person(p) for p in notify.get("people_to_notify") or []] or ["None"]})
    prefs = a.get("preferences", {})
    rows.append({"heading": "Section 7: preferences and instructions", "paragraphs": ["Preferences: " + (prefs.get("preferences") or "None"), "Instructions: " + (prefs.get("instructions") or "None")]})
    cp = notify.get("certificate_provider") or {}
    rows.append({"heading": "Certificate provider", "paragraphs": [_person(cp), cp.get("basis", "")]})
    return {"title": s["title"] + ": " + donor.get("full_name", ""), "notice": DRAFT_NOTICE + " This is a summary of your answers to transfer to the official LPA form or GOV.UK service; it is not itself the LPA.", "sections": rows, "next_steps": s["next_steps"]}


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
