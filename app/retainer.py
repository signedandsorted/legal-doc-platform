"""Express request to start work during the 14-day cancellation period.

Consumer Contracts (Information, Cancellation and Additional Charges)
Regulations 2013, regulation 36. Signing does not delete the right in advance.
The right to cancel a section ends when that section has been fully performed.
"""
from __future__ import annotations

SECTIONS = [
    ("will", "Will"),
    ("lpa_property", "Property and financial affairs lasting power of attorney"),
    ("lpa_health", "Health and welfare lasting power of attorney"),
    ("poa_ordinary", "Ordinary power of attorney"),
    ("probate", "Probate and estate administration"),
    ("prenup", "Prenuptial agreement"),
    ("postnup", "Postnuptial agreement"),
    ("nuptial", "Nuptial agreement"),
    ("cohabitation", "Cohabitation agreement"),
    ("employment_settlement", "Employment settlement agreement"),
    ("trust", "Trust"),
    ("deputyship", "Deputyship"),
]
SECTION_IDS = [item[0] for item in SECTIONS]

PLACES = [
    "At the firm’s office",
    "At my home, or someone else’s home",
    "At a hospital or care home",
    "At my workplace",
    "Online or by telephone, not in person",
]
OFF_PREMISES = {
    "At my home, or someone else’s home",
    "At a hospital or care home",
    "At my workplace",
}
DISTANCE = {"Online or by telephone, not in person"}


def clean_retainer(raw: dict | None) -> dict:
    raw = raw or {}
    place = raw.get("place") if raw.get("place") in PLACES else ""
    signed_on = (raw.get("signed_on") or "").strip()
    if len(signed_on) != 10:
        signed_on = ""
    name = " ".join(str(raw.get("signed_name") or "").split())[:160]
    finished = []
    for item in raw.get("finished") or []:
        if item in SECTION_IDS and item not in finished:
            finished.append(item)
    signed = bool(signed_on and name and place)
    return {
        "signed": signed,
        "signed_on": signed_on if signed else "",
        "signed_name": name if signed else "",
        "place": place if signed else place,
        "sections": list(SECTION_IDS),
        "finished": finished,
    }


def effect(record: dict, section: str) -> str:
    """What the signed retainer does for one section. It never waives the right on signature alone."""
    record = clean_retainer(record)
    title = dict(SECTIONS).get(section, "This section")
    if not record["signed"]:
        return (
            f"{title} has no signed retainer yet. If the contract is made at a home, a hospital, a workplace, or at a distance, "
            "there are 14 days to cancel. Work does not start in that period unless you sign a request to start."
        )
    if record["place"] == "At the firm’s office":
        return (
            f"The retainer for {title} was signed at the firm’s office on {record['signed_on']}. "
            "A contract made on the firm’s premises is not given the 14-day cancellation right by these regulations. "
            "That is because of where it was signed, not because the retainer waived the right."
        )
    if section in record["finished"]:
        return (
            f"{title} has been fully performed. The signed request of {record['signed_on']} said the right to cancel this section would end then. "
            "That is the end of the right for this section only. It does not cancel the right on a section that is not finished."
        )
    return (
        f"The retainer signed on {record['signed_on']} asks the firm to start {title} during the 14 days, with every other section on the list. "
        "The right to cancel this section has not ended. It ends only when this section has been fully performed. "
        "Until then you can cancel it and pay a reasonable amount for the work already done on it."
    )


def document(record: dict, client: str = "") -> dict:
    record = clean_retainer({**record, "signed_name": record.get("signed_name") or client or "the client"})
    who = record["signed_name"] or client or "the client"
    sections = "\n".join(f"- {label}" for _, label in SECTIONS)
    body = [
        f"I, {who}, ask the firm to start work during the 14-day cancellation period on every section below.",
        sections,
        "This request covers every section of this service: wills, lasting powers of attorney, an ordinary power of attorney, probate, prenuptial and postnuptial agreements, a cohabitation agreement, an employment settlement, trusts and deputyships. It is one request. Each section is a separate piece of work.",
        "I understand that I lose the right to cancel a section only when that section has been fully performed. Signing this retainer does not remove the right today.",
        "If I cancel a section before it has been fully performed, I will pay a reasonable amount for the work already done on that section. I do not pay for a section that has not been started.",
        "Where this contract is made at my home, someone else’s home, a hospital, a care home or my workplace, I make this request on this document so that there is a durable record. Where it is made online or by telephone, this document is that record.",
        "Where I sign at the firm’s office, the 14-day right does not arise from these regulations, because the contract is made on the firm’s premises.",
        "This request does not make a will, a lasting power or any other document valid. It does not stop a court claim. The firm does not start a section I have not asked for.",
        f"Place: {record['place'] or '[where the retainer is signed]'}. Date: {record['signed_on'] or '____________'}.",
        "Signed: ______________________",
    ]
    return {
        "title": "Request to start work — all sections",
        "notice": "This is the client’s request under regulation 36 of the Consumer Contracts Regulations 2013. It is not a waiver of the right to cancel before the work is finished.",
        "sections": [{"heading": "Request", "paragraphs": body}],
        "next_steps": ["The firm keeps the signed copy on the file. A tick on a screen is not the signature."],
        "sources": [{"title": "Consumer Contracts Regulations 2013", "url": "https://www.legislation.gov.uk/uksi/2013/3134/contents"}],
    }
