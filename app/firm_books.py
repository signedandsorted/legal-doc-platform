"""One set of probate figures for the firm desk.

Date-of-death values go through the same plan() the public probate helper uses,
so the five grant figures, the tax estimate and the form list cannot drift.
The cash account and the distributions use what has actually been collected and paid.
"""
from uuid import uuid4

from .common import money
from .firm_account import KIND_LABEL, clean_copied, clean_discovery, clean_notice, guess_kind, notice_text, step_account
from .doc_probate import plan
from .guide_probate import APPLICANT_ROLES, FULL_DETAIL_TRIGGERS

OWNERSHIP = {
    "sole": "Owned on their own",
    "joint_tenants": "Joint tenants (passes automatically to the other owner)",
    "tenants_in_common": "Tenants in common (enter their share only)",
}
WILL = ["Yes, I have the original", "Yes, but the original is lost", "No", "Not sure"]
DOMICILE = ["Yes", "No, elsewhere in the UK", "No, outside the UK"]
MARITAL = ["Married or in a civil partnership", "Widowed or a surviving civil partner", "Divorced or civil partnership dissolved", "Separated", "Never married"]
CERT = ["UK death certificate", "Interim certificate from the coroner", "Certificate from outside England or Wales", "Not yet"]
OTHERS = ["None", "Holding power reserved", "Giving up the right to apply (renouncing)", "Want to appoint someone to apply for them", "Have died", "Cannot apply because of a mental health condition or impairment"]
SPOUSE = ["They are applying", "They are giving up their right (form PA16)", "There is no surviving spouse or civil partner"]
APPLICANTS = ["1", "2", "3", "4", "More than 4"]
FEES = ["No", "Yes", "Not sure"]


def _num(value) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    if n != n or n < 0 or n > 1e12:
        return 0.0
    return round(n, 2)


def _text(value, limit=240) -> str:
    return str(value or "").strip()[:limit]


def _pick(value, allowed, default=""):
    return value if value in allowed else default


def empty_books() -> dict:
    return {"lines": [], "people": [], "case": {}, "letters": []}


def _line(raw: dict, n: int) -> dict:
    side = "debt" if raw.get("side") == "debt" else "asset"
    ownership = raw.get("ownership") if raw.get("ownership") in OWNERSHIP else "sole"
    realised = raw.get("realised")
    return {
        "id": _text(raw.get("id"), 12) or uuid4().hex[:8],
        "side": side,
        "name": _text(raw.get("name"), 160) or ("Debt" if side == "debt" else "Asset"),
        "holder": _text(raw.get("holder"), 160),
        "ownership": ownership,
        "value": _num(raw.get("value")),
        "joint": raw.get("joint") == "Yes" or raw.get("joint") is True,
        "abroad": raw.get("abroad") == "Yes" or raw.get("abroad") is True,
        "realised": None if realised in (None, "") else _num(realised),
        "income": _num(raw.get("income")),
        "costs": _num(raw.get("costs")),
        "paid": bool(raw.get("paid")),
        "funeral": bool(raw.get("funeral")) and side == "debt",
        "kind": raw.get("kind") if raw.get("kind") in ("property", "bank", "shares", "goods", "pension", "other") else guess_kind(raw.get("name") or ""),
    }


def _person(raw: dict, n: int) -> dict:
    return {
        "id": _text(raw.get("id"), 12) or uuid4().hex[:8],
        "name": _text(raw.get("name"), 160) or "Beneficiary",
        "relationship": _text(raw.get("relationship"), 80),
        "specific": _num(raw.get("specific")),
        "share": min(100.0, _num(raw.get("share"))),
        "paid": _num(raw.get("paid")),
    }


