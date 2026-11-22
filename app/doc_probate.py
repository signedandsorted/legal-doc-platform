"""Probate plan: online or post, forms, the 5 estate values, an Inheritance Tax estimate.
Estimates only. DRAFT: needs lawyer review before it goes live."""
import calendar
from datetime import date

from .common import DRAFT_NOTICE, issue, money, num, person
from .guide_probate import (EXCEPTED_EXEMPT_LIMIT, EXCEPTED_FOREIGN_DOM_LIMIT, EXCEPTED_TNRB_LIMIT, EXTRA_COPY_FEE, FULL_DETAIL_TRIGGERS, NRB, PROBATE,
                            PROBATE_FEE, PROBATE_FEE_FREE_UNDER, RNRB, RNRB_TAPER_FROM)

JOINT_TENANTS = "Joint tenants"


def values(a: dict) -> dict:
    e, t = a.get("estate") or {}, a.get("tax") or {}
    assets, debts = e.get("assets") or [], e.get("debts") or []
    gifts = num(t.get("gifts_7_years"))
    funeral = num(e.get("funeral_costs"))
    total_assets = sum(num(x.get("value")) for x in assets)
    all_debts = sum(num(x.get("value")) for x in debts)
    sole_debts = sum(num(x.get("value")) for x in debts if x.get("joint") != "Yes")
    gross_iht = total_assets + gifts
    net_iht = gross_iht - all_debts - funeral
    exempt = num(t.get("to_spouse")) + num(t.get("to_charity"))
    net_qualifying = max(0.0, net_iht - exempt)
    excluded = sum(num(x.get("value")) for x in assets if str(x.get("ownership", "")).startswith(JOINT_TENANTS) or x.get("abroad") == "Yes")
    gross_probate = max(0.0, total_assets - excluded)
    net_probate = max(0.0, gross_probate - sole_debts - funeral)
    return {"gross_iht": gross_iht, "net_iht": net_iht, "net_qualifying": net_qualifying, "gross_probate": gross_probate, "net_probate": net_probate,
            "abroad": sum(num(x.get("value")) for x in assets if x.get("abroad") == "Yes"), "gifts": gifts}


def iht(a: dict, v: dict) -> dict:
    t = a.get("tax") or {}
    tnrb_pct = min(100.0, num(t.get("unused_nrb_percent") or 100)) if t.get("earlier_spouse_died") == "Yes" else 0.0
    nrb = NRB * (1 + tnrb_pct / 100)
    rnrb = 0.0
    if t.get("home_to_descendants") == "Yes":
        cap = RNRB * (2 if t.get("earlier_spouse_died") == "Yes" else 1)  # assumes the earlier spouse's RNRB was unused (IHT436): solicitor to confirm
        cap = max(0.0, cap - max(0.0, v["net_iht"] - RNRB_TAPER_FROM) / 2)
        rnrb = min(cap, num(t.get("home_value_to_descendants")))
    threshold = nrb + rnrb
    taxable = max(0.0, v["net_qualifying"] - threshold)
    charity = num(t.get("to_charity"))
    baseline = max(0.0, v["net_iht"] - num(t.get("to_spouse")) - nrb)
    rate = 0.36 if charity and baseline and charity >= 0.1 * baseline else 0.40
    return {"nrb": nrb, "rnrb": rnrb, "threshold": threshold, "taxable": taxable, "rate": rate, "tax": taxable * rate, "tnrb_pct": tnrb_pct}


def estate_type(a: dict, v: dict, tax: dict) -> tuple[bool, list[str]]:
    """Returns (excepted, reasons). Rules for deaths on or after 1 January 2022 (GOV.UK 'Check if you need to send full details')."""
    t, d = a.get("tax") or {}, a.get("deceased") or {}
    reasons = [label for k, label in FULL_DETAIL_TRIGGERS if t.get(k) is True]
    if v["gifts"] > 250_000:
        reasons.append("They gave away more than £250,000 in the 7 years before they died")
    if v["gross_iht"] > EXCEPTED_EXEMPT_LIMIT:
        reasons.append("The estate is worth more than £3 million")
    if v["abroad"] > 100_000:
        reasons.append("They had foreign assets worth more than £100,000")
    if tax["tax"] > 0:
        reasons.append("Inheritance Tax looks likely to be due")
    if reasons:
        return False, reasons
    if d.get("domicile") == "No, outside the UK":
        return (v["gross_iht"] - v["abroad"] <= EXCEPTED_FOREIGN_DOM_LIMIT), ([] if v["gross_iht"] - v["abroad"] <= EXCEPTED_FOREIGN_DOM_LIMIT else ["They lived outside the UK and their UK assets are over £150,000"])
    if v["gross_iht"] <= NRB:
        return True, []
    if tax["tnrb_pct"] >= 100 and v["gross_iht"] <= EXCEPTED_TNRB_LIMIT:
        return True, []
    if v["net_qualifying"] <= 0 and v["gross_iht"] < EXCEPTED_EXEMPT_LIMIT:
        return True, []
    return False, ["The estate is over the tax-free threshold, so full details (and any claims for extra allowances) go to HMRC even if no tax is due"]


