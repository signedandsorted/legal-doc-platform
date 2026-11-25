"""Wills and Inheritance Quality Scheme support for a firm file.

The scheme accredits an SRA practice, not a piece of software. These points are
this desk's own checklist, written against the public scheme pages and the
Wills and Inheritance Protocol (version 1.0, 3 July 2013). They are not a copy
of the protocol and they do not confer the quality mark.
"""

PROTOCOL = "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme"
HOW = "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme/how-to-apply"
TRAINING = "https://www.lawsociety.org.uk/topics/firm-accreditations/wills-and-inheritance-quality-scheme/training"
PROTOCOL_PDF = "https://tls-sc104-prd-glo-fde-01-duatf0eka4hpcxe6.a03.azurefd.net/-/media/files/accreditations/wiqs/wills-and-inheritance-protocol.pdf?rev=a7a352c41cbd4f58b38c9ab40443afe4&hash=A390E01065FCEE60FDD8DB84CC524417"
CORE_PDF = "https://tls-sc104-prd-glo-fde-01-duatf0eka4hpcxe6.a03.azurefd.net/-/media/files/accreditations/wiqs/wiqs-core-practice-management-standards.pdf?rev=ce10ee03ef87441b952db535ae8c8e47&hash=3A948F2B528497D171D6DA2593932F9F"
CONSUMER = "https://www.legislation.gov.uk/uksi/2013/3134/contents"
DBS = "https://www.gov.uk/request-copy-criminal-record"

LINKS = [
    {"title": "Wills and Inheritance Quality Scheme", "url": PROTOCOL},
    {"title": "How a firm applies", "url": HOW},
    {"title": "Mandatory training after accreditation", "url": TRAINING},
    {"title": "Wills and Inheritance Protocol (PDF, version 1.0, 3 July 2013)", "url": PROTOCOL_PDF},
    {"title": "Core practice management standards (PDF, July 2013)", "url": CORE_PDF},
    {"title": "Consumer Contracts Regulations 2013", "url": CONSUMER},
    {"title": "GOV.UK: basic DBS check", "url": DBS},
]

CANNOT = [
    "This desk cannot award the quality mark. Only the Law Society accredits an SRA-regulated practice that offers both wills and estate administration.",
    "It does not appoint the senior responsible officer, run Disclosure and Barring Service checks, or complete the mandatory training.",
    "A tick here is not a file review, a costs letter, or an attendance note. The firm still does those.",
    "The protocol PDF on the Law Society site is still version 1.0 of 3 July 2013. Where later law is different, follow the later law. The cooling-off period is the example below.",
]