def clean_books(raw: dict | None) -> dict:
    raw = raw or {}
    case = raw.get("case") or {}
    triggers = [k for k, _ in FULL_DETAIL_TRIGGERS if case.get(k) in (True, "Yes", "yes", "on")]
    clean_case = {
        "address": _text(case.get("address"), 400),
        "date_of_birth": _text(case.get("date_of_birth"), 10),
        "domicile": _pick(case.get("domicile"), DOMICILE, "Yes"),
        "marital_status": _pick(case.get("marital_status"), MARITAL),
        "death_certificate": _pick(case.get("death_certificate"), CERT),
        "has_will": _pick(case.get("has_will"), WILL),
        "applicant_role": _pick(case.get("applicant_role"), APPLICANT_ROLES),
        "applicant_address": _text(case.get("applicant_address"), 400),
        "applicant_phone": _text(case.get("applicant_phone"), 40),
        "applicants": _pick(case.get("applicants"), APPLICANTS, "1"),
        "other_executors": _pick(case.get("other_executors"), OTHERS),
        "surviving_spouse_applying": _pick(case.get("surviving_spouse_applying"), SPOUSE),
        "help_with_fees": _pick(case.get("help_with_fees"), FEES, "No"),
        "to_spouse": _num(case.get("to_spouse")),
        "to_charity": _num(case.get("to_charity")),
        "home_to_descendants": "Yes" if case.get("home_to_descendants") in (True, "Yes") else "No",
        "home_value_to_descendants": _num(case.get("home_value_to_descendants")),
        "earlier_spouse_died": "Yes" if case.get("earlier_spouse_died") in (True, "Yes") else "No",
        "unused_nrb_percent": min(100.0, _num(case.get("unused_nrb_percent") if case.get("unused_nrb_percent") not in (None, "") else 100)),
        "gifts_7_years": _num(case.get("gifts_7_years")),
        "tax_paid": _num(case.get("tax_paid")),
    }
    for key in triggers:
        clean_case[key] = True
    letters = []
    for i, letter in enumerate((raw.get("letters") or [])[:40]):
        if not isinstance(letter, dict):
            continue
        letters.append({
            "id": _text(letter.get("id"), 12) or f"e{i}",
            "title": _text(letter.get("title"), 160),
            "body": _text(letter.get("body"), 8000),
            "at": _text(letter.get("at"), 40),
            "by": _text(letter.get("by"), 254),
        })
    return {
        "lines": [_line(x, i) for i, x in enumerate((raw.get("lines") or [])[:80]) if isinstance(x, dict)],
        "people": [_person(x, i) for i, x in enumerate((raw.get("people") or [])[:40]) if isinstance(x, dict)],
        "case": clean_case,
        "letters": letters,
        "discovery": clean_discovery(raw.get("discovery")),
        "notice": clean_notice(raw.get("notice")),
        "copied": clean_copied(raw.get("copied")),
    }


def to_answers(matter: dict, books: dict) -> dict:
    """The public probate draft's answer shape, so plan() is the only tax engine."""
    case = books["case"]
    assets, debts, funeral = [], [], 0.0
    for line in books["lines"]:
        if line["funeral"]:
            funeral += line["value"]
            continue
        if line["side"] == "debt":
            debts.append({"description": line["name"], "value": line["value"], "joint": "Yes" if line["joint"] else "No"})
        else:
            assets.append({
                "description": line["name"],
                "value": line["value"],
                "ownership": OWNERSHIP[line["ownership"]],
                "abroad": "Yes" if line["abroad"] else "No",
            })
    tax = {
        "to_spouse": case["to_spouse"],
        "to_charity": case["to_charity"],
        "home_to_descendants": case["home_to_descendants"],
        "home_value_to_descendants": case["home_value_to_descendants"],
        "earlier_spouse_died": case["earlier_spouse_died"],
        "unused_nrb_percent": case["unused_nrb_percent"],
        "gifts_7_years": case["gifts_7_years"],
    }
    for key, _label in FULL_DETAIL_TRIGGERS:
        if case.get(key):
            tax[key] = True
    return {
        "deceased": {
            "full_name": matter.get("deceased_name") or "",
            "date_of_death": matter.get("date_of_death") or "",
            "date_of_birth": case["date_of_birth"],
            "address": case["address"],
            "domicile": case["domicile"],
            "marital_status": case["marital_status"],
            "death_certificate": case["death_certificate"],
        },
        "will": {
            "has_will": case["has_will"],
            "applicant_role": case["applicant_role"],
            "applicant": {
                "full_name": matter.get("client_name") or "",
                "address": case["applicant_address"],
                "email": matter.get("client_email") or "",
                "phone": case["applicant_phone"],
            },
            "applicants": case["applicants"],
            "other_executors": case["other_executors"],
            "surviving_spouse_applying": case["surviving_spouse_applying"],
            "help_with_fees": case["help_with_fees"],
        },
        "estate": {"assets": assets, "debts": debts, "funeral_costs": funeral},
        "tax": tax,
    }


