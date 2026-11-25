"""Estate account in the shape a probate firm expects, and the places to look for accounts nobody mentioned.

This is not a credit-file search. Firms that sell those buy a data feed. Here the family and the firm work the official tracing services, and anything found is typed once into the same list.
"""
from .common import money

KINDS = ("property", "bank", "shares", "goods", "pension", "other")
KIND_LABEL = {
    "property": "Houses, land and buildings",
    "bank": "Bank and building society accounts",
    "shares": "Stocks, shares and investments",
    "goods": "Household and personal goods",
    "pension": "Pensions and life policies paid to the estate",
    "other": "Other assets",
}
DISCOVERY = [
    {"id": "banks", "place": "Banks and building societies", "ask": "Ask every bank they used. Then use My Lost Account for ones nobody knew about. It is free and covers banks, building societies and NS&I.", "url": "https://www.mylostaccount.org.uk/", "url_title": "My Lost Account"},
    {"id": "nsandi", "place": "Premium Bonds and NS&I", "ask": "Ask NS&I. Premium Bonds do not always show on a bank statement.", "url": "https://www.nsandi.com/", "url_title": "NS&I"},
    {"id": "pensions", "place": "Pensions", "ask": "Use the Pension Tracing Service for workplace and personal pensions the family cannot find.", "url": "https://www.gov.uk/find-pension-contact-details", "url_title": "Pension Tracing Service"},
    {"id": "property", "place": "Property", "ask": "Search the Land Registry for houses or land in their name.", "url": "https://www.gov.uk/search-property-information-land-registry", "url_title": "Search for property information"},
    {"id": "shares", "place": "Shares and funds", "ask": "Check dividend letters, brokers and the three main registrars: Equiniti, Computershare and Link. A date-of-death price is typed from the valuation you obtain. This desk does not look up a share price.", "url": "", "url_title": ""},
    {"id": "insurance", "place": "Life insurance", "ask": "Ask any insurer named in the papers, and the employer if it may be a death-in-service policy.", "url": "", "url_title": ""},
    {"id": "employer", "place": "Last employer", "ask": "Ask about unpaid pay, shares and any lump sum.", "url": "", "url_title": ""},
    {"id": "benefits", "place": "State Pension and benefits", "ask": "Tell Us Once can notify several government departments from one report.", "url": "https://www.gov.uk/tell-us-once", "url_title": "Tell Us Once"},
    {"id": "cards", "place": "Credit cards, loans and catalogues", "ask": "These are usually debts. A statement in the post is the usual clue. Open and closed credit accounts come from a bureau report, not from this page.", "url": "", "url_title": ""},
    {"id": "digital", "place": "PayPal, transfers and online balances", "ask": "Search email for payment receipts, then write to the company. A sweep of crypto exchanges is a paid search, not a button here.", "url": "", "url_title": ""},
    {"id": "companies", "place": "Companies House", "ask": "Search the free register for directorships and companies in their name. The Estatesearch premium search also does this. You can do the register yourself.", "url": "https://find-and-update.company-information.service.gov.uk/", "url_title": "Find company information"},
    {"id": "opg", "place": "Lasting powers and deputyships", "ask": "Ask the Office of the Public Guardian whether a lasting power or a deputyship is registered.", "url": "https://www.gov.uk/find-someones-attorney-deputy-or-guardian", "url_title": "Find an attorney, deputy or guardian"},
    {"id": "insolvency", "place": "Bankruptcy and IVAs", "ask": "Search the public Individual Insolvency Register. A credit report can show CCJs as well. This register does not show a credit file.", "url": "https://www.gov.uk/search-bankruptcy-insolvency-register", "url_title": "Search the bankruptcy and insolvency register"},
    {"id": "wills", "place": "A will that has not been found", "ask": "Search wills that have already been proved, and record any paid search of the National Will Register. This desk does not search that register.", "url": "https://www.gov.uk/search-will-probate", "url_title": "Search for a will or probate"},
    {"id": "vehicle", "place": "A vehicle", "ask": "Tell DVLA. Tax and MOT status are not looked up here. Type the open-market value once you have it.", "url": "https://www.gov.uk/tell-dvla-about-bereavement", "url_title": "Tell DVLA about a death"},
]
STATUS = ("not_asked", "asked", "found", "nothing")


