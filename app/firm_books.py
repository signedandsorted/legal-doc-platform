"""One set of probate figures for the firm desk.

Date-of-death values go through the same plan() the public probate helper uses,
so the five grant figures, the tax estimate and the form list cannot drift.
The cash account and the distributions use what has actually been collected and paid.
"""
from uuid import uuid4

from .common import money
from .firm_account import KIND_LABEL, clean_asset_search, clean_copied, clean_covers, clean_credit, clean_discovery, clean_notice, clean_orders, clean_vrs, clean_will_search, credit_letter, estatesearch_letter, guess_kind, notice_text, step_account
from .iht_schedules import CATALOGUE, choose_schedules, clean_form_choice, with_choice
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
        "credit": clean_credit(raw.get("credit")),
        "asset_search": clean_asset_search(raw.get("asset_search")),
        "orders": clean_orders(raw.get("orders")),
        "will_search": clean_will_search(raw.get("will_search")),
        "covers": clean_covers(raw.get("covers")),
        "vrs": clean_vrs(raw.get("vrs")),
        "form_choice": clean_form_choice(raw.get("form_choice")),
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
        "suggested": [{"code": item["code"], "why": item["why"]} for item in choose_schedules(books, worked)],
        "chosen": [{"code": item["code"], "why": item["why"], "ready": item["ready"], "source": item.get("source") or "figures"} for item in with_choice(choose_schedules(books, worked), books.get("form_choice") or {})],
        "catalogue": [{"code": code, "label": label} for code, label in CATALOGUE.items()],
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
    if kind.startswith("lex_"):
        from .lexcel import letter as lexcel_letter
        return lexcel_letter(kind, matter, matter.get("_conflict_matches"))
    if kind in ("act1975", "golden", "couple", "file_summary", "old_will", "retainer"):
        return protection_letter(kind, matter)
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
    if kind == "credit":
        return credit_letter(matter, books)
    if kind == "estatesearch":
        return estatesearch_letter(matter, books)
    if kind in ("will_ipw", "will_sww", "will_probate", "will_local"):
        return will_finder_letter(kind, matter, books)
    if kind == "pension":
        return pension_letter(matter, books)
    if kind == "client":
        return None
    return None


