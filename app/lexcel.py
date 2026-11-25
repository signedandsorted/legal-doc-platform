"""Lexcel v6.1 comments for a firm file.

Lexcel is the Law Society's practice-management mark. It accredits a practice,
not this software. The wording below is this desk's own note of what the file
must show. It is not a copy of the standard and a tick does not accredit the firm.

The standard is Lexcel England and Wales v6.1 for legal practices, Law Society,
March 2018. Annual maintenance visits always look at sections 5, 6 and 7.
The assessor uses the Law Society's own case-management checklist.
"""

STANDARD = "https://www.lawsociety.org.uk/-/media/files/accreditations/lexcel/lexcel-v6-1/lexcel-standard-for-legal-practices-in-england-and-wales.pdf"
GUIDANCE = "https://www.lawsociety.org.uk/topics/firm-accreditations/lexcel"
APPLY = "https://www.lawsociety.org.uk/topics/firm-accreditations/lexcel/how-to-apply-for-lexcel-england-and-wales-v6-1"

LINKS = [
    {"title": "Lexcel", "url": GUIDANCE},
    {"title": "How a firm applies (v6.1)", "url": APPLY},
    {"title": "The standard for legal practices (PDF, March 2018)", "url": STANDARD},
]

NOTICE = (
    "Lexcel v6.1 is the Law Society mark for client care, risk and file management. "
    "It is awarded to a practice after an independent assessment, not by this desk. "
    "The requirements must already have been in place for three months before the first visit. "
    "Accreditation lasts three years. Every annual visit looks at risk, client care, and the file."
)

CANNOT = [
    "A tick is the fee earner's note that the point is on the file. It is not the client-care letter, the file review, or the accreditation.",
    "Sections 1 to 4 (strategy, finance, information and people) are firm policies. This screen does not write those policies.",
    "This desk does not give an undertaking, run an anti-money-laundering check, or keep the central complaints record.",
]

# Each desk line says what this file can hold. The requirement line is the firm's job.
ITEMS = [
    {"id": "strategy", "section": "7. File and case management", "clause": "7.1",
     "requirement": "The strategy for the matter is apparent on the file. A complex matter has a plan.",
     "desk": "The Next step is that strategy. If the matter is complex, the plan goes in a file note, not only in someone's head."},
    {"id": "undertakings", "section": "7. File and case management", "clause": "7.2",
     "requirement": "The firm has a written procedure for who may give an undertaking, and for monitoring and discharging it.",
     "desk": "This desk cannot give an undertaking. If the firm gives one, record it in a file note and record when it is discharged."},
    {"id": "trace", "section": "7. File and case management", "clause": "7.3",
     "requirement": "The firm can list open and closed matters, find every file for one client, and trace deeds, wills and other papers. The status is visible to a colleague. Papers are kept in order. Confidentiality is protected.",
     "desk": "The matter list is the open and closed list. The will's location is on Before you act. It is not a deeds register, and it is not a substitute for the firm's confidentiality arrangements."},
    {"id": "progress", "section": "7. File and case management", "clause": "7.4",
     "requirement": "Key facts are on the file. Calls and letters are answered in good time. Cost information continues as the matter goes on. If the person doing the work changes, or the person a client can complain to about service changes, the client is told in writing.",
     "desk": "The person assigned is on Next. A change of person is not told to the client until the firm writes. The bill is not the costs update."},
    {"id": "dates", "section": "5. Risk management", "clause": "5.7",
     "requirement": "Key dates are defined for each type of work, recorded on the file, and kept in a backup as well.",
     "desk": "Dates on this matter (the grant, tax, the six months, and section 27) are the file copy. The firm still needs its own backup diary."},
    {"id": "conflict", "section": "5. Risk management", "clause": "5.8",
     "requirement": "The firm defines a conflict, trains people to see one, and the check is on the file.",
     "desk": "Before you act records the name check. It does not decide whether there is a conflict, and it does not train the staff."},
    {"id": "supervision", "section": "5. Risk management", "clause": "5.9",
     "requirement": "Everyone doing the work, including a temporary person, has a supervisor who is available and who looks at the matter.",
     "desk": "Name the supervisor on the client-care letter. Assigning the matter on this screen is not that letter."},
    {"id": "review", "section": "5. Risk management", "clause": "5.11",
     "requirement": "Someone who did not do the work reviews either the running of the file or the legal content, or both. The review is kept on the file and centrally. Anything found is put right within 28 days and then checked. The supervisor looks at what the reviews show.",
     "desk": "Record the review in a file note, with the date and what was put right. This screen does not carry out the review and it does not keep the central record."},
    {"id": "aml", "section": "5. Risk management", "clause": "5.13",
     "requirement": "The firm has an anti-money-laundering policy, trains people, and screens the people who should be screened.",
     "desk": "Identity and source of funds can be noted on Before you act. This desk does not run the check."},
    {"id": "takeon", "section": "6. Client care", "clause": "6.1",
     "requirement": "Before the firm takes the client on, it has the people and the competence to do the work. It knows how a new enquiry is handled.",
     "desk": "If the work is beyond the person it is assigned to, they tell the supervisor and it is moved. Opening the matter is not that decision."},
    {"id": "letter", "section": "6. Client care", "clause": "6.2",
     "requirement": "Unless another form is more appropriate, write to the client with: what they want; the issues and the options; what you will and will not do; the next steps; how often you will report; the timescale; how it is paid for; whether the cost is worth the outcome; the level of service; what the firm will do and what the client will do; the name and status of the person doing the work; the name and status of the supervisor; and their data-protection rights and the person responsible.",
     "desk": "That letter is the client-care letter. Draft it and keep the copy on the file. None of the boxes on this desk is that letter."},
    {"id": "costs", "section": "6. Client care", "clause": "6.4",
     "requirement": "At the start, give a costs estimate that includes the expected payments to other people and says what extra costs can arise. Update it before the estimate is exceeded.",
     "desk": "Time and bills can be recorded on Bill. The estimate itself is still a letter to the client."},
    {"id": "complaints", "section": "6. Client care", "clause": "6.5",
     "requirement": "The client is told how to complain. Once a complaint is made, they are told in writing how it will be handled and when they will have a reply. Complaints are recorded centrally, the cause is looked at, and the procedure is corrected if it failed.",
     "desk": "Put the complaints wording in the client-care letter. This desk does not keep the central complaints record."},
]

