from datetime import date

DRAFT_NOTICE = "DRAFT FOR SOLICITOR REVIEW. This document has not been checked by a solicitor and must not be signed or sent until it has."


def visible(field: dict, container: dict) -> bool:
    cond = field.get("show_if")
    if not cond:
        return True
    return (container or {}).get(cond["field"]) in cond["in"]


def missing_in(field: dict, value, where: str, container: dict) -> list[str]:
    if not visible(field, container):
        return []
    label = f"{where}: {field['label']}"
    if field["type"] == "list":
        items = value or []
        out = [f"{label} (at least {field['min']})"] if len(items) < field.get("min", 0) else []
        for i, item in enumerate(items, 1):
            for sub in field["fields"]:
                out += missing_in(sub, (item or {}).get(sub["name"]), f"{label} {i}", item or {})
        return out
    if field["type"] == "group":
        return [m for sub in field["fields"] for m in missing_in(sub, (value or {}).get(sub["name"]), label, value or {})]
    if field["type"] == "checkbox":
        return [label] if field.get("required") and value is not True else []
    if field.get("required") and (value is None or str(value).strip() == ""):
        return [label]
    return []


def names(people) -> str:
    ns = [p.get("full_name", "").strip() for p in people or [] if p and p.get("full_name")]
    if len(ns) < 2:
        return "".join(ns)
    return ", ".join(ns[:-1]) + " and " + ns[-1]


def person(p: dict) -> str:
    parts = [(p or {}).get("full_name", "")]
    if (p or {}).get("address"):
        parts.append("of " + " ".join(p["address"].split()))
    return " ".join(parts)


def money(value) -> str:
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def age_on(dob: str, on: date | None = None) -> int | None:
    try:
        b = date.fromisoformat(str(dob))
    except ValueError:
        return None
    on = on or date.today()
    return on.year - b.year - ((on.month, on.day) < (b.month, b.day))


def norm(name: str) -> str:
    return " ".join(str(name or "").lower().replace(".", " ").split())


def issue(level: str, message: str) -> dict:
    return {"level": level, "message": message}