def guess_kind(name: str) -> str:
    text = (name or "").lower()
    if any(word in text for word in ("house", "flat", "property", "land", "bungalow")):
        return "property"
    if any(word in text for word in ("bank", "isa", "savings", "building society")):
        return "bank"
    if any(word in text for word in ("share", "stock", "fund", "investment")):
        return "shares"
    if "pension" in text or "life" in text:
        return "pension"
    if any(word in text for word in ("car", "jewellery", "furniture", "goods")):
        return "goods"
    return "other"


def clean_discovery(raw) -> list[dict]:
    saved = {item.get("id"): item for item in (raw or []) if isinstance(item, dict)}
    out = []
    for place in DISCOVERY:
        row = saved.get(place["id"]) or {}
        status = row.get("status") if row.get("status") in STATUS else "not_asked"
        note = str(row.get("note") or "").strip()[:400]
        out.append({**place, "status": status, "note": note})
    return out


def step_account(accounts: dict) -> dict:
    """Capital account, income account, distribution and a cash reconciliation."""
    totals = accounts["totals"]
    capital = []
    at_death = gains = losses = 0.0
    for row in accounts["capital"]:
        collected = row["collected"] or 0.0
        movement = round(collected - row["dod"], 2) if collected else 0.0
        at_death += row["dod"]
        gains += max(0.0, movement)
        losses += max(0.0, -movement)
        capital.append({"name": row["name"], "holder": row["holder"], "at_death": row["dod"], "movement": movement, "income": row["income"], "costs": row["costs"]})
    capital_out = totals["costs"] + totals["debts"] + totals["funeral"] + totals["tax"] + totals["specific"]
    capital_balance = at_death + gains - losses - totals["costs"] - totals["debts"] - totals["funeral"] - totals["tax"] - totals["specific"]
    paid_out = sum(person["paid"] for person in accounts["people"])
    receipts = totals["collected"] + totals["income"]
    payments = totals["costs"] + totals["debts_paid"] + totals["funeral_paid"] + totals["tax_paid"] + paid_out
    return {
        "title": "Estate account",
        "note": "Set out as a capital account, an income account and a distribution. It follows the usual probate layout. A solicitor approves it before it is sent to the family. It is not a substitute for their sign-off.",
        "capital": capital,
        "capital_totals": {
            "at_death": round(at_death, 2), "gains": round(gains, 2), "losses": round(losses, 2),
            "costs": totals["costs"], "debts": totals["debts"], "funeral": totals["funeral"], "tax": totals["tax"],
            "legacies": totals["specific"], "balance": round(capital_balance, 2), "payments": round(capital_out, 2),
        },
        "income_total": totals["income"],
        "distribution": accounts["people"],
        "residue": totals["residue"],
        "cash": {"receipts": round(receipts, 2), "payments": round(payments, 2), "in_hand": round(receipts - payments, 2)},
        "outside": accounts["outside"],
    }


