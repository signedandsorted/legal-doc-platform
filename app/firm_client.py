"""The firm's client account, kept apart from office money, and the three-way check.

Every receipt and payment is on a client. The cash book is those movements.
The ledgers are the same movements added up by matter. The third figure is the
balance on the bank statement, after unpresented cheques and money paid in
that the bank has not credited yet. The three should match. This desk does
not pay the bank.
"""
from uuid import uuid4

KINDS = ("in", "out", "transfer")


def _num(value) -> float:
    try:
        number = round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0
    return min(1_000_000_000.0, max(0.0, number))


def _date(value) -> str:
    text = str(value or "").strip()[:10]
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    return ""


def clean_client_account(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    entries = []
    for item in (raw.get("entries") or [])[:2000]:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind") if item.get("kind") in KINDS else ""
        amount = _num(item.get("amount"))
        if not kind or amount <= 0:
            continue
        entries.append({
            "id": str(item.get("id") or "")[:12] or uuid4().hex[:8],
            "kind": kind,
            "on": _date(item.get("on")),
            "matter_id": str(item.get("matter_id") or "").strip()[:36],
            "what": str(item.get("what") or "").strip()[:200] or "Client money",
            "amount": amount,
            "reference": str(item.get("reference") or "").strip()[:80],
        })
    statement = raw.get("statement") if isinstance(raw.get("statement"), dict) else {}
    return {
        "entries": entries,
        "statement": {
            "on": _date(statement.get("on")),
            "balance": _num(statement.get("balance")),
            "unpresented": _num(statement.get("unpresented")),
            "outstanding": _num(statement.get("outstanding")),
        },
        "signoffs": _history(raw.get("signoffs")),
        "breaches": _history(raw.get("breaches")),
    }


def _history(rows) -> list[dict]:
    kept = []
    for item in (rows or [])[:200]:
        if not isinstance(item, dict) or not item.get("at") or not item.get("by"):
            continue
        kept.append({
            "at": str(item.get("at"))[:40],
            "by": str(item.get("by"))[:120],
            "cash_book": _num(item.get("cash_book")),
            "ledger_total": _num(item.get("ledger_total")),
            "adjusted_bank": _num(item.get("adjusted_bank")),
            "statement_on": _date(item.get("statement_on")),
            "note": str(item.get("note") or "")[:400],
        })
    return kept


def matter_balance(book: dict, matter_id: str) -> float:
    total = 0.0
    for row in book.get("entries") or []:
        if row.get("matter_id") != matter_id:
            continue
        total += row["amount"] if row["kind"] == "in" else -row["amount"]
    return round(total, 2)


def post_entry(book: dict, raw: dict, known_matters: set[str]) -> dict:
    book = clean_client_account(book)
    kind = raw.get("kind") if raw.get("kind") in KINDS else ""
    amount = _num(raw.get("amount"))
    matter_id = str(raw.get("matter_id") or "").strip()[:36]
    if kind not in KINDS or amount <= 0:
        raise ValueError("Enter the amount and whether it is money in, money out, or a transfer to office")
    if matter_id and matter_id not in known_matters:
        raise ValueError("Choose a matter on this desk")
    if kind == "in" and not matter_id:
        raise ValueError("Client money has to be entered against a matter")
    if kind in ("out", "transfer"):
        if not matter_id:
            raise ValueError("A payment has to name the matter")
        if round(matter_balance(book, matter_id) - amount, 2) < 0:
            raise ValueError("That would take this client's balance below zero")
    book["entries"].append({
        "id": uuid4().hex[:8],
        "kind": kind,
        "on": _date(raw.get("on")),
        "matter_id": matter_id,
        "what": str(raw.get("what") or "").strip()[:200] or "Client money",
        "amount": amount,
        "reference": str(raw.get("reference") or "").strip()[:80],
    })
    return book


def set_statement(book: dict, raw: dict) -> dict:
    book = clean_client_account(book)
    book["statement"] = {
        "on": _date(raw.get("on")),
        "balance": _num(raw.get("balance")),
        "unpresented": _num(raw.get("unpresented")),
        "outstanding": _num(raw.get("outstanding")),
    }
    return book


def reconcile(book: dict, titles: dict[str, str]) -> dict:
    book = clean_client_account(book)
    cash = 0.0
    by_matter: dict[str, float] = {}
    for row in book["entries"]:
        signed = row["amount"] if row["kind"] == "in" else -row["amount"]
        cash += signed
        key = row["matter_id"] or ""
        by_matter[key] = round(by_matter.get(key, 0.0) + signed, 2)
    cash = round(cash, 2)
    ledgers = [{"matter_id": key, "title": titles.get(key) or "Matter", "balance": balance} for key, balance in by_matter.items() if key]
    ledger_total = round(sum(row["balance"] for row in ledgers), 2)
    statement = book["statement"]
    adjusted = round(statement["balance"] + statement["outstanding"] - statement["unpresented"], 2)
    return {
        "cash_book": cash,
        "ledger_total": ledger_total,
        "statement": statement["balance"],
        "statement_on": statement["on"],
        "unpresented": statement["unpresented"],
        "outstanding": statement["outstanding"],
        "adjusted_bank": adjusted,
        "books_agree": abs(cash - ledger_total) < 0.01,
        "bank_agrees": abs(adjusted - cash) < 0.01,
        "agrees": abs(cash - ledger_total) < 0.01 and abs(adjusted - cash) < 0.01,
        "ledgers": ledgers,
        "entries": list(reversed(book["entries"][-40:])),
        "signoffs": book.get("signoffs") or [],
        "breaches": book.get("breaches") or [],
    }


def _stamp(view: dict, by: str, at: str, note: str) -> dict:
    return {
        "at": str(at)[:40],
        "by": str(by)[:120],
        "cash_book": view["cash_book"],
        "ledger_total": view["ledger_total"],
        "adjusted_bank": view["adjusted_bank"],
        "statement_on": view["statement_on"],
        "note": str(note or "").strip()[:400],
    }


def sign_off(book: dict, titles: dict[str, str], by: str, at: str, note: str) -> dict:
    book = clean_client_account(book)
    view = reconcile(book, titles)
    if not view["agrees"]:
        raise ValueError("The cash book, the client ledgers and the bank statement do not agree, so this cannot be signed off")
    book["signoffs"].append(_stamp(view, by, at, note))
    return book


def record_breach(book: dict, titles: dict[str, str], by: str, at: str, note: str) -> dict:
    book = clean_client_account(book)
    text = str(note or "").strip()
    if len(text) < 3:
        raise ValueError("Say what went wrong")
    view = reconcile(book, titles)
    book["breaches"].append(_stamp(view, by, at, text))
    return book


def residuals(ledgers: list[dict], status_by_id: dict[str, str]) -> list[dict]:
    """Client money still held on a matter the firm has closed."""
    found = []
    for row in ledgers:
        if status_by_id.get(row["matter_id"]) == "closed" and abs(row["balance"]) >= 0.01:
            found.append(row)
    return found
