"""The firm's own money on a matter: time, costs, bills and money received.

This is not the estate account and it is not a set of statutory accounts. It is what the firm has earned, billed and been paid.
"""
from uuid import uuid4

KINDS = ("time", "cost", "bill", "paid")


def _num(value) -> float:
    try:
        number = round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0
    return min(1_000_000.0, max(0.0, number))


def _date(value: str) -> str:
    text = str(value or "").strip()[:10]
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    return ""


def clean_bill(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    entries = []
    for index, item in enumerate((raw.get("entries") or [])[:200]):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind") if item.get("kind") in KINDS else "time"
        hours = _num(item.get("hours"))
        rate = _num(item.get("rate"))
        amount = _num(item.get("amount"))
        if kind == "time" and hours and rate:
            amount = round(hours * rate, 2)
        entries.append({
            "id": str(item.get("id") or "")[:12] or uuid4().hex[:8],
            "kind": kind,
            "on": _date(item.get("on")),
            "what": str(item.get("what") or "").strip()[:200] or "Work",
            "hours": hours,
            "rate": rate,
            "amount": amount,
        })
    return {"entries": entries}


def bill_summary(bill: dict) -> dict:
    entries = (bill or {}).get("entries") or []
    time = sum(row["amount"] for row in entries if row["kind"] == "time")
    costs = sum(row["amount"] for row in entries if row["kind"] == "cost")
    billed = sum(row["amount"] for row in entries if row["kind"] == "bill")
    paid = sum(row["amount"] for row in entries if row["kind"] == "paid")
    return {
        "time": round(time, 2),
        "costs": round(costs, 2),
        "unbilled": round(time + costs - billed, 2),
        "billed": round(billed, 2),
        "paid": round(paid, 2),
        "outstanding": round(billed - paid, 2),
    }