def plan(a: dict) -> dict:
    d, w, t = a.get("deceased") or {}, a.get("will") or {}, a.get("tax") or {}
    v = values(a)
    tax = iht(a, v)
    excepted, reasons = estate_type(a, v, tax)
    has_will = str(w.get("has_will", "")).startswith("Yes")
    lost = w.get("has_will") == "Yes, but the original is lost"
    role = w.get("applicant_role", "")
    post_reasons, blockers, forms, iss = [], [], [], []
    if w.get("has_will") == "Not sure":
        blockers.append("Find out whether there is a will first: search their papers, ask their solicitor or bank, and check the probate service's will storage.")
    if lost:
        post_reasons.append("The original will is lost, so you need form PA13 and must apply by post.")
        forms.append(("PA13", "Lost will: apply for probate using a copy"))
    if d.get("domicile") and d["domicile"] != "Yes":
        post_reasons.append("They did not live permanently in England or Wales. The online service is for people who did; a solicitor should confirm where to apply.")
    if role == "Unmarried partner":
        blockers.append("An unmarried partner cannot apply. The closest relative must apply, or a solicitor can advise.")
    if role.startswith("Someone else"):
        post_reasons.append("You are not an executor or the closest relative, so you will need a power of attorney form (PA11 with a will, PA12 without) or legal advice, and must apply by post.")
        forms.append(("PA11" if has_will else "PA12", "Appoint someone to apply on the entitled person's behalf"))
    if w.get("applicants") == "More than 4":
        iss.append(issue("warning", "Only up to 4 people can be named on the application. Agree who will apply."))
    if has_will and role and not role.startswith("Executor") and not role.startswith("Someone else"):
        iss.append(issue("warning", "With a will, the executors named in it normally apply. If no executor can act, another entitled person (for example a beneficiary) may apply. A solicitor will check."))
    if not has_will and w.get("has_will") == "No" and role == "Child aged 18 or over" and d.get("marital_status") == "Married or in a civil partnership" and w.get("surviving_spouse_applying") != "They are giving up their right (form PA16)":
        iss.append(issue("warning", "With no will, a surviving husband, wife or civil partner is first in line. A child can apply if they give up the right on form PA16."))
    oe = w.get("other_executors", "")
    if oe.startswith("Giving up"):
        forms.append(("PA15", "Renunciation: an executor gives up the right to apply"))
    if oe.startswith("Want to appoint"):
        forms.append(("PA11", "Appoint someone to apply for an executor"))
    if oe.startswith("Cannot apply"):
        forms.append(("PA14", "Medical certificate for an executor who cannot apply (must be done before anyone applies)"))
    if oe.startswith("Holding"):
        iss.append(issue("info", "The executor holding power reserved must tell the applicant in writing."))
    if w.get("surviving_spouse_applying", "").startswith("They are giving up"):
        forms.append(("PA16", "Spouse or civil partner gives up the right to administer"))
    if d.get("death_certificate") in ("Interim certificate from the coroner", "Certificate from outside England or Wales"):
        iss.append(issue("info", "Send a copy of the death certificate with the application (and a translation if it is not in English)."))
    if not excepted:
        forms.insert(0, ("IHT400", "Inheritance Tax account: send to HMRC within 12 months and before applying for probate"))
        if tax["tnrb_pct"] > 0:
            forms.insert(1, ("IHT402", "Claim to transfer the unused nil rate band"))
        if tax["rnrb"] > 0:
            forms.insert(1, ("IHT435", "Claim the residence nil rate band"))
            if t.get("earlier_spouse_died") == "Yes":
                forms.insert(2, ("IHT436", "Claim to transfer the unused residence nil rate band"))
    fee = PROBATE_FEE if v["net_probate"] > PROBATE_FEE_FREE_UNDER else 0
    if fee and w.get("help_with_fees") in ("Yes", "Not sure"):
        forms.append(("EX160", "Help with fees (or apply online for help with fees)"))
    online = not post_reasons and not blockers
    app_form = ("PA1P" if has_will else "PA1A")
    route = "Blocked: sort out the points below first" if blockers else ("Online on GOV.UK" if online else f"By post on form {app_form}")
    if not blockers:
        forms.insert(0, (app_form, "Paper probate application" + ("" if not online else " (only if you cannot apply online)")))
    return {"values": v, "tax": tax, "excepted": excepted, "estate_reasons": reasons, "route": route, "online": online, "post_reasons": post_reasons,
            "blockers": blockers, "forms": forms, "fee": fee, "issues": iss, "grant": "grant of probate" if has_will else "letters of administration"}


