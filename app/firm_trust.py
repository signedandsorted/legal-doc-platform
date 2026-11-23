"""A trust account, and a deputy's record of the person's money. Neither is filed anywhere from here."""
from uuid import uuid4


def _num(value) -> float:
    try:
        number = round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0
    return min(100_000_000.0, max(0.0, number))


def _lines(raw, pots) -> list[dict]:
    lines = []
    for item in (raw or [])[:200]:
        if not isinstance(item, dict):
            continue
        pot = item.get("pot") if item.get("pot") in pots else pots[0]
        lines.append({
            "id": str(item.get("id") or "")[:12] or uuid4().hex[:8],
            "name": str(item.get("name") or "").strip()[:160] or "Item",
            "pot": pot,
            "out": item.get("out") in (True, "Yes", "yes", "on"),
            "amount": _num(item.get("amount")),
        })
    return lines


def _balance(lines: list[dict], pot: str) -> dict:
    inn = sum(row["amount"] for row in lines if row["pot"] == pot and not row["out"])
    out = sum(row["amount"] for row in lines if row["pot"] == pot and row["out"])
    return {"in": round(inn, 2), "out": round(out, 2), "balance": round(inn - out, 2)}


def clean_trust(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    lines = _lines(raw.get("lines"), ("capital", "income"))
    return {
        "name": str(raw.get("name") or "").strip()[:160],
        "trustees": str(raw.get("trustees") or "").strip()[:400],
        "lines": lines,
        "capital": _balance(lines, "capital"),
        "income": _balance(lines, "income"),
    }


def clean_deputy(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    lines = _lines(raw.get("lines"), ("money",))
    balance = _balance(lines, "money")
    return {
        "person": str(raw.get("person") or "").strip()[:160],
        "order_date": str(raw.get("order_date") or "").strip()[:10],
        "lines": lines,
        "money": balance,
    }