def protection_letter(kind: str, matter: dict) -> dict:
    """File notes and client letters. Nothing is sent. None of them stops a claim."""
    if kind == "retainer":
        from .retainer import document as retainer_document
        record = ((matter.get("facts") or {}).get("retainer") or {})
        doc = retainer_document(record, matter.get("client_name") or "")
        return {"title": doc["title"], "body": "\n\n".join(doc["sections"][0]["paragraphs"])}
    client = matter.get("client_name") or "the client"
    kind_label = matter.get("kind") or "matter"
    estate = matter.get("deceased_name") or ""
    who = estate or client
    if kind == "act1975":
        body = "\n".join([
            f"Dear {client},",
            "",
            "This letter is about the Inheritance (Provision for Family and Dependants) Act 1975. It is not legal advice beyond what we discuss with you, and it does not stop a claim.",
            "",
            "Some people can ask a court for reasonable financial provision from an estate if a will, or the intestacy rules, do not provide it. That can include a husband, wife or civil partner, a former spouse who has not formed a new marriage or civil partnership, a child, someone treated as a child of the family, a person who was being maintained, and a partner who lived with the person who died as husband, wife or civil partner for the whole of the two years before the death.",
            "",
            "A claim is normally brought within six months of the grant of probate or letters of administration. A spouse’s or civil partner’s claim is not limited to maintenance. Most other claims are.",
            "",
            "If you are leaving someone out, or leaving them less than they might expect, tell us in your own words why. We keep those reasons in a statement that is not part of the will. The statement can help if a claim is made. It does not prevent the claim, and it does not make this firm immune from a complaint or a claim.",
            "",
            "Please tell us if anyone who might claim has not been mentioned.",
            "",
            "Yours sincerely,",
            "Signed and Sorted",
            "",
            "This letter has not been sent. The firm sends it.",
        ])
        return {"title": f"1975 Act — {who}", "body": body}
    if kind == "golden":
        body = "\n".join([
            f"Attendance note — {client}",
            f"Matter: {kind_label}" + (f" — estate of {estate}" if estate else ""),
            "",
            "This note is for the file. It is not a medical report and it does not decide capacity.",
            "",
            "1. Date and place of the meeting:",
            "2. Who was in the room. Instructions should be taken with the client alone. If someone else was there, say who, and whether the client was then seen alone:",
            "3. Banks v Goodfellow, in the client’s own words as far as possible:",
            "   - Do they understand they are making a will and the effect of it?",
            "   - Do they understand, in broad terms, what they own?",
            "   - Can they comprehend the people they ought to consider?",
            "   - Is there a disorder of the mind that poisons those decisions?",
            "4. Golden rule (Kenward v Adams). It is practice, not a ground of invalidity (Hughes v Pritchard). If the client is elderly or seriously ill, or capacity may be doubted, a doctor should examine them, apply that test, and write a note. Doctor instructed: yes / not needed / not yet. Do not delay the will so long that it is never signed.",
            "5. Any sign of pressure or undue influence:",
            "6. Why anyone is left out, in the client’s words (kept off the will):",
            "7. Gift to the drafter, their family or an employee? If yes, independent advice under the SRA wills guidance (25 November 2019) and Code paragraph 6.1, or the reason for an exception:",
            "8. Mirror or mutual. Mirror: each can change their own will, including after the first death, unless a separate promise was made. The mirror will says on its face that it is not mutual. Mutual: after the first death the survivor may be bound by a constructive trust. A will cannot be made irrevocable. Mutual wording is a warning, not a finished clause. Which was explained, and what the client chose:",
            "9. If these are mirror wills for a couple the firm acted for together: information is shared. If one of them later wants to change their will without the other knowing, the firm usually cannot take that instruction. Explained: yes / not this matter.",
            "10. Old will, if one was uploaded. A person read the original or a full copy, not only the machine reading. It was not marked or destroyed. Every codicil is on the file. Where the original is:",
            "11. If this firm drew the old will and it may be wrong: nothing in this note admits liability. Insurers, and whether the firm is in conflict, are considered before the firm corrects its own work.",
            "12. The client was told this note does not stop a claim and does not make the firm immune.",
            "",
            "Signed: ______________________   Date: ____________",
        ])
        return {"title": f"Golden rule attendance note — {client}", "body": body}
    if kind == "couple":
        body = "\n".join([
            f"Dear {client},",
            "",
            "You asked about wills for a couple. These words follow the distinction drawn by the Society of Will Writers. They are not a promise that a later court will agree, and they do not stop either of you changing your mind while you are both alive.",
            "",
            "Mirror wills are two separate wills in similar terms. Each of you can change or revoke your own will at any time, including after the other has died, unless you have made a separate binding promise. Signing similar wills does not, by itself, create that promise. We put a sentence in a mirror will saying that either of you can change it, so it is not later called a mutual will.",
            "",
            "Mutual wills are different. You would be agreeing that neither of you will revoke the will. It is not possible to make a will irrevocable. While you are both alive, either of you can still revoke. After the first death, if the survivor accepts the benefit, equity can enforce the agreement by a constructive trust, so the survivor may not be free to change who inherits. A later marriage can still revoke the will. Mutual wills are rarely what a couple wants. We will not draft one unless both of you have been advised, and each of you has had the chance to be advised separately. The draft on the file is a warning, not a finished mutual-will clause.",
            "",
            "Where we act for you both, what one of you tells us is shared with the other. If one of you later wants to change a will without the other knowing, we usually cannot take that instruction, because we already know the other’s affairs and we would have to tell the person instructing us of a conflict. That is a limit of a joint retainer. It is not a promise that the survivor cannot change a mirror will.",
            "",
            "A life interest, so the survivor can live in the home and the capital is then protected for the children, is often a better way to deal with the worry that the survivor will change the will. That is a decision for you, after advice.",
            "",
            "Yours sincerely,",
            "Signed and Sorted",
            "",
            "This letter has not been sent. The firm sends it.",
        ])
        return {"title": f"Mirror and mutual wills — {client}", "body": body}
    if kind == "old_will":
        body = "\n".join([
            f"File note — review of an earlier will — {client}",
            f"Matter: {kind_label}" + (f" — estate of {estate}" if estate else ""),
            "",
            "File protection is the record that lets someone who was not at the meeting say, years later, how this will was made. It is the attendance note, the family and the assets, what was said about capacity, why anyone was left out, whether the wills are mirror or mutual, how the paper was signed, and the earlier wills. It is what the file uses for a Larke v Nugus request, a 1975 Act claim, or a negligence claim. It does not make the firm immune, and a tick on a screen is not the note.",
            "",
            "The Law Society’s practice note on file retention: wills and probate (1 November 2018), as the Society repeated on 2 August 2019, says an original will stored by the firm is the client’s property and, after the death, the estate’s. Keep it until after the death or until it is returned. There is no absolute period. Some firms keep wills indefinitely. Some keep them for fifty years. Ask the client before any original is destroyed, even if a later will is thought to exist. A revoked will can still be evidence. If a will is revoked, keep a copy. A claim about how a will was drafted often arises on death, not on the day it was signed, so the preparation file is kept on the same basis.",
            "",
            "What the machine reading is not",
            "1. The text extracted from an upload is not the will. A person reads the original, or a complete copy of every page and every codicil, before a new will is signed. A photograph can drop a line, including the word “not”.",
            "2. Do not cross out, write on, or use correction fluid on the old will. The Institute of Professional Willwriters’ public note is that this can make the whole will invalid. Make a new will, or a codicil for a small change. Wills Act 1837 section 21: an alteration after signing counts only if it is executed like a will, or the court is satisfied the words were already there.",
            "3. Do not destroy the original. It applies until the new will is signed and witnessed. If the new will fails, the old one may be the last valid will.",
            "4. Collect every codicil. A codicil can change, confirm or revive a will (section 22).",
            "",
            "Points to decide before the new will is signed",
            "5. Mirror or mutual. Following the Society of Will Writers: mirror wills can each be changed, including after the first death, unless there was a separate promise. Mutual wills can bind the survivor after the first death by a constructive trust. A will still cannot be made irrevocable. A mirror will says on its face that it is not mutual. A mutual will is a warning on this file, not a finished clause.",
            "6. A joint will is one document for two people. It is not a pair of mirror wills.",
            "7. Marriage or civil partnership usually revokes an earlier will unless it was made in expectation of that marriage or partnership and says so (sections 18 and 18B). Divorce or dissolution does not revoke the whole will: the former spouse or civil partner is treated as having died for gifts and appointments (sections 18A and 18C).",
            "8. A gift to a witness, or to their spouse or civil partner, is void. The rest of the will stands (section 15). Check the old attestation.",
            "9. A general revocation clause can cancel a foreign will the client meant to keep. Joint property, pension nominations, death-in-service benefits and policies written in trust usually pass outside the will. A specific gift of something the client no longer owns fails. Do not copy those gifts without checking.",
            "10. Nil-rate-band trusts, debt-and-charge schemes and STEP provisions are not deleted or swapped by the machine. Note the edition. The second edition of the STEP provisions is often used with some clauses excluded.",
            "11. A list “to be written later” is usually not part of the will. Do not staple a new list to the old will. A letter of wishes stays off the will. Reasons for leaving someone out stay off the will, in a signed statement. The statement does not stop a 1975 Act claim.",
            "12. If capacity is now in doubt, an earlier will may be the valid one. Do not destroy it. The golden rule is the file practice for the new will. It does not, by itself, invalidate the old one.",
            "13. If this firm drew the old will and the review shows it may be wrong, this note does not admit liability. Consider notifying insurers of circumstances, and whether the firm is now in conflict, before acting on a correction. The client may need independent advice.",
            "14. Where the original old will is now:",
            "15. The person who read it, and the date:",
            "",
            "Signed: ______________________   Date: ____________",
        ])
        return {"title": f"Old will review — {client}", "body": body}
    body = "\n".join([
        f"Dear {client},",
        "",
        f"This is a summary of your {kind_label} file" + (f" for the estate of {estate}" if estate else "") + ".",
        "It sets out the stage the file has reached. It is not the document itself, and it is not legal advice.",
        "",
        "What we are doing: taking your instructions, preparing a draft, and keeping each version. The current draft is the one on the screen. Older versions stay on the file. We note when a final copy is sent. Sending it does not mean it has been signed.",
        "",
        "Risks to have in mind:",
        "- A will or an intestacy can still be challenged, including under the Inheritance (Provision for Family and Dependants) Act 1975.",
        "- Capacity, pressure, and a gift to the person who drafts the will are file points. A tick box is not a doctor’s note.",
        "- A lasting power must be signed in the official order or the Office of the Public Guardian will not register it.",
        "- An ordinary power of attorney ends if you lose capacity.",
        "- Probate papers are not filed from this desk. The firm sends them.",
        "- A nuptial or cohabitation agreement is not automatically binding. An employment settlement needs your own advice if you are the employee.",
        "",
        "Please read the draft, the clause notes, and this summary, and tell us anything that is wrong before a final copy is sent.",
        "",
        "Yours sincerely,",
        "Signed and Sorted",
        "",
        "This email has not been sent. Use Email the summary, or send the PDF yourself. If email is not switched on, nothing leaves this desk.",
    ])
    return {"title": f"Summary of the file — {client}", "body": body}


