"""What firm staff collect, in order. Probate is a full matter plan. Other documents follow the public steps.

The assistant only restates this checklist and the same draft checks the public site already runs.
It does not invent law, and it does not file anything.
"""
import calendar
from datetime import date

from .guides import SERVICES

ITEM_STATUS = ("needed", "asked", "received", "done", "na")
MATTER_STATUS = ("open", "waiting", "working", "ready", "closed")

_P = [
    ("open", "1. Take instructions", [
        ("client", "The person instructing the firm", "Ask for their full name, address, email and phone, and how they knew the person who died.", "You need a client of record before you take papers.", "client"),
        ("id", "Identity of the client", "Take the usual identification the firm requires before you act.", "This is the firm's own check, not a probate form.", "firm"),
        ("role", "Why they are the right person to instruct you", "Ask whether they are an executor, the person who would apply if there is no will, or someone helping that person.", "An unmarried partner cannot apply if there is no will.", "client"),
    ]),
    ("death", "2. The death", [
        ("certificate", "Death certificate", "Ask for the UK death certificate, an interim certificate from the coroner, or a foreign certificate with an English translation.", "The application needs one of these. Photos are enough to start.", "client"),
        ("identity", "Who died", "Full name, any other names used on accounts, date of birth, date of death, and last permanent address.", "The name must match the will and the bank accounts.", "client"),
        ("home", "Where they lived", "Ask whether they lived permanently in England or Wales, elsewhere in the UK, or outside the UK.", "This affects who can apply and whether the application can be online.", "client"),
        ("marital", "Marital status", "Married, civil partner, widowed, divorced, separated, or never married, at the date of death.", "A husband, wife or civil partner is first in line if there is no will, even if they were separated.", "client"),
    ]),
    ("will", "3. The will and who is applying", [
        ("original", "The original will and any codicils", "Ask for the original, not a photocopy. If it is lost, say so. A lost original may need form PA13 and a postal application.", "The probate service does not accept a photocopy.", "client"),
        ("none", "If there is no will", "Confirm there is no will. The closest relative applies: husband, wife or civil partner, then children aged 18 or over.", "An unmarried partner cannot apply.", "client"),
        ("applicants", "Who will apply", "Up to 4 people can apply. Record the lead applicant's name, address, email and phone.", "You need this before the PA1P or PA1A can be filled in.", "client"),
        ("others", "Executors who are not applying", "Ask if they are holding power reserved, giving up the right with form PA15, appointing someone with form PA11, or cannot apply.", "Only needed when there is a will.", "client"),
    ]),
    ("people", "4. The people", [
        ("beneficiaries", "Who inherits", "List the people named in the will, or the family who inherit if there is no will, with a way to contact each of them.", "You will need them when you account and distribute.", "client"),
        ("left_out", "Anyone who might have expected to inherit", "Ask the client to tell you if a child or someone else close is left out.", "A solicitor decides whether that raises a claim. Do not advise on it from this screen.", "client"),
    ]),
    ("estate", "5. What they owned and owed", [
        ("banks", "Date-of-death values", "The client, or you, writes to each bank or organisation with the death certificate and asks for the value on the date of death.", "Each organisation sets its own limit for releasing money without a grant.", "client"),
        ("property", "Property and joint assets", "For anything owned jointly, record only their share and how it was owned. Joint tenants' assets pass to the other owner and stay out of the probate value.", "Do not put a property on the market until there is a grant.", "client"),
        ("debts", "Debts and the funeral invoice", "List mortgages, loans, cards, bills, and the funeral cost.", "These feed the five figures the probate application asks for.", "client"),
        ("five", "The five application values", "Enter the list in the probate draft. The draft works out the five values. Do not retype them by hand.", "The same figures are used for the tax check.", "firm"),
    ]),
    ("tax", "6. Inheritance tax", [
        ("excepted", "Excepted estate or full details", "Record gifts to a spouse, civil partner or charity, whether a home goes to children or grandchildren, any unused threshold from an earlier spouse, and gifts in the 7 years before death.", "Most estates do not send full details to HMRC. Some still need form IHT400 even when no tax is due.", "client"),
        ("iht400", "If form IHT400 is needed", "Send full details to HMRC within 12 months of the death, start paying any tax, and wait for HMRC's code before applying for the grant.", "The draft tells you if this applies. A solicitor checks it.", "firm"),
        ("deadline", "Tax deadline", "Any tax is due by the end of the sixth month after the death. The date is shown on this matter once the date of death is entered.", "This is the date already used in the public probate helper.", "firm"),
    ]),
    ("grant", "7. Apply for the grant", [
        ("route", "Online or by post", "Use the probate draft. It says whether you can apply online or must use a paper PA form, and which form.", "We never file the application for the client.", "firm"),
        ("papers", "What goes with the application", "The original will, if there is one, goes to the probate service. HMRC only needs copies.", "Keep a scan before the original is posted.", "firm"),
        ("fee", "The fee", "Ask whether the client wants help with fees checked. The draft shows the fee.", "Do not guess a different fee.", "client"),
    ]),
    ("after", "8. After the grant", [
        ("collect", "Collect the assets and pay the debts", "Write to each organisation with the grant. Pay debts and any tax. Keep a record.", "This is the administration, not the application.", "firm"),
        ("protect", "Protect against unknown claims", "Consider a deceased estates notice in The Gazette, and wait at least 6 months from the grant before distributing in full.", "That 6-month wait is about claims under the Inheritance (Provision for Family and Dependants) Act 1975. A solicitor decides.", "firm"),
        ("accounts", "Estate accounts and distribution", "Prepare the accounts, then distribute under the will or the intestacy rules.", "Close the matter only when the accounts are agreed.", "firm"),
    ]),
]