def account_document(matter: dict, accounts: dict) -> dict:
    step = accounts["step"]
    estate = matter.get("deceased_name") or matter.get("title") or "the estate"
    cap = step["capital_totals"]
    sections = [
        {"heading": "Capital account", "paragraphs": [
            f"{row['name']}: value at death {money(row['at_death'])}" + (f", change on collection {money(row['movement'])}" if row["movement"] else "") + (f", costs {money(row['costs'])}" if row["costs"] else "")
            for row in step["capital"]
        ] or ["No assets in the probate estate yet."]},
        {"heading": "Capital account totals", "paragraphs": [
            f"Assets at death {money(cap['at_death'])}.",
            f"Gains on collection {money(cap['gains'])}. Losses on collection {money(cap['losses'])}.",
            f"Costs of sale {money(cap['costs'])}. Debts {money(cap['debts'])}. Funeral {money(cap['funeral'])}. Tax estimate {money(cap['tax'])}. Specific gifts {money(cap['legacies'])}.",
            f"Balance of the capital account {money(cap['balance'])}.",
        ]},
        {"heading": "Income account", "paragraphs": [f"Income received after death {money(step['income_total'])}."]},
        {"heading": "Distribution account", "paragraphs": [
            f"{person['name']}: entitled {money(person['entitlement'])}, paid {money(person['paid'])}, due {money(person['due'])}"
            for person in step["distribution"]
        ] or ["No beneficiaries entered. The will, or the law if there is no will, decides who inherits."]},
        {"heading": "Cash", "paragraphs": [
            f"Collected and income {money(step['cash']['receipts'])}.",
            f"Costs, debts, funeral, tax and sums already paid out {money(step['cash']['payments'])}.",
            f"Cash that should be in hand {money(step['cash']['in_hand'])}.",
        ]},
    ]
    if step["outside"]:
        sections.append({"heading": "Not in this account", "paragraphs": [f"{row['name']}: {money(row['value'])}. {row['why']}" for row in step["outside"]]})
    return {
        "title": f"Estate account — {estate}",
        "notice": step["note"],
        "sections": sections,
        "next_steps": ["A solicitor checks this account before anyone is paid.", "Download the copy you can edit if a figure needs a note the list does not hold."],
        "sources": [{"title": "GOV.UK: Applying for probate", "url": "https://www.gov.uk/applying-for-probate"}],
    }


def account_html(matter: dict, accounts: dict) -> str:
    step = accounts["step"]
    cap = step["capital_totals"]
    estate = matter.get("deceased_name") or "the estate"
    rows = "".join(
        f"<tr><td>{_h(row['name'])}</td><td>{money(row['at_death'])}</td><td>{money(row['movement'])}</td><td>{money(row['costs'])}</td></tr>"
        for row in step["capital"]
    )
    people = "".join(
        f"<tr><td>{_h(person['name'])}</td><td>{money(person['entitlement'])}</td><td>{money(person['paid'])}</td><td>{money(person['due'])}</td></tr>"
        for person in step["distribution"]
    )
    return f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="utf-8"><title>Estate account</title>