def will_finder_letter(kind: str, matter: dict, books: dict) -> dict:
    case = books.get("case") or {}
    estate = matter.get("deceased_name") or "the person who died"
    died = matter.get("date_of_death") or "[date of death]"
    address = case.get("address") or "[last address]"
    born = case.get("date_of_birth") or "[date of birth, if known]"
    name = matter.get("client_name") or "[your name]"
    ask = [
        f"We are trying to find a will of {estate}, who died on {died}.",
        f"Last address: {address}.",
        f"Date of birth: {born}.",
        "Please tell us whether you, or a member you can ask, hold an original or a copy, or know who prepared one.",
        "Please do not send the will to us until we have confirmed who is entitled to receive it.",
        "This letter does not authorise you to release the will.",
    ]
    targets = {
        "will_ipw": ("Institute of Professional Willwriters", "enquiries@ipw.org.uk", "Trinity Point, New Road, Halesowen, B63 3HY", "0345 257 2570"),
        "will_sww": ("The Society of Will Writers", "info@willwriters.com", "Chancery House, Whisby Way, Lincoln, LN6 3LQ", "01522 687888"),
        "will_probate": ("HMCTS Probate", "contactprobate@justice.gov.uk", "PO Box 12625, Harlow, CM20 9QF", "0300 303 0648"),
        "will_local": ("The partners", "", "[firm name and address]", ""),
    }
    who, email, postal, phone = targets[kind]
    extra = []
    if kind == "will_probate":
        extra = [
            "Please say whether a will of this person has been deposited with the probate service for safe custody, and whether a grant has already been issued.",
            "A search of wills that have already been proved can also be made at https://www.gov.uk/search-will-probate.",
            "This letter is not a search of every solicitor's office.",
        ]
    if kind == "will_local":
        extra = [
            "Please send one copy of this letter to each solicitor and will writer who may have acted for them near the last address.",
            "Solicitors can be found at https://solicitors.lawsociety.org.uk/.",
            "This desk does not send the letter.",
        ]
    body = "\n".join([
        f"To: {who}",
        *([f"Email: {email}"] if email else []),
        f"Post: {postal}",
        *([f"Telephone: {phone}"] if phone else []),
        "",
        "Dear Sir or Madam,",
        "",
        *ask,
        *([""] + extra if extra else []),
        "",
        "Yours faithfully,",
        name,
    ])
    titles = {
        "will_ipw": "Will search — Institute of Professional Willwriters",
        "will_sww": "Will search — Society of Will Writers",
        "will_probate": "Will search — HMCTS Probate",
        "will_local": "Will search — local firms and will writers",
    }
    return {"title": f"{titles[kind]} — {estate}", "body": body}


