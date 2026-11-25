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
    }


def clean_saved(done: list) -> dict:
    kept = []
    for item in done or []:
        if item in _IDS and item not in kept:
            kept.append(item)
    return {"done": kept}