# area is used to decide which matters show the point.
ITEMS = [
    {"id": "sro", "area": "practice", "point": "The firm, not this desk, appoints a senior responsible officer and applies to the Law Society. Record the officer’s name on the firm’s own list. A tick does not accredit the practice."},
    {"id": "accept", "area": "practice", "point": "Record why the matter was accepted and that the person doing it is competent. If it is beyond them, they tell the supervisor and the work is moved."},
    {"id": "costs", "area": "practice", "point": "At the start, tell the client in writing how you charge, the estimate, and what they may have to pay to others. If the estimate will be exceeded, tell them before the extra work is done."},
    {"id": "people", "area": "practice", "point": "Name the person doing the work and the person supervising it. If either changes, write to the client with the new name and status."},
    {"id": "complaints", "area": "practice", "point": "At the start, tell the client they can complain, who to, and that they can ask for the complaints procedure. A complaint is answered in the firm’s own process."},
    {"id": "vulnerable", "area": "practice", "point": "Consider vulnerability: illness, bereavement, age, disability, a learning difficulty, or pressure. Do not press a vulnerable client to buy a further service. See the client alone if someone else came with them."},
    {"id": "plain", "area": "practice", "point": "Advice is in plain English. Where a legal word is necessary, it is explained."},
    {"id": "timescale", "area": "practice", "point": "Agree a timescale. If it slips, including because someone at the firm is away, tell the client why and give a new date."},
    {"id": "conflict", "area": "practice", "point": "Check for a conflict before you start, and again if the facts change. A gift to the drafter, their family or an employee is recorded. Joint clients are told that a later secret change is usually not taken."},
    {"id": "offpremises", "area": "practice", "point": "If the contract was made at the client’s home, a hospital or a workplace, or at a distance, the Consumer Contracts Regulations 2013 give 14 days to cancel. A signed retainer can ask the firm to start every section during those 14 days. Signing does not waive the right. The right to cancel a section ends only when that section has been fully performed. Until then the client can cancel it and pay a reasonable amount for the work already done. A contract signed at the firm’s office does not get that 14-day right, because of where it was signed. The 2013 protocol’s 7-day period is out of date. Use 14 days."},
    {"id": "close", "area": "practice", "point": "At the end, report the outcome, account for any money, return originals unless storage was agreed, say when the client should review the matter, and keep the file for the firm’s retention period."},
    {"id": "file-review", "area": "practice", "point": "Someone who did not do the work reviews the file. Anything they find is put right within 28 days and the reviewer checks that it was. This screen records that. It does not carry out the review."},
    {"id": "dbs", "area": "practice", "point": "Basic Disclosure and Barring Service checks for the senior responsible officer and the other relevant people are ordered by the firm. An existing check is accepted by the scheme only if it is under 12 months old. This desk does not run the check."},
    {"id": "alone", "area": "will", "point": "Will instructions were taken without a beneficiary in the room, or the advice to do that and the client’s answer are on the attendance note."},
    {"id": "joint", "area": "will", "point": "Where a couple gave instructions together, each agreed to that, and each was told that a conflict means the firm may have to stop acting for both, and that a later significant change will not be made in secret."},
    {"id": "oldwill", "area": "will", "point": "Any earlier will was read by a person, not only by the machine. It was not crossed out or written on. It is not destroyed until the new will is signed and witnessed. The reasons for the changes are noted."},
    {"id": "outside", "area": "will", "point": "Assets that pass outside the will were discussed: joint property, pensions, death-in-service benefits, and life policies written in trust."},
    {"id": "act1975", "area": "will", "point": "People who might claim under the Inheritance (Provision for Family and Dependants) Act 1975 were identified. Reasons for leaving someone out are kept off the will. The statement does not stop a claim."},
    {"id": "tax", "area": "will", "point": "Inheritance tax was explained in broad terms, including what is not calculated on this screen. The client was not told that a particular scheme removes the tax."},
    {"id": "foreign", "area": "will", "point": "Foreign property was asked about. If a foreign will should stand, the new revocation clause is limited to property in England and Wales."},
    {"id": "business", "area": "will", "point": "Business and farm assets, and any partnership or shareholders’ agreement, were asked about. The gift of those assets is drafted by a solicitor, not left as a placeholder."},
    {"id": "review-will", "area": "will", "point": "The client was told to review the will after marriage, divorce, children, a move, or a large change in what they own. Marriage or a civil partnership usually revokes a will unless it was made in expectation of that event."},
    {"id": "terms", "area": "will", "point": "The client confirmed the draft that was sent. That version is the one kept on the file. An older version is still there."},
    {"id": "execution", "area": "will", "point": "Signing was supervised, or written instructions were given: the client signs first, then two adult witnesses, both present at the same time. A witness is not a beneficiary or the spouse or civil partner of a beneficiary."},
    {"id": "storage", "area": "will", "point": "Where the new original is stored is recorded. The earlier original is stored or returned to the client. A copy of a revoked will stays on the file. An original the firm holds is the client’s property, and after death the estate’s."},
    {"id": "larke", "area": "will", "point": "The attendance note is full enough that, years later, the drafter could explain the instructions and the signing if the will is challenged."},
    {"id": "before", "area": "estate", "point": "Before the estate was taken on, the firm checked who is entitled to instruct and whether the validity of the will is disputed. A disputed will is not pushed through the ordinary application."},
    {"id": "executor-firm", "area": "estate", "point": "If someone at the firm is an executor, the client was not told that a solicitor executor is essential. The right to charge, and the likely cost, were explained."},
    {"id": "protect", "area": "estate", "point": "The steps to protect the estate are listed: insure an empty property, secure valuables, and keep the original will safe. Nothing is sold from this screen."},
    {"id": "benefits", "area": "estate", "point": "Tell Us Once and any state benefits were mentioned to the family. This desk does not claim the benefits."},
    {"id": "report28", "area": "estate", "point": "On an estate, write to the client about progress every 28 days unless a different interval was agreed. Record the date of the last report. The next date then shows with the other deadlines."},
    {"id": "accounts", "area": "estate", "point": "Estate accounts are prepared from the one set of figures before the residue is paid. A beneficiary is not told a figure is final while assets are still to be collected."},
    {"id": "variation", "area": "estate", "point": "A change to who inherits after the death, if the family wants one, is their decision and is usually made within two years. This desk does not send it to HMRC."},
    {"id": "claim1975", "area": "estate", "point": "If a 1975 Act claim arrives, distribution of the assets in dispute stops. The personal representatives do not admit liability in a letter. The six-month period from the grant is already on the deadline list."},
    {"id": "lpa-order", "area": "lpa", "point": "The lasting power is signed in the LP12 order: donor, certificate provider, attorneys, then section 15. The wrong order means the Office of the Public Guardian will not register it."},
    {"id": "certificate", "area": "lpa", "point": "The certificate provider is eligible and saw the donor, not only the attorneys. The donor’s understanding was discussed with the donor."},
    {"id": "ordinary", "area": "lpa", "point": "An ordinary power of attorney was explained as ending if the donor loses capacity. It is not registered with the Office of the Public Guardian."},
    {"id": "independent", "area": "agreement", "point": "Each person has their own advice before signing. A prenuptial or postnuptial agreement is not automatically binding. An employment settlement that waives claims needs advice for the employee. A cohabitation agreement does not create the rights of a marriage."},
    {"id": "disclosure", "area": "agreement", "point": "For a nuptial agreement, each side’s financial disclosure is on the file before anyone is asked to sign."},
    {"id": "separate-money", "area": "trust", "point": "Trust or deputyship money is recorded apart from the firm’s own money. A deputyship follows the court order. Nothing is paid out of this website."},
]