_IDS = {item["id"] for item in ITEMS}

QUOTE_FIELDS = (
    "objectives", "next_steps", "will_not", "timescale", "funding",
    "fee", "disbursements", "extras",
    "fee_earner", "fee_earner_status", "supervisor", "supervisor_status", "data_officer",
)


def _blank_quote() -> dict:
    return {key: "" for key in QUOTE_FIELDS}


def _quote(raw, previous) -> dict:
    base = _blank_quote()
    base.update({key: str((previous or {}).get(key) or "")[:400] for key in QUOTE_FIELDS})
    if isinstance(raw, dict):
        for key in QUOTE_FIELDS:
            if key in raw:
                base[key] = str(raw.get(key) or "")[:400]
    return base


def for_matter(saved: dict | None) -> dict:
    saved = saved or {}
    done = [item for item in (saved.get("done") or []) if item in _IDS]
    items = [{**item, "done": item["id"] in done} for item in ITEMS]
    return {
        "title": "Lexcel v6.1",
        "notice": NOTICE,
        "cannot": CANNOT,
        "links": LINKS,
        "items": items,
        "open": sum(1 for item in items if not item["done"]),
        "quote": _quote(None, saved.get("quote")),
        "conflict_q": str(saved.get("conflict_q") or "")[:200],
    }


def clean_saved(done, quote, previous, conflict_q) -> dict:
    previous = previous or {}
    if done is None:
        kept = [item for item in (previous.get("done") or []) if item in _IDS]
    else:
        kept = []
        for item in done or []:
            if item in _IDS and item not in kept:
                kept.append(item)
    q = previous.get("conflict_q") or ""
    if conflict_q is not None:
        q = str(conflict_q)[:200]
    return {"done": kept, "quote": _quote(quote, previous.get("quote")), "conflict_q": q}


def _line(label: str, value: str) -> str:
    return f"{label}: {value.strip() or '[not yet entered on this file]'}"