def _accounts(books: dict, worked: dict) -> dict:
    outside, capital, debt_rows = [], [], []
    collected = still = income = costs = debt_total = debt_paid = funeral = funeral_paid = 0.0
    for line in books["lines"]:
        if line["funeral"]:
            funeral += line["value"]
            if line["paid"]:
                funeral_paid += line["value"]
            continue
        if line["side"] == "debt":
            debt_rows.append({"name": line["name"], "value": line["value"], "paid": line["paid"], "joint": line["joint"]})
            if not line["joint"]:
                debt_total += line["value"]
                if line["paid"]:
                    debt_paid += line["value"]
            continue
        passes = line["ownership"] == "joint_tenants" or line["abroad"]
        why = "Joint tenants: this passes to the other owner and is not in the probate figures." if line["ownership"] == "joint_tenants" else "Outside the UK: not in the probate figures. A solicitor decides how it is collected."
        if passes:
            outside.append({"name": line["name"], "holder": line["holder"], "value": line["value"], "why": why})
            continue
        worth = line["value"] if line["realised"] is None else line["realised"]
        capital.append({
            "name": line["name"], "holder": line["holder"], "dod": line["value"],
            "collected": 0.0 if line["realised"] is None else line["realised"],
            "still": line["value"] if line["realised"] is None else 0.0,
            "income": line["income"], "costs": line["costs"],
        })
        if line["realised"] is None:
            still += line["value"]
        else:
            collected += line["realised"]
        income += line["income"]
        costs += line["costs"]
    tax = worked["tax"]["tax"]
    tax_paid = books["case"]["tax_paid"]
    cash = collected + income - costs - debt_paid - funeral_paid - tax_paid
    expected = collected + still + income - costs - debt_total - funeral - tax
    people_in = books["people"]
    specific = sum(p["specific"] for p in people_in)
    shares = sum(p["share"] for p in people_in)
    warnings = []
    if people_in and shares == 0:
        each = 100 / len(people_in)
        shares_used = {p["id"]: each for p in people_in}
    else:
        shares_used = {p["id"]: p["share"] for p in people_in}
        if people_in and abs(shares - 100) > 0.05:
            warnings.append(f"Residue shares add up to {shares:.2f}%, not 100%.")
    if specific > max(0.0, expected) + 0.01:
        warnings.append("The specific gifts are more than the estate now comes to. A solicitor decides what is paid.")
    residue = expected - specific
    if any(d["joint"] for d in debt_rows):
        warnings.append("Joint debts are left out of the probate net, matching the grant figures. A solicitor confirms who pays them.")
    people = []
    for p in people_in:
        ent = p["specific"] + max(0.0, residue) * shares_used[p["id"]] / 100
        people.append({**p, "share_used": round(shares_used[p["id"]], 2), "entitlement": round(ent, 2), "due": round(ent - p["paid"], 2)})
        if p["paid"] > ent + 0.01:
            warnings.append(f"{p['name']} has been paid more than their share.")
    return {
        "outside": outside,
        "capital": capital,
        "debts": debt_rows,
        "funeral": funeral,
        "totals": {
            "collected": round(collected, 2), "still_to_collect": round(still, 2), "income": round(income, 2),
            "costs": round(costs, 2), "debts": round(debt_total, 2), "debts_paid": round(debt_paid, 2),
            "funeral": round(funeral, 2), "funeral_paid": round(funeral_paid, 2),
            "tax": round(tax, 2), "tax_paid": round(tax_paid, 2),
            "cash_in_hand": round(cash, 2), "expected_net": round(expected, 2),
            "specific": round(specific, 2), "residue": round(residue, 2),
        },
        "people": people,
        "warnings": warnings,
        "step": None,
    }


def _forms(matter: dict, books: dict, answers: dict, worked: dict) -> dict:
    v, tax, case = worked["values"], worked["tax"], books["case"]
    deceased = [
        ["Full name", matter.get("deceased_name") or ""],
        ["Date of death", matter.get("date_of_death") or ""],
        ["Last address", case["address"]],
        ["Lived permanently in England or Wales", case["domicile"]],
        ["Marital status", case["marital_status"]],
        ["Death certificate", case["death_certificate"]],
        ["Will", case["has_will"] or "Not entered"],
        ["Applicant", matter.get("client_name") or ""],
        ["Applying as", case["applicant_role"]],
        ["Applicant address", case["applicant_address"]],
        ["Number applying", case["applicants"]],
    ]
    five = [
        ["Gross estate for Inheritance Tax", money(v["gross_iht"])],
        ["Net estate for Inheritance Tax", money(v["net_iht"])],
        ["Net qualifying value", money(v["net_qualifying"])],
        ["Gross value for probate", money(v["gross_probate"])],
        ["Net value for probate", money(v["net_probate"])],
        ["Fee", "No fee" if worked["fee"] == 0 else money(worked["fee"])],
    ]
    schedule = []
    for code, label in worked["forms"]:
        rows = deceased + five if code in ("PA1P", "PA1A") else []
        if code == "IHT400":
            rows = [
                ["Gross for Inheritance Tax", money(v["gross_iht"])],
                ["Debts and funeral", money(v["gross_iht"] - v["net_iht"])],
                ["Net for Inheritance Tax", money(v["net_iht"])],
                ["Left to a spouse or civil partner", money(case["to_spouse"])],
                ["Left to charity", money(case["to_charity"])],
                ["Net qualifying value", money(v["net_qualifying"])],
                ["Gifts in the 7 years", money(v["gifts"])],
                ["Nil rate band used", money(tax["nrb"])],
                ["Residence nil rate band used", money(tax["rnrb"])],
                ["Tax estimate", money(tax["tax"])],
            ] + [[line["name"], money(line["value"])] for line in books["lines"]]
        schedule.append({"code": code, "label": label, "rows": rows or deceased})
    grouped = {kind: [] for kind in KIND_LABEL}
    for line in books["lines"]:
        if line["side"] != "asset" or line["ownership"] == "joint_tenants" or line["abroad"]:
            continue
        grouped[line["kind"]].append([line["name"] + (f" — {line['holder']}" if line["holder"] else ""), money(line["value"])])
    for kind, label in KIND_LABEL.items():
        if grouped[kind]:
            schedule.append({"code": "IHT400 · " + label, "label": "Copy onto the official schedule for this type of asset", "rows": grouped[kind]})
    return {
        "route": worked["route"],
        "grant": worked["grant"],
        "excepted": worked["excepted"],
        "reasons": worked["estate_reasons"],
        "blockers": worked["blockers"],
        "post_reasons": worked["post_reasons"],
        "issues": [i["message"] for i in worked["issues"]],
        "schedule": schedule,
        "notice": "Working paper to copy onto the official form. It is not the form HMRC or the court issue, and nothing is sent to them from here.",
    }