def pension_letter(matter: dict, books: dict) -> dict:
    case = books.get("case") or {}
    estate = matter.get("deceased_name") or "the person who died"
    died = matter.get("date_of_death") or "[date of death]"
    address = case.get("address") or "[last address]"
    name = matter.get("client_name") or "[your name]"
    schemes = [ln for ln in books.get("lines") or [] if ln.get("kind") == "pension"]
    named = [f"- {ln.get('name')}" + (f" ({ln.get('holder')})" if ln.get("holder") else "") for ln in schemes]
    body = "\n".join([
        "To: The pension scheme administrator",
        "Send this to the address on the annual statement, or the address given by the Pension Tracing Service (https://www.gov.uk/find-pension-contact-details).",
        "",
        "Dear Sir or Madam,",
        "",
        f"We act in the estate of {estate}, who died on {died}.",
        f"Last address: {address}.",
        "Please tell us, for Inheritance Tax from 6 April 2027:",
        "- the value of any unused pension fund or pension death benefit at the date of death;",
        "- how much of that is for a husband, wife, civil partner or charity, and how much is for anyone else;",
        "- whether any sum is a death-in-service benefit, which is not part of the estate for Inheritance Tax;",
        "- the membership or policy number.",
        "",
        *(named or ["The scheme name, if you have it, should be written at the top before this is sent."]),
        "",
        "A copy of the death certificate can follow. Please reply within 28 days of this request.",
        "This email asks for the figures. It is not a notice to withhold money or to pay HMRC. Those notices will use HMRC's own template.",
        "Nothing in this letter has been sent. The firm sends it.",
        "",
        "Yours faithfully,",
        name,
    ])
    return {"title": f"Pension figures — estate of {estate}", "body": body}