_IDS = {item["id"] for item in ITEMS}


def areas_for(kind: str) -> set[str]:
    areas = {"practice"}
    if kind == "will":
        areas.add("will")
    elif kind == "probate":
        areas.add("estate")
    elif str(kind).startswith("lpa") or kind == "poa_ordinary":
        areas.add("lpa")
    elif kind in {"prenup", "postnup", "nuptial", "cohabitation", "employment_settlement"}:
        areas.add("agreement")
    elif kind in {"trust", "deputyship"}:
        areas.add("trust")
    return areas


def for_matter(kind: str, saved: dict | None) -> dict:
    saved = saved or {}
    done = {item for item in (saved.get("done") or []) if item in _IDS}
    wanted = areas_for(kind)
    items = [{**item, "done": item["id"] in done} for item in ITEMS if item["area"] in wanted]
    return {
        "notice": "This is the firm’s checklist for the Wills and Inheritance Quality Scheme. It follows the public scheme pages and the 2013 protocol. It is not the protocol, and it does not make the firm a member.",
        "cannot": CANNOT,
        "links": LINKS,
        "items": items,
        "done": sorted(done),
        "last_report": saved.get("last_report") or "",
        "open": sum(1 for item in items if not item["done"]),
    }


def clean_saved(done: list, last_report: str) -> dict:
    kept = []
    for item in done or []:
        if item in _IDS and item not in kept:
            kept.append(item)
    report = (last_report or "").strip()
    if report and len(report) != 10:
        report = ""
    return {"done": kept[:80], "last_report": report}
