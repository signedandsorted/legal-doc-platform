"""Ordinary and specific power of attorney drafts.

The general power follows the statutory form in Schedule 1 to the Powers of Attorney
Act 1971, which section 10 also allows 'in a form to the like effect but expressed to
be made under this Act'. The specific power is a limited deed, not a statutory form,
and is flagged for solicitor review. DRAFT: not legal advice; do not sign until reviewed.
"""
from datetime import date

from .common import DRAFT_NOTICE, age_on, issue, person
from .guides import SERVICES

NOT_LEGAL_ADVICE = (
    "This is not legal advice. It is a draft for solicitor review and must not be signed or used until a solicitor has approved it."
)

# Powers of Attorney Act 1971, Schedule 1, as published on legislation.gov.uk.
# The official text uses '19' for the year and 'In Witness etc.'. Section 10 allows
# a form to the like effect expressed to be made under the Act; the year and deed
# attestation below are filled for a current deed, and are flagged for review.
SCH1_BLANK = (
    "This General Power of Attorney is made this day of 19 by AB of "
    "I appoint CD of [or CD of and EF of jointly or jointly and severally] "
    "to be my attorney[s] in accordance with section 10 of the Powers of Attorney Act 1971. "
    "In Witness etc."
)

CAPACITY_NOTE = (
    "This is an ordinary power of attorney, not a lasting power of attorney. "
    "HM Land Registry Practice Guide 9 states that the death, bankruptcy or mental incapacity "
    "of the donor will automatically revoke the power, and that the donor may also revoke it at any time."
)

DEED_NOTE = (
    "The Powers of Attorney Act 1971, section 1, requires an instrument creating a power of attorney "
    "to be executed as a deed by the donor. The Law of Property (Miscellaneous Provisions) Act 1989, "
    "section 1, requires a deed to be signed by the donor in the presence of a witness who attests the signature."
)


def _attorneys(a: dict) -> list:
    return (a.get("attorneys") or {}).get("attorneys") or []


def _type(a: dict) -> str:
    return (a.get("type") or {}).get("poa_type") or ""


def _is_general(a: dict) -> bool:
    return _type(a).startswith("General")


def _is_specific(a: dict) -> bool:
    return _type(a).startswith("Specific")


def _how(a: dict) -> str:
    return (a.get("attorneys") or {}).get("how_they_act") or ""


def poa_issues(a: dict) -> list[dict]:
    out = []
    donor = a.get("donor") or {}
    att = _attorneys(a)
    if not (a.get("type") or {}).get("understood_capacity"):
        out.append(issue("error", "Please confirm that you understand this power stops if you lose mental capacity, and that it is not a substitute for a lasting power of attorney."))
    if donor.get("date_of_birth") and (age_on(donor["date_of_birth"]) or 0) < 18:
        out.append(issue("error", "You must be 18 or over to make this power of attorney."))
    for p in att:
        age = age_on(p.get("date_of_birth", "")) if p.get("date_of_birth") else None
        if age is not None and age < 18:
            out.append(issue("error", f"Attorney {p.get('full_name')} is under 18."))
    if len(att) > 1 and _how(a) == "Only one attorney":
        out.append(issue("error", "You have more than one attorney, so choose whether they act jointly or jointly and severally."))
    if len(att) == 1 and _how(a) in ("Jointly", "Jointly and severally"):
        out.append(issue("warning", "You have one attorney, so a joint or jointly and severally choice is not needed."))
    if _is_specific(a) and not ((a.get("authority") or {}).get("task") or "").strip():
        out.append(issue("error", "Describe the exact task this specific power is limited to."))
    if _is_general(a) and ((a.get("authority") or {}).get("task") or "").strip():
        out.append(issue("warning", "You chose a general power, so the statutory form does not include a limited task. A solicitor will ignore the task box or discuss changing this to a specific power."))
    end_wish = (a.get("authority") or {}).get("end_wish") or ""
    if end_wish.startswith("I would like"):
        out.append(issue("warning", "An end date or 'ends when the task is finished' clause is not part of the statutory Schedule 1 form. A solicitor must review that wording before you sign."))
    if _is_specific(a):
        out.append(issue("warning", "A specific (limited) power is not a statutory form. A solicitor must review it, especially if it will be used for land or registered title (HM Land Registry Practice Guide 9)."))
    out.append(issue("info", "This draft is not legal advice and is not a substitute for a lasting power of attorney."))
    return out


def _appoint_line(att: list, how: str) -> str:
    if not att:
        return "I appoint [name of attorney] of [address] to be my attorney in accordance with section 10 of the Powers of Attorney Act 1971."
    if len(att) == 1:
        return f"I appoint {person(att[0])} to be my attorney in accordance with section 10 of the Powers of Attorney Act 1971."
    people = " and ".join(person(p) for p in att)
    if how == "Jointly":
        return f"I appoint {people} jointly to be my attorneys in accordance with section 10 of the Powers of Attorney Act 1971."
    return f"I appoint {people} jointly and severally to be my attorneys in accordance with section 10 of the Powers of Attorney Act 1971."