<style>body{{font-family:Georgia,serif;max-width:760px;margin:32px auto;color:#1c2333}} table{{width:100%;border-collapse:collapse}} td,th{{border-bottom:1px solid #ddd;text-align:left;padding:6px}} .note{{color:#667}} </style></head>
<body><h1>Estate account — {_h(estate)}</h1><p class="note">{_h(step['note'])}</p>
<h2>Capital account</h2><table><tr><th>Item</th><th>At death</th><th>Change</th><th>Costs</th></tr>{rows}</table>
<p>At death {money(cap['at_death'])}. Gains {money(cap['gains'])}. Losses {money(cap['losses'])}. Debts {money(cap['debts'])}. Funeral {money(cap['funeral'])}. Tax {money(cap['tax'])}. Specific gifts {money(cap['legacies'])}.</p>
<p><b>Balance of capital {money(cap['balance'])}.</b></p>
<h2>Income account</h2><p>Income after death {money(step['income_total'])}.</p>
<h2>Distribution</h2><table><tr><th>Person</th><th>Entitled</th><th>Paid</th><th>Due</th></tr>{people}</table>
<h2>Cash</h2><p>In {money(step['cash']['receipts'])}. Out {money(step['cash']['payments'])}. Should be in hand {money(step['cash']['in_hand'])}.</p>
</body></html>"""


def _h(value: str) -> str:
    return (value or "").replace("&", "&").replace("<", "<").replace(">", ">")


def clean_notice(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    placed = str(raw.get("placed_on") or "").strip()[:10]
    if len(placed) != 10 or placed[4] != "-" or placed[7] != "-":
        placed = ""
    return {
        "placed_on": placed,
        "gazette_ref": str(raw.get("gazette_ref") or "").strip()[:80],
        "local_paper": str(raw.get("local_paper") or "").strip()[:120],
        "claims_to": str(raw.get("claims_to") or "").strip()[:240],
    }


def clean_copied(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:40]:
        text = str(item or "").strip()[:80]
        if text and text not in out:
            out.append(text)
    return out


def notice_text(matter: dict, books: dict) -> dict:
    """Wording for a Trustee Act 1925 section 27 notice. The firm places it. This desk does not."""
    estate = matter.get("deceased_name") or "the person who died"
    died = matter.get("date_of_death") or "[date of death]"
    address = (books.get("case") or {}).get("address") or "[last address]"
    claims = (books.get("notice") or {}).get("claims_to") or "[name and address of the firm]"
    firm = matter.get("client_name") or "The personal representatives"
    body = "\n".join([
        f"{estate}, deceased",
        f"Late of {address}, who died on {died}.",
        "",
        f"Notice is given that creditors and others having claims against the estate of the above named should send written particulars of those claims to {claims} within two months of the date of this notice.",
        "",
        "After that time the personal representatives will distribute the estate having regard only to the claims of which they then have notice.",
        "",
        "This notice is given under section 27 of the Trustee Act 1925. It does not shut out a claim the firm already knows about.",
        "If the estate includes land, the same notice also has to go in a newspaper local to that land, as well as The London Gazette.",
        "",
        "The firm places this notice. It is not sent from this desk.",
        "",
        firm,
    ])
    return {"title": f"Section 27 notice — estate of {estate}", "body": body}


AGENCIES = ("Experian", "Equifax", "TransUnion", "Estatesearch")


def clean_credit(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    ordered = str(raw.get("ordered_on") or "").strip()[:10]
    received = str(raw.get("received_on") or "").strip()[:10]
    if len(ordered) != 10 or ordered[4] != "-":
        ordered = ""
    if len(received) != 10 or received[4] != "-":
        received = ""
    agency = raw.get("agency") if raw.get("agency") in AGENCIES else ""
    try:
        fee = round(float(raw.get("fee") or 0), 2)
    except (TypeError, ValueError):
        fee = 0.0
    fee = min(10000.0, max(0.0, fee))
    return {
        "agency": agency,
        "reference": str(raw.get("reference") or "").strip()[:80],
        "ordered_on": ordered,
        "received_on": received,
        "note": str(raw.get("note") or "").strip()[:400],
        "fee": fee,
    }


def credit_letter(matter: dict, books: dict) -> dict:
    """A letter the firm posts or uploads to the agency. This desk does not send it."""
    estate = matter.get("deceased_name") or "[full name]"
    died = matter.get("date_of_death") or "[date of death]"
    address = (books.get("case") or {}).get("address") or "[last address]"
    name = matter.get("client_name") or "The personal representatives"
    credit = clean_credit(books.get("credit"))
    ref = f" Their reference is {credit['reference']}." if credit.get("reference") else ""
    body = "\n".join([
        "Dear Sir or Madam,",
        "",
        f"We act in the estate of {estate}, late of {address}, who died on {died}.",
        "Please send the credit report you hold, including each lender, account and balance on the file." + ref,
        "A copy of the death certificate is enclosed. The grant will follow if you require it before releasing the report.",
        "",
        "The firm sends this request. The software does not.",
        "",
        "Yours faithfully,",
        name,
    ])
    return {"title": f"Credit report request — estate of {estate}", "body": body}


SEARCH_TARGETS = [
    ("barclays", "Barclays", "main"),
    ("lloyds", "Lloyds", "main"),
    ("hsbc", "HSBC", "main"),
    ("natwest", "NatWest", "main"),
    ("santander", "Santander", "main"),
    ("nationwide", "Nationwide", "main"),
    ("halifax", "Halifax", "main"),
    ("nsandi", "NS&I, including Premium Bonds", "main"),
    ("aviva", "Aviva", "extra"),
    ("landg", "Legal & General", "extra"),
    ("widows", "Scottish Widows", "extra"),
    ("standard", "Standard Life", "extra"),
    ("hl", "Hargreaves Lansdown", "extra"),
    ("computershare", "Computershare", "extra"),
    ("equiniti", "Equiniti", "extra"),
    ("link", "Link Group", "extra"),
    ("dwp", "Department for Work and Pensions", "extra"),
    ("royal", "The Royal Mint", "extra"),
    ("paypal", "PayPal", "extra"),
]
SEARCH_STATUS = ("ready", "sent", "found", "nothing")


def clean_asset_search(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    saved = {item.get("id"): item for item in (raw.get("items") or []) if isinstance(item, dict)}
    items = []
    for tid, name, group in SEARCH_TARGETS:
        row = saved.get(tid) or {}
        status = row.get("status") if row.get("status") in SEARCH_STATUS else ""
        items.append({"id": tid, "name": name, "group": group, "status": status})
    try:
        fee = round(float(raw.get("fee") or 0), 2)
    except (TypeError, ValueError):
        fee = 0.0
    fee = min(10000.0, max(0.0, fee))
    return {"fee": fee, "paid": raw.get("paid") in (True, "Yes", "yes", "on"), "items": items}


def enquiry_letter(matter: dict, books: dict, institution: str) -> dict:
    estate = matter.get("deceased_name") or "[full name]"
    died = matter.get("date_of_death") or "[date of death]"
    address = (books.get("case") or {}).get("address") or "[last address]"
    name = matter.get("client_name") or "The personal representatives"
    body = "\n".join([
        f"Dear Bereavement team, {institution},",
        "",
        f"We act in the estate of {estate}, late of {address}, who died on {died}.",
        "Please say whether this person held an account, policy or investment with you, and the balance at the date of death.",
        "Please also say whether you will release the funds without a grant.",
        "A copy of the death certificate can follow.",
        "",
        "The firm posts or emails this letter. It has not been sent by the software.",
        "",
        "Yours faithfully,",
        name,
    ])
    return {"title": f"Asset enquiry — {institution}", "body": body}


def prepare_asset_search(matter: dict, books: dict, chosen: list[str], fee: float, paid: bool) -> dict:
    """Draft one enquiry per chosen institution. Does not send them and does not invent a balance."""
    books = dict(books)
    search = clean_asset_search(books.get("asset_search"))
    wanted = [item for item in search["items"] if item["id"] in set(chosen)]
    if not wanted:
        raise ValueError("Choose at least one institution")
    letters = list(books.get("letters") or [])
    by_id = {item["id"]: item for item in search["items"]}
    for item in wanted:
        if item["status"] in ("ready", "sent", "found", "nothing"):
            continue
        letter = enquiry_letter(matter, books, item["name"])
        letters.append({"title": letter["title"], "body": letter["body"]})
        by_id[item["id"]]["status"] = "ready"
    search["items"] = [by_id[tid] for tid, _name, _group in SEARCH_TARGETS]
    search["fee"] = fee
    search["paid"] = paid
    books["letters"] = letters
    books["asset_search"] = search
    return books


PORTAL = "https://www.estatesearch.co.uk/services/"
ORDER_STATUS = ("not_ordered", "ordered", "report_in", "nothing", "not_using")
PRODUCTS = [
    {"id": "liability", "name": "Credit and liabilities search", "price": "£25 + VAT", "covers": "Bankruptcy, CCJs, IVAs, previous names and addresses, open and closed credit accounts."},
    {"id": "standard", "name": "Financial Profile Standard", "price": "£165 + VAT", "covers": "Credit and liability data, a notice to hundreds of organisations, and a vulnerability registration."},
    {"id": "premium", "name": "Financial Profile Premium", "price": "£210 + VAT", "covers": "Live, online, lost and dormant accounts, an unclaimed-asset search, Companies House and the OPG."},
    {"id": "international", "name": "International financial profile", "price": "Price on application", "covers": "Enquiries to institutions in one other country. The price depends on the country."},
    {"id": "hnw", "name": "High net worth bolt-on", "price": "£250 + VAT", "covers": "Private banks, wealth managers and the Royal Mint."},
    {"id": "digital", "name": "Digital assets search", "price": "£35 + VAT", "covers": "Cryptocurrency exchanges, online gambling and money-transfer services."},
    {"id": "living", "name": "Financial asset search for the living", "price": "£155 + VAT", "covers": "Lost accounts of a living person, used for a deputy or an attorney."},
    {"id": "gazette", "name": "Section 27 notice in The Gazette", "price": "Their price list", "covers": "Place this yourself on The Gazette. In the same order they can place the local newspaper advert. You do not need Estatesearch for it."},
    {"id": "localad", "name": "Section 27 notice in a local paper", "price": "Set by The Gazette", "covers": "If the estate includes land. The Gazette offers this when you place the notice. A local paper is still required."},
    {"id": "will", "name": "Will search", "price": "£60 + VAT", "covers": "A paid search for a will. Not the free search of wills that have already been proved."},
    {"id": "missingwill", "name": "Missing will service", "price": "£349 + VAT", "covers": "Probate registry, the National Will Register, and a postal search. Can lead to missing-will insurance."},
    {"id": "shareval", "name": "Share valuation", "price": "£10 + VAT a holding", "covers": "Date-of-death price, ex-dividend and company changes. Type the figure they return onto the share."},
    {"id": "sharecheck", "name": "Share verification", "price": "£10 + VAT a holding", "covers": "How many shares, and whether they are certificated or in a nominee."},
    {"id": "sharesale", "name": "Share sale or transfer", "price": "£55 + VAT a holding", "covers": "They register the grant and prepare the forms. Brokerage is extra."},
    {"id": "vehicle", "name": "Vehicle valuation", "price": "£10 + VAT", "covers": "Open-market value, MOT, tax and outstanding finance. Type the value onto the car."},
    {"id": "identity", "name": "Identity and bankruptcy check", "price": "From £4 + VAT", "covers": "An identity check and an insolvency search on a living person. Not an electronic check in this desk."},
]
COVERS = [
    ("unoccupied", "Unoccupied property insurance"),
    ("missing_will", "Missing will insurance"),
    ("no_notice", "No section 27 insurance"),
    ("missing_person", "Missing beneficiary insurance"),
    ("early", "Early distribution insurance"),
    ("share_cert", "Missing share certificate insurance"),
]
COVER_DECISION = ("not_considered", "asked", "bought", "not_buying")
WILL_RESULT = ("not_searched", "none_found", "will_found", "later_will")


def _fee(value) -> float:
    try:
        number = round(float(value or 0), 2)
    except (TypeError, ValueError):
        number = 0.0
    return min(10000.0, max(0.0, number))


def _day(value) -> str:
    text = str(value or "").strip()[:10]
    return text if len(text) == 10 and text[4] == "-" else ""


def clean_orders(raw) -> list[dict]:
    saved = {}
    if isinstance(raw, list):
        saved = {item.get("id"): item for item in raw if isinstance(item, dict)}
    elif isinstance(raw, dict):
        saved = {key: value for key, value in raw.items() if isinstance(value, dict)}
    out = []
    for product in PRODUCTS:
        row = saved.get(product["id"]) or {}
        status = row.get("status") if row.get("status") in ORDER_STATUS else "not_ordered"
        out.append({
            **product,
            "status": status,
            "reference": str(row.get("reference") or "").strip()[:80],
            "ordered_on": _day(row.get("ordered_on")),
            "fee": _fee(row.get("fee")),
            "note": str(row.get("note") or "").strip()[:240],
        })
    return out


def clean_will_search(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    result = raw.get("result") if raw.get("result") in WILL_RESULT else "not_searched"
    return {
        "result": result,
        "where": str(raw.get("where") or "").strip()[:80],
        "reference": str(raw.get("reference") or "").strip()[:80],
        "note": str(raw.get("note") or "").strip()[:400],
    }


def clean_covers(raw) -> list[dict]:
    saved = {}
    if isinstance(raw, list):
        saved = {item.get("id"): item for item in raw if isinstance(item, dict)}
    elif isinstance(raw, dict):
        saved = {key: value for key, value in raw.items() if isinstance(value, dict)}
    out = []
    for cid, name in COVERS:
        row = saved.get(cid) or {}
        decision = row.get("decision") if row.get("decision") in COVER_DECISION else "not_considered"
        out.append({
            "id": cid,
            "name": name,
            "decision": decision,
            "reference": str(row.get("reference") or "").strip()[:80],
            "note": str(row.get("note") or "").strip()[:240],
        })
    return out


VRS_STATUS = ("not_registered", "registered", "not_needed")


def clean_vrs(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    status = raw.get("status") if raw.get("status") in VRS_STATUS else "not_registered"
    return {
        "status": status,
        "reference": str(raw.get("reference") or "").strip()[:80],
        "note": str(raw.get("note") or "").strip()[:240],
    }


def estatesearch_letter(matter: dict, books: dict) -> dict:
    """An email the firm sends. This desk does not send it."""
    estate = matter.get("deceased_name") or "[full name of the person who died]"
    died = matter.get("date_of_death") or "[date of death]"
    address = (books.get("case") or {}).get("address") or "[last address]"
    sender = matter.get("client_name") or "[your name]"
    body = "\n".join([
        "Dear [name],",
        "",
        "I was given your name as our contact at Estatesearch. I am writing to open the right account for a private-client practice, and to agree how we instruct you.",
        "",
        "Our own software prepares the will, the lasting powers and the estate file. It does not hold a credit licence and it does not have a market-data feed. Where a government page or a supplier will deal with the firm direct, we use that. For everything else we want Estatesearch, rather than a separate contract with Experian, the share registrars and the insurers.",
        "",
        "We already do these ourselves:",
        "— The section 27 notice. We draft it. The firm places it on The Gazette, and can add the local newspaper in the same order.",
        "— The public insolvency register, Companies House, the Office of the Public Guardian, and wills that have already been proved.",
        "— MOT status and vehicle tax, on GOV.UK, from the registration number.",
        "— A link to the National Will Register, so the firm can search it direct.",
        "— A quarter-up share figure, once someone has typed in the lower price, the higher price and the mid price. We do not look the prices up.",
        "",
        "Please supply the rest, per matter, with no subscription if that is still how you work:",
        "— Credit and liabilities: Experian, open and closed accounts, CCJs, IVAs, bankruptcy, previous names and addresses.",
        "— Financial Profile Standard and Premium, including the notices you send to banks, pension firms and insurers, and the replies.",
        "— Will search and the missing will service.",
        "— Share valuation on the HMRC basis, verification, and a sale or transfer.",
        "— Vehicle valuation, including outstanding finance.",
        "— The identity and anti-money-laundering check on the premium search.",
        "— An overseas profile, the high-net-worth bolt-on, and the digital-assets search.",
        "— The insurances: unoccupied property, a missing will, no section 27 notice, a missing beneficiary, early distribution, and a lost share certificate.",
        "— Will-bank management, if a firm wants deaths and address changes reported back.",
        "",
        "Could you confirm:",
        "1. That a solicitor’s practice can open an account and be invoiced for each search.",
        "2. What you need on each estate before you will start. I expect the full name, the date of death, the last address, and any National Insurance number or date of birth we hold.",
        "3. Whether you have an API, or another secure way for software to send an instruction and receive the report. If not, we will keep the order in your portal and upload the PDF you send.",
        "4. Who should receive instructions, if it is not you.",
        "5. Your current prices, including VAT, and whether a software firm is billed on the same list as a law firm.",
        "",
        "We will not tell a client that a search has been run until your report is on the file.",
        "",
        "As an example of an instruction, not an order yet:",
        f"Estate of {estate}, died {died}, late of {address}.",
        "Please say which search you would recommend, and what else you need from us.",
        "",
        "Yours sincerely,",
        sender,
        "",
        "If this does not reach you, your published desk is helpdesk@estatesearch.co.uk and 0330 900 1700.",
    ])
    return {"title": f"Email to Estatesearch — estate of {estate}", "body": body}


def account_xlsx(matter: dict, accounts: dict) -> bytes:
    """Excel workbook of the estate account. One sheet for each part."""
    step = accounts["step"]
    cap = step["capital_totals"]
    cash = step["cash"]
    estate = matter.get("deceased_name") or matter.get("title") or "Estate"
    capital_rows = [["Item", "Holder", "At death", "Change", "Income", "Costs"]]
    for row in step["capital"]:
        capital_rows.append([row["name"], row.get("holder") or "", row["at_death"], row["movement"], row["income"], row["costs"]])
    capital_rows += [
        ["At death", "", cap["at_death"], "", "", ""],
        ["Gains", "", cap["gains"], "", "", ""],
        ["Losses", "", cap["losses"], "", "", ""],
        ["Debts", "", cap["debts"], "", "", ""],
        ["Funeral", "", cap["funeral"], "", "", ""],
        ["Tax", "", cap["tax"], "", "", ""],
        ["Specific gifts", "", cap["legacies"], "", "", ""],
        ["Balance of capital", "", cap["balance"], "", "", ""],
    ]
    people = [["Person", "Entitled", "Paid", "Still due"]]
    for person in step["distribution"]:
        people.append([person["name"], person["entitlement"], person["paid"], person["due"]])
    outside = [["Item", "Value", "Why"]] + [[row["name"], row["value"], row["why"]] for row in step["outside"]]
    summary = [
        ["Estate", estate],
        ["Income received after death", step["income_total"]],
        ["Cash in", cash["receipts"]],
        ["Cash out", cash["payments"]],
        ["Cash that should be in hand", cash["in_hand"]],
        ["Left to share", accounts["totals"]["expected_net"]],
    ]
    return xlsx_bytes([("Summary", summary), ("Capital", capital_rows), ("Distribution", people), ("Outside the estate", outside)])


def xlsx_bytes(sheets: list[tuple[str, list]]) -> bytes:
    import io
    import zipfile
    from xml.sax.saxutils import escape

    def col(n: int) -> str:
        out = ""
        while n:
            n, rem = divmod(n - 1, 26)
            out = chr(65 + rem) + out
        return out

    def cell(ref: str, value) -> str:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        text = "" if value is None else str(value)
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'

    def sheet_xml(rows: list) -> str:
        body = []
        for r_i, row in enumerate(rows, 1):
            bits = "".join(cell(f"{col(c)}{r_i}", value) for c, value in enumerate(row, 1))
            body.append(f'<row r="{r_i}">{bits}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(body)}</sheetData></worksheet>'
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(sheets) + 1)
            ) + '</Types>'
        ))
        book.writestr("_rels/.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ))
        safe = []
        banned = set(':\\/?*[]')
        for i, (name, _rows) in enumerate(sheets, 1):
            clean = "".join(ch for ch in name if ch not in banned)[:31] or f"Sheet{i}"
            safe.append(clean)
        book.writestr("xl/workbook.xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(safe, 1))
            + '</sheets></workbook>'
        ))
        book.writestr("xl/_rels/workbook.xml.rels", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            ) + '</Relationships>'
        ))
        for i, (_name, rows) in enumerate(sheets, 1):
            book.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))
    return buf.getvalue()