def _item(iid, title, ask, why, who):
    return {"id": iid, "title": title, "ask": ask, "why": why, "who": who}


def probate_checklist():
    return [{"id": sid, "title": title, "items": [_item(*row) for row in rows]} for sid, title, rows in _P]


def guide_checklist(kind: str):
    spec = SERVICES[kind]
    stages = []
    for i, step in enumerate(spec["steps"], 1):
        guidance = [g for g in (step.get("guidance") or []) if g]
        ask = " ".join(guidance[:2]) if guidance else step["title"]
        stages.append({
            "id": step["id"],
            "title": f"{i}. {step['title']}",
            "items": [_item(step["id"], step["title"], ask, "Complete this with the client, or from the papers they send. It is the same step as on the public site.", "client")],
        })
    n = len(stages) + 1
    stages.append({
        "id": "signoff",
        "title": f"{n}. Solicitor sign-off",
        "items": [_item("signoff", "A solicitor checks the draft before anyone signs", "Read the draft and the warnings. Nothing is signed from the website.", "The public service prepares a draft. It is not legal advice until a solicitor has checked it.", "firm")],
    })
    return stages


def checklist(kind: str):
    if kind not in SERVICES:
        raise KeyError(kind)
    if kind == "probate":
        return probate_checklist()
    return guide_checklist(kind)


def client_prepare(kind: str = "probate"):
    """Short list for the public probate page: what the family can gather."""
    out = []
    for stage in checklist(kind):
        items = [{"title": it["title"], "ask": it["ask"]} for it in stage["items"] if it["who"] == "client"]
        if items:
            out.append({"title": stage["title"], "items": items})
    return out


def _parse_iso(value: str) -> date | None:
    try:
        y, m, d = (int(x) for x in (value or "").split("-"))
        return date(y, m, d)
    except (TypeError, ValueError):
        return None


def iht_due(date_of_death: str) -> str | None:
    """End of the sixth month after the death. Matches the public probate helper."""
    dob = _parse_iso(date_of_death)
    if not dob:
        return None
    month = dob.month + 6
    year = dob.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def grant_wait_until(grant_date: str) -> str | None:
    """Six months from the grant, before distributing in full. Day-of-month is clamped."""
    g = _parse_iso(grant_date)
    if not g:
        return None
    month = g.month + 6
    year = g.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(g.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def deadlines(matter: dict) -> list[dict]:
    if matter.get("kind") != "probate":
        return []
    out = []
    due = iht_due(matter.get("date_of_death") or "")
    if due:
        out.append({"label": "Inheritance tax, if any is due", "date": due, "note": "By the end of the sixth month after the death."})
    elif not matter.get("date_of_death"):
        out.append({"label": "Inheritance tax", "date": "", "note": "Enter the date of death and this date will be filled in."})
    wait = grant_wait_until(matter.get("grant_date") or "")
    if wait:
        out.append({"label": "Do not distribute in full before", "date": wait, "note": "At least 6 months from the grant, in case of a claim. A solicitor decides."})
    return out


def flat_items(kind: str):
    return [it for stage in checklist(kind) for it in stage["items"]]


def progress(kind: str, facts: dict) -> dict:
    states = (facts or {}).get("items") or {}
    items = flat_items(kind)
    done = sum(1 for it in items if states.get(it["id"]) in ("done", "na"))
    return {"done": done, "total": len(items)}


def next_item(kind: str, facts: dict):
    states = (facts or {}).get("items") or {}
    for stage in checklist(kind):
        for it in stage["items"]:
            if states.get(it["id"]) not in ("done", "na", "received"):
                return stage, it
    return None, None


def request_letter(matter: dict) -> dict:
    states = (matter.get("facts") or {}).get("items") or {}
    outstanding = []
    for stage in checklist(matter["kind"]):
        for it in stage["items"]:
            if it["who"] == "client" and states.get(it["id"]) not in ("done", "na", "received"):
                outstanding.append(it)
    name = matter.get("client_name") or "there"
    title = matter.get("title") or SERVICES[matter["kind"]]["title"]
    lines = [f"Dear {name},", "", f"Thank you for instructing us on {title}.", "", "Please send the items below. A clear photo or scan is enough unless we have asked for an original.", ""]
    if not outstanding:
        lines += ["We have nothing outstanding from you at the moment. We will write again if that changes.", ""]
    else:
        for i, it in enumerate(outstanding, 1):
            lines += [f"{i}. {it['title']}", it["ask"], ""]
    lines += ["Please reply to this email, or bring the papers in.", "", "This is a request for information. It is not legal advice.", "Signed and Sorted"]
    return {"subject": f"What we still need from you — {title}", "body": "\n".join(lines), "count": len(outstanding)}


def assist(matter: dict, action: str, draft: dict | None) -> dict:
    stage, item = next_item(matter["kind"], matter.get("facts") or {})
    base = {
        "next": None if not item else {"stage": stage["title"], "title": item["title"], "ask": item["ask"], "why": item["why"], "who": item["who"]},
        "progress": progress(matter["kind"], matter.get("facts") or {}),
        "deadlines": deadlines(matter),
        "note": "Staff assistant. It follows this checklist and the draft checks. It is not a solicitor and it does not file anything.",
    }
    if action == "request":
        base["letter"] = request_letter(matter)
    elif action == "check":
        base["check"] = draft or {"missing": [], "issues": [], "detail": "Open the draft first. The checks run on the answers in that draft."}
    return base