def letter(kind: str, matter: dict, matches: list | None = None) -> dict | None:
    """Drafts for the file. Nothing is sent, and none of them accredits the firm."""
    saved = ((matter.get("facts") or {}).get("lexcel") or {})
    quote = _quote(None, saved.get("quote"))
    client = matter.get("client_name") or "the client"
    work = matter.get("title") or matter.get("kind") or "this matter"
    earner = quote["fee_earner"] or "[fee earner]"
    status = quote["fee_earner_status"] or "[status]"
    supervisor = quote["supervisor"] or "[supervisor]"
    supervisor_status = quote["supervisor_status"] or "[status]"
    if kind == "lex_care":
        body = "\n".join([
            f"Dear {client},", "",
            f"Thank you for asking us to act on {work}.",
            "This letter sets out how we will do that. It is the client-care letter for this file (Lexcel 6.2). It is not a guarantee of an outcome.",
            "",
            _line("What you want", quote["objectives"]),
            _line("What we will do next", quote["next_steps"]),
            _line("What we will not do", quote["will_not"]),
            _line("How long we expect it to take", quote["timescale"]),
            _line("How it is paid for", quote["funding"]),
            _line("Our fee", quote["fee"]),
            _line("Payments to other people", quote["disbursements"]),
            _line("Costs that can still arise", quote["extras"]),
            _line("The person doing the work", f"{earner}, {status}"),
            _line("The person supervising it", f"{supervisor}, {supervisor_status}"),
            _line("Data protection", quote["data_officer"] or "The firm’s data-protection contact"),
            "",
            "You can complain to the supervisor named above. We will tell you how a complaint will be handled and when you will have a reply. You can also ask for the firm’s complaints procedure.",
            "If the person doing the work changes, or the person you should speak to about the service changes, we will write to you.",
            "Please tell us if anything in this letter is wrong before we start.",
            "",
            "Yours sincerely,",
            earner,
        ])
        return {"title": f"Client-care letter — {client}", "body": body}
    if kind == "lex_quote":
        body = "\n".join([
            f"Dear {client},", "",
            f"This is the costs estimate for {work} (Lexcel 6.4). It is an estimate, not a final bill.",
            "",
            _line("Our fee", quote["fee"]),
            _line("Payments to other people, so far as we can see them now", quote["disbursements"]),
            _line("Further costs that can arise", quote["extras"]),
            _line("How it is paid for", quote["funding"]),
            "",
            "If the work is going to cost more than this estimate, we will write to you before that extra work is done.",
            "Please say if you want us to stop, or to limit what we do, so that the cost stays inside a figure you choose.",
            "",
            "Yours sincerely,",
            earner,
        ])
        return {"title": f"Costs estimate — {client}", "body": body}
    if kind == "lex_progress":
        body = "\n".join([
            f"Dear {client},", "",
            f"This is a progress report on {work}.",
            _line("Where it stands", quote["next_steps"]),
            _line("The timescale we are working to", quote["timescale"]),
            "The costs estimate already given still applies unless this letter says it does not.",
            "Nothing has been filed or paid from this desk.",
            "",
            "Yours sincerely,",
            earner,
        ])
        return {"title": f"Progress report — {client}", "body": body}
    if kind == "lex_change":
        body = "\n".join([
            f"Dear {client},", "",
            f"The person dealing with {work} has changed. Lexcel 7.4 asks us to tell you in writing.",
            "",
            _line("The person now doing the work", f"{earner}, {status}"),
            _line("The person supervising it, and the person to contact about the service", f"{supervisor}, {supervisor_status}"),
            "The work itself has not changed because of this letter.",
            "",
            "Yours sincerely,",
            supervisor,
        ])
        return {"title": f"Change of person — {client}", "body": body}
    if kind == "lex_complaint":
        body = "\n".join([
            f"Dear {client},", "",
            "Thank you for telling us you are unhappy with the service. This letter says how we will handle that. It is not a decision on the complaint.",
            "",
            f"The person looking at it is {supervisor}, {supervisor_status}. They did not have to be the person who did the work.",
            "We will write again with a first reply, or with the outcome, within the time in the firm’s complaints procedure. If that date is not already in the procedure, put it in this letter before it is sent.",
            "The complaint is also recorded on the firm’s central list, not only on this file. This desk does not keep that central list.",
            "",
            "Yours sincerely,",
            supervisor,
        ])
        return {"title": f"Complaint acknowledgement — {client}", "body": body}
    if kind == "lex_review":
        body = "\n".join([
            f"File review note — {work}",
            f"Client: {client}",
            "",
            "Lexcel 5.11. Someone who did not do the work reviews the running of the file, or the legal content, or both.",
            _line("Reviewer", supervisor),
            "Date of review: [date]",
            "What was looked at: [the file / the advice]",
            "What was found: [nothing / set it out]",
            "What will be put right, and by when: [within 28 days]",
            "Checked after it was put right, and by whom: [name and date]",
            "",
            "A copy of this note stays on the file. The same result is recorded on the firm’s central review record. This desk is not that central record.",
        ])
        return {"title": f"File review — {client}", "body": body}
    if kind == "lex_undertaking":
        body = "\n".join([
            f"Undertaking record — {work}",
            "",
            "Lexcel 7.2. This desk cannot give an undertaking. This note records one the firm has chosen to give.",
            "Who is allowed to give it, under the firm’s procedure: [name]",
            "The exact words of the undertaking: [words]",
            "Who it was given to: [name]",
            "Date it was given: [date]",
            "What has to happen before it is discharged: [steps]",
            "Date it was discharged: [date, or still open]",
            "",
            "Until it is discharged it stays on the file and on the firm’s own list of undertakings.",
        ])
        return {"title": f"Undertaking — {client}", "body": body}
    if kind == "lex_conflict":
        looked = saved.get("conflict_q") or client
        lines = [f"- {item.get('title') or 'Untitled'} · {item.get('client_name') or ''} · {item.get('deceased_name') or ''}".rstrip(" ·") for item in (matches or [])]
        body = "\n".join([
            f"Conflict search — {work}",
            f"Client: {client}",
            "",
            "Lexcel 5.8. This searches the matters already on this desk. It is not a search of every firm the client has used, and it is not an identity check.",
            f"Names searched: {looked}",
            "",
            *(lines or ["No other matter on this desk uses these names."]),
            "",
            "Decision: [no conflict seen / we cannot act / we can act, and why]",
            "Person who decided: [name]",
            "Date: [date]",
        ])
        return {"title": f"Conflict search — {client}", "body": body}
    return None
