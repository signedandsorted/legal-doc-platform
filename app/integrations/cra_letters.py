"""Pre-filled statutory credit report request letters for the deceased (Experian; the same
letter for Equifax and TransUnion). The executor signs and sends them. Nothing is sent from here.

Source for the Experian third-party / deceased request route (checked 2026-11-24):
https://www.experian.co.uk/consumer/data-access/thirdparty.html
No agency postal addresses are hard-coded: the executor uses the address or upload route each
agency gives on its own website at the time.
"""
from __future__ import annotations

import io
import zipfile
from datetime import date
from xml.sax.saxutils import escape

from .asset_trace import details_sheet

AGENCIES = ["Experian", "Equifax", "TransUnion"]
EXPERIAN_URL = "https://www.experian.co.uk/consumer/data-access/thirdparty.html"
ENCLOSURES = [
    "A copy of the grant of probate or letters of administration",
    "A copy of my photo ID (passport or driving licence)",
    "Two proofs of my address (for example a recent utility bill and a bank statement)",
    "A copy of the death certificate",
]
NOTE = "You sign and send these letters yourself. Nothing is sent to any credit reference agency from this website."


def letters(answers: dict, today: date | None = None) -> dict:
    dec = answers.get("deceased") or {}
    applicant = (answers.get("will") or {}).get("applicant") or {}
    sheet = details_sheet(answers)
    rows = {r["label"]: r["value"] for r in sheet["rows"]}
    missing = list(sheet["missing"])
    if not applicant.get("full_name"):
        missing.append("Your name (executor or administrator)")
    if not applicant.get("address"):
        missing.append("Your address")
    ph = lambda v, label: v or f"[{label}]"  # noqa: E731
    me, my_addr = ph(applicant.get("full_name"), "your name"), ph(applicant.get("address"), "your address")
    when = (today or date.today()).strftime("%d %B %Y")
    out = []
    for agency in AGENCIES:
        body = [
            my_addr, "", when, "", f"{agency}", "Statutory credit report request for a person who has died", "",
            "Dear Sir or Madam,", "",
            f"I am the executor or administrator of the estate of {ph(rows['Full name'], 'full name')}"
            + (f" (also known as {rows['Other or previous names']})" if rows["Other or previous names"] else "")
            + f", born {ph(rows['Date of birth'], 'date of birth')}, who died on {ph(rows['Date of death'], 'date of death')}.",
            f"Their last address was {ph(rows['Last address'], 'last address')}."
            + (f" Other addresses in the last 6 years: {rows['Other addresses in the last 6 years']}." if rows["Other addresses in the last 6 years"] else " [List their other addresses in the last 6 years.]"),
            "",
            "Please send me a copy of the credit report you hold for them, showing each lender, account and balance, so that I can deal with their estate. Please also note the death on your records.",
            "", "I enclose:", *[f"- {e}" for e in ENCLOSURES], "",
            "Yours faithfully,", "", "", me, "Executor or administrator",
        ]
        out.append({"agency": agency, "title": f"Credit report request to {agency}", "lines": body})
    return {"letters": out, "missing": missing, "enclosures": ENCLOSURES, "experian_url": EXPERIAN_URL, "note": NOTE}


def pdf_document(pack: dict) -> dict:
    return {
        "title": "Credit report request letters",
        "notice": pack["note"],
        "sections": [{"heading": l["title"], "paragraphs": [x if x else " " for x in l["lines"]]} for l in pack["letters"]],
        "next_steps": ["Fill in anything in [square brackets].", "Sign each letter.", "Send it with the enclosures using the route each agency gives on its website.", "When a report comes back, add any accounts it shows to the estate."],
        "sources": [{"title": "Experian: requests for someone who has died or by a third party", "url": EXPERIAN_URL}],
    }


def docx_bytes(pack: dict) -> bytes:
    """A minimal Word document (no extra dependency): one letter per page."""
    paras = []
    for i, l in enumerate(pack["letters"]):
        if i:
            paras.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        for line in l["lines"]:
            paras.append(f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(paras) + "</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", doc)
    return buf.getvalue()