def compile_books(matter: dict, books: dict | None = None) -> dict:
    books = clean_books(books if books is not None else (matter.get("facts") or {}).get("books"))
    if matter.get("kind") != "probate":
        return {"books": books, "figures": None, "accounts": None, "forms": None}
    answers = to_answers(matter, books)
    worked = plan(answers)
    v, tax = worked["values"], worked["tax"]
    accounts = _accounts(books, worked)
    accounts["step"] = step_account(accounts)
    return {
        "books": books,
        "answers": answers,
        "figures": {
            "gross_iht": v["gross_iht"], "net_iht": v["net_iht"], "net_qualifying": v["net_qualifying"],
            "gross_probate": v["gross_probate"], "net_probate": v["net_probate"],
            "tax": tax["tax"], "threshold": tax["threshold"], "nrb": tax["nrb"], "rnrb": tax["rnrb"],
            "excepted": worked["excepted"], "fee": worked["fee"], "route": worked["route"], "grant": worked["grant"],
        },
        "accounts": accounts,
        "forms": _forms(matter, books, answers, worked),
    }


def letter_text(kind: str, matter: dict, compiled: dict) -> dict | None:
    books = compiled["books"]
    figures = compiled.get("figures") or {}
    name = matter.get("client_name") or "there"
    estate = matter.get("deceased_name") or "the person who died"
    died = matter.get("date_of_death") or "the date of death"
    if kind == "bank":
        pending = [ln for ln in books["lines"] if ln["side"] == "asset" and ln["realised"] is None and not ln["abroad"]]
        if not pending:
            pending = [ln for ln in books["lines"] if ln["side"] == "asset"]
        lines = [f"- {ln['name']}" + (f", {ln['holder']}" if ln["holder"] else "") for ln in pending] or ["- [account or property]"]
        body = "\n".join([
            "Dear Sir or Madam,", "",
            f"We act in the estate of {estate}, who died on {died}.",
            "Please let us have the balance, or the value, at the date of death for:", "",
            *lines, "",
            "A copy of the death certificate can follow. Please also say whether you will release the funds without a grant.",
            "", "Yours faithfully,", name,
        ])
        return {"title": f"Value request — estate of {estate}", "body": body}
    if kind == "beneficiary":
        rows = compiled.get("accounts", {}).get("people") or []
        detail = [f"- {p['name']}: estimated share {money(p['entitlement'])}, paid {money(p['paid'])}, still due {money(p['due'])}" for p in rows]
        body = "\n".join([
            "Dear ", "",
            f"This is a short update on the estate of {estate}.",
            f"The current estimate of what is left to share is {money((compiled.get('accounts') or {}).get('totals', {}).get('expected_net', 0))}.",
            "That figure moves when assets are collected or bills are paid. It is not a final account.", "",
            *(detail or ["No beneficiary shares have been entered yet."]), "",
            "Nothing in this letter is a promise to pay on a particular date.",
            "", "Yours sincerely,", name,
        ])
        return {"title": f"Beneficiary update — estate of {estate}", "body": body}
    if kind == "grant":
        body = "\n".join([
            "Dear Sir or Madam,", "",
            f"The grant has been issued in the estate of {estate}, who died on {died}.",
            "Please close the account and send the closing balance to the estate.",
            "We will send a court-sealed copy of the grant with this letter.",
            "", "Yours faithfully,", name,
        ])
        return {"title": f"After the grant — estate of {estate}", "body": body}
    if kind == "notice":
        return notice_text(matter, books)
    if kind == "client":
        return None
    return None