def probate_issues(a: dict) -> list[dict]:
    p = plan(a)
    return [issue("error", b) for b in p["blockers"]] + p["issues"] + ([issue("warning", "Inheritance Tax looks likely to be due. You normally pay some before probate is granted, and by the end of the sixth month after the death to avoid interest.")] if p["tax"]["tax"] > 0 else [])


def _deadline(dod: str) -> str:
    try:
        d = date.fromisoformat(dod)
    except ValueError:
        return ""
    y, m = d.year + (d.month + 6 - 1) // 12, (d.month + 6 - 1) % 12 + 1
    return date(y, m, calendar.monthrange(y, m)[1]).strftime("%d %B %Y")


def _plain_account(e: dict, v: dict, tax: dict, p: dict) -> list[str]:
    """A lay-person account. It does not decide who inherits."""
    debts = sum(num(x.get("value")) for x in (e.get("debts") or []) if x.get("joint") != "Yes") + num(e.get("funeral_costs"))
    lines = [
        f"The grant covers {money(v['gross_probate'])}.",
        f"Debts and the funeral in this account come to {money(debts)}.",
        f"What is left for the grant is {money(v['net_probate'])}.",
        f"The tax estimate is {money(tax['tax'])}. " + ("No full tax form is needed on these answers." if p["excepted"] else "These answers need form IHT400, posted to HMRC, before you apply for the grant."),
    ]
    passed = [x for x in (e.get("assets") or []) if str(x.get("ownership", "")).startswith("Joint tenants") or x.get("abroad") == "Yes"]
    if passed:
        lines.append("These are not in the account. Jointly owned things go to the other owner. Things abroad are dealt with separately: " + "; ".join(f"{x.get('description')} {money(x.get('value'))}" for x in passed) + ".")
    else:
        lines.append("Nothing you entered passes automatically to another owner.")
    return lines


def _people(a: dict) -> list[str]:
    names = [x.get("full_name") for x in ((a.get("account") or {}).get("people") or []) if x.get("full_name")]
    if not names:
        return ["You have not named anyone to keep informed. The will, or the law if there is no will, decides who inherits. A solicitor checks that."]
    return ["People to keep informed: " + ", ".join(names) + ". This is not a decision about who inherits. The will, or the law if there is no will, decides the shares."]


def client_steps(a: dict, p: dict) -> list[str]:
    """What the client does next. Asking the firm to file is a request, not a filing."""
    choice = (a.get("account") or {}).get("who_files") or ""
    steps = ["Read the estate account in your plan. It uses the values you entered. A solicitor checks it before anyone is paid."]
    if not p["excepted"]:
        steps.append("Full tax details are needed. Form IHT400 is printed, signed and posted to HMRC. Wait for their code. This website cannot send that form.")
    if choice.startswith("I want the firm"):
        steps.append("You have asked the firm to file the grant. This is a request. Nothing is filed until a solicitor accepts the matter and sends it. This website cannot sign in to HMCTS.")
        if p["blockers"]:
            steps.append("The plan is blocked, so it cannot be filed until those points are sorted out.")
        elif p["online"]:
            steps.append("If the firm accepts the matter, a solicitor files the grant in MyHMCTS and will ask you for the original will. You do not apply on GOV.UK yourself.")
        else:
            steps.append("The online service will not take this application. If the firm accepts the matter, a solicitor files it by post on the form named above.")
    else:
        if p["online"]:
            steps.append("You chose to file the grant yourself. Apply on GOV.UK and send the original will. This website cannot send the application.")
        elif not p["blockers"]:
            steps.append("You chose to file the grant yourself. The online service will not take this one, so apply by post on the form named above and send the original will.")
        else:
            steps.append("Sort out the blocked points before anyone applies.")
    steps.append("When the grant arrives, collect each account and pay the debts and the funeral. Keep a note of money in and money out.")
    steps.append("Wait at least 6 months from the grant before paying everyone in full. Share what is left as the will says, or as the law says if there is no will.")
    return steps


