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
    {"id": "shares", "place": "Shares and funds", "ask": "Check dividend letters, brokers and investment platforms.", "url": "", "url_title": ""},
    {"id": "insurance", "place": "Life insurance", "ask": "Ask any insurer named in the papers, and the employer if it may be a death-in-service policy.", "url": "", "url_title": ""},
    {"id": "employer", "place": "Last employer", "ask": "Ask about unpaid pay, shares and any lump sum.", "url": "", "url_title": ""},
    {"id": "benefits", "place": "State Pension and benefits", "ask": "Tell Us Once can notify several government departments from one report.", "url": "https://www.gov.uk/tell-us-once", "url_title": "Tell Us Once"},
    {"id": "cards", "place": "Credit cards, loans and catalogues", "ask": "These are usually debts. A statement in the post is the usual clue.", "url": "", "url_title": ""},
    {"id": "digital", "place": "PayPal and other online balances", "ask": "Search email for payment receipts, then ask the company with the death certificate.", "url": "", "url_title": ""},
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