def _end_wish_paragraph(a: dict) -> str | None:
    auth = a.get("authority") or {}
    wish = auth.get("end_wish") or ""
    if wish.startswith("I would like it to end on a date") and auth.get("end_date"):
        return (
            f"[For solicitor review — not in the statutory Schedule 1 form.] "
            f"The donor has asked that this power end on {auth['end_date']}."
        )
    if wish.startswith("I would like it to end when the specific task"):
        return (
            "[For solicitor review — not in the statutory Schedule 1 form.] "
            "The donor has asked that this power end when the specific task has been completed."
        )
    return None


def _attestation(donor_name: str) -> list[str]:
    return [
        DEED_NOTE,
        f"SIGNED AS A DEED by {donor_name or 'the donor'} in the presence of:",
        "Donor signature: ______________________   Date: ____________",
        "Witness signature: ______________________",
        "Witness full name, address and occupation: ______________________________________________",
    ]


def build_poa(_, a: dict, uploads: list | None = None) -> dict:
    s = SERVICES["poa_ordinary"]
    donor = a.get("donor") or {}
    att = _attorneys(a)
    today = date.today().strftime("%d %B %Y")
    donor_line = person(donor) or "the donor"
    sections = []
    sections.append({
        "heading": "Important notice",
        "paragraphs": [
            DRAFT_NOTICE + " " + NOT_LEGAL_ADVICE,
            CAPACITY_NOTE,
            "Unlike a lasting power of attorney, this document is not registered with the Office of the Public Guardian and can be used as soon as it has been validly executed as a deed. An LPA must be registered before it can be used, which OPG guidance says takes 8 to 10 weeks if there are no mistakes.",
        ],
    })
    if _is_general(a):
        sections.append({
            "heading": "Statutory form (Powers of Attorney Act 1971, Schedule 1)",
            "paragraphs": [
                "Section 10 of the Act uses this form, or a form to the like effect but expressed to be made under the Act. The official text on legislation.gov.uk is:",
                SCH1_BLANK,
            ],
        })
        sections.append({
            "heading": "General power of attorney — draft deed",
            "paragraphs": [
                f"This General Power of Attorney is made this {today} by {donor_line}.",
                _appoint_line(att, _how(a)),
                "This power of attorney is made under the Powers of Attorney Act 1971 and is executed as a deed.",
                "Subject to section 10(2) of that Act, this power is intended to operate as a general power of attorney in a form to the like effect as the form set out in Schedule 1 to that Act.",
            ] + ([_end_wish_paragraph(a)] if _end_wish_paragraph(a) else []),
        })
    else:
        task = ((a.get("authority") or {}).get("task") or "").strip() or "[describe the exact task]"
        if len(att) == 1:
            appoint = f"I appoint {person(att[0]) if att else '[name of attorney] of [address]'} to be my attorney for the following limited purpose only:"
        else:
            people = " and ".join(person(p) for p in att) if att else "[names of attorneys]"
            how = "jointly" if _how(a) == "Jointly" else "jointly and severally"
            appoint = f"I appoint {people} {how} to be my attorneys for the following limited purpose only:"
        sections.append({
            "heading": "Specific (limited) power of attorney — draft deed",
            "paragraphs": [
                "This is not the statutory general form in Schedule 1 to the Powers of Attorney Act 1971. Practice Guide 9 says a donor may use any form of wording giving limited powers, for example in connection with a particular transaction, but must execute the power as a deed. A solicitor must review this draft.",
                f"This Specific Power of Attorney is made this {today} by {donor_line}.",
                appoint,
                task,
                "The authority given by this deed is limited to that purpose. It is not a general power of attorney under section 10 of the Powers of Attorney Act 1971.",
                "This power of attorney is executed as a deed.",
            ] + ([_end_wish_paragraph(a)] if _end_wish_paragraph(a) else []),
        })
    sections.append({"heading": "Execution as a deed", "paragraphs": _attestation(donor.get("full_name") or "the donor")})
    sections.append({
        "heading": "When this power can be used, and when it ends",
        "paragraphs": [
            "It can be used as soon as it has been signed and witnessed as a deed. It does not need to be registered with the Office of the Public Guardian.",
            CAPACITY_NOTE,
        ],
    })
    if att:
        sections.append({
            "heading": "People named in this draft",
            "paragraphs": [f"Donor: {person(donor)}"] + [f"Attorney: {person(p)}" for p in att],
        })
    if uploads:
        sections.append({"heading": "Documents you uploaded", "paragraphs": [f"{u['filename']} ({u['kind']})" for u in uploads]})
    return {
        "title": ("General power of attorney: " if _is_general(a) else "Specific power of attorney: ") + (donor.get("full_name") or ""),
        "notice": DRAFT_NOTICE + " " + NOT_LEGAL_ADVICE,
        "sections": sections,
        "next_steps": s["next_steps"],
        "sources": [x for st in s["steps"] for x in st.get("sources", [])],
    }