def build_probate(_, a: dict, uploads: list | None = None) -> dict:
    d, w = a.get("deceased") or {}, a.get("will") or {}
    p = plan(a)
    v, tax = p["values"], p["tax"]
    e = a.get("estate") or {}
    sec = [
        {"heading": "Your route", "paragraphs": [f"How to apply: {p['route']}.", f"What you will get: a {p['grant']}."] + p["post_reasons"] + p["blockers"]},
        {"heading": "Forms you need", "paragraphs": [f"{f}: {why}" for f, why in p["forms"]] or ["None beyond the online application."]},
        {"heading": "The 5 values for the probate application", "paragraphs": [
            f"Gross estate value for Inheritance Tax: {money(v['gross_iht'])}", f"Net estate value for Inheritance Tax: {money(v['net_iht'])}",
            f"Net qualifying estate value for Inheritance Tax: {money(v['net_qualifying'])}", f"Gross value for probate: {money(v['gross_probate'])}",
            f"Net value for probate: {money(v['net_probate'])}",
            "Probate values leave out joint-tenancy assets passing to the surviving owner, gifts, assets abroad and trust assets, and jointly owed debts."]},
        {"heading": "Inheritance Tax estimate", "paragraphs": [
            f"Estate type: {'excepted estate (no full details to HMRC)' if p['excepted'] else 'full details needed on form IHT400'}."] + [f"Reason: {r}" for r in p["estate_reasons"]] + [
            f"Tax-free threshold used: {money(tax['threshold'])} (nil rate band {money(tax['nrb'])}" + (f", residence nil rate band {money(tax['rnrb'])}" if tax['rnrb'] else "") + ").",
            f"Estimated tax: {money(tax['tax'])}" + (f" at {int(tax['rate'] * 100)}%" if tax["tax"] else "") + ".",
            ("Pay by " + _deadline(d.get("date_of_death", "")) + " to avoid interest." if tax["tax"] and _deadline(d.get("date_of_death", "")) else "This is an estimate, not tax advice. A solicitor will check it.")]},
        {"heading": "Fee", "paragraphs": [f"Application fee: {money(p['fee'])}" + (" (estate over £5,000)" if p["fee"] else " (estate £5,000 or less)") + f". Extra copies of the grant: £{EXTRA_COPY_FEE} each when you apply."]},
        {"heading": "Your estate account", "paragraphs": _plain_account(e, v, tax, p) + _people(a)},
        {"heading": "Who files the grant", "paragraphs": [
            (a.get("account") or {}).get("who_files") or "Not chosen yet.",
            "Asking the firm to file does not send the application. A solicitor files it in MyHMCTS, or by post if the online service will not take it.",
        ]},
        {"heading": "The person who died", "paragraphs": [person(d), "Date of death: " + d.get("date_of_death", ""), "Lived permanently in England or Wales: " + d.get("domicile", ""), "Marital status: " + d.get("marital_status", "")]},
        {"heading": "Will and applicant", "paragraphs": ["Will: " + w.get("has_will", ""), "Applicant: " + person(w.get("applicant") or {}) + (f" ({w.get('applicant_role')})" if w.get("applicant_role") else ""), "Number applying: " + w.get("applicants", "")]},
        {"heading": "Assets", "paragraphs": [f"{x.get('description')}: {money(x.get('value'))}" + (f" ({x['ownership']})" if x.get("ownership") else "") + (" (abroad)" if x.get("abroad") == "Yes" else "") for x in e.get("assets") or []] or ["None listed yet"]},
        {"heading": "Debts and funeral costs", "paragraphs": [f"{x.get('description')}: {money(x.get('value'))}" + (" (joint)" if x.get("joint") == "Yes" else "") for x in e.get("debts") or []] + ([f"Funeral: {money(e['funeral_costs'])}"] if e.get("funeral_costs") else []) or ["None listed yet"]},
        {"heading": "Checklist", "paragraphs": ["Original will and any codicils" if str(w.get("has_will", "")).startswith("Yes") else "Confirm there is no will", "Death certificate", "Date-of-death valuations from each bank and organisation", "Lead applicant's email and mobile, and the same for every other applicant (they sign the legal declaration online)"]},
    ]
    if uploads:
        sec.append({"heading": "Documents you uploaded", "paragraphs": [f"{u['filename']} ({u['kind']})" for u in uploads]})
    return {"title": "Probate plan: " + d.get("full_name", ""), "notice": "Prepared " + date.today().strftime("%d %B %Y") + ". " + DRAFT_NOTICE + " Figures are estimates to guide you.",
            "sections": sec, "next_steps": client_steps(a, p), "sources": [x for st in PROBATE["steps"] for x in st.get("sources", [])] + [{"title": "GOV.UK: Probate fees", "url": "https://www.gov.uk/applying-for-probate/fees"}]}
