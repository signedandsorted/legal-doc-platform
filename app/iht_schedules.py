"""Choose the extra Inheritance Tax schedules from the figures, and fill HMRC's own files.

The choice is a rule, not a guess. A house in one name asks for IHT405. A bank account asks for IHT406.
Schedules whose official file we do not hold are still named, so nobody thinks they were forgotten.
"""
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DIR = Path(__file__).resolve().parent / "forms" / "schedules"

# Description column, amount column. None means the schedule is named and the file is filled
# with the person's details only, because the rows are a claim rather than a list we hold.
ROWS = {
    "IHT405": ("B - Full address or description", "H - Open market value at the date of death"),
    "IHT406": ("Name of bank or building society", "Amount held, including interest"),
    "IHT407": ("Description of item", "Open market value at date of death"),
    "IHT409": ("Name of the pension scheme or title of the personal pension policy", None),
    "IHT411": ("Description of stock", "Total value of stock"),
    "IHT404": ("Description of asset", "Value of the whole item"),
    "IHT417": ("Description of assets", "Value of assets at the date of death  £ sterling"),
}


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _parts(iso: str) -> tuple[str, str, str]:
    bits = (iso or "").split("-")
    if len(bits) != 3:
        return "", "", ""
    year, month, day = bits
    return day, month, year


def _natural(value: str):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def _sole(line: dict) -> bool:
    return line["side"] == "asset" and line["ownership"] == "sole" and not line["abroad"]


def choose_schedules(books: dict, worked: dict) -> list[dict]:
    """The schedules this estate needs. Each one says why."""
    if worked.get("excepted"):
        return []
    lines = books.get("lines") or []
    chosen = []

    def add(code: str, why: str, rows: list[dict]) -> None:
        chosen.append({"code": code, "why": why, "rows": len(rows), "ready": (DIR / f"{code}.pdf").exists()})

    houses = [ln for ln in lines if _sole(ln) and ln["kind"] == "property"]
    banks = [ln for ln in lines if _sole(ln) and ln["kind"] == "bank"]
    goods = [ln for ln in lines if _sole(ln) and ln["kind"] == "goods"]
    shares = [ln for ln in lines if _sole(ln) and ln["kind"] == "shares"]
    pensions = [ln for ln in lines if _sole(ln) and ln["kind"] == "pension"]
    joint = [ln for ln in lines if ln["side"] == "asset" and ln["ownership"] != "sole" and not ln["abroad"]]
    abroad = [ln for ln in lines if ln["side"] == "asset" and ln["abroad"]]
    debts = [ln for ln in lines if ln["side"] == "debt" and not ln.get("funeral")]
    if houses:
        add("IHT405", "There is a house or land in the sole name.", houses)
    if banks:
        add("IHT406", "There is a bank or building society account in the sole name.", banks)
    if goods:
        add("IHT407", "There are household or personal goods.", goods)
    if shares:
        add("IHT411", "There are stocks or shares.", shares)
    if pensions:
        add("IHT409", "There is a pension or policy paid to the estate.", pensions)
    if joint:
        add("IHT404", "Something was owned with another person.", joint)
    if abroad:
        add("IHT417", "Something is outside the UK.", abroad)
    if debts:
        add("IHT419", "There are debts. This form splits them by type, so the rows are not guessed.", [])
    if (books.get("case") or {}).get("gifts_7_years"):
        add("IHT403", "Gifts in the 7 years were entered as a total. Each gift still has to be listed.", [])
    known = {code for code, _why in worked.get("forms") or []}
    if "IHT402" in known:
        add("IHT402", "A transfer of the unused nil rate band was indicated.", [])
    if "IHT435" in known:
        add("IHT435", "The residence nil rate band was used. HMRC's file for this claim is not stored here yet.", [])
    if "IHT436" in known:
        add("IHT436", "A transfer of the unused residence nil rate band was indicated. That file is not stored here yet.", [])
    return chosen


def _fill_identity(values: dict, fields: dict, matter: dict) -> None:
    name = (matter.get("deceased_name") or "")[:80]
    for key, meta in fields.items():
        tip = " ".join(str(meta.get("/TU") or "").split()).lower()
        if meta.get("/FT") == "/Tx" and tip in ("name of deceased", "name of the deceased") and name:
            values[key] = name
            break
    day, month, year = _parts(matter.get("date_of_death") or "")
    if not day:
        return
    digits = list(day + month + year)
    grouped: dict[str, list[str]] = {}
    for key, meta in fields.items():
        tip = " ".join(str(meta.get("/TU") or "").split())
        if meta.get("/FT") == "/Tx" and "date of death" in tip.lower() and "dd mm yyyy" in tip.lower():
            grouped.setdefault(tip, []).append(key)
    for keys in grouped.values():
        ordered = sorted(keys, key=_natural)
        if len(ordered) >= 8:
            for char, key in zip(digits, ordered[:8]):
                values[key] = char
            return
    def boxes(token: str) -> list[str]:
        found = []
        for key, meta in fields.items():
            tip = " ".join(str(meta.get("/TU") or "").split())
            if meta.get("/FT") == "/Tx" and tip.lower().endswith(token.lower()):
                found.append(key)
        return sorted(found, key=_natural)
    dd, mm, yy = boxes("DD"), boxes("MM"), boxes("YYYY")
    for chars, keys in ((day, dd), (month, mm), (year, yy)):
        for char, key in zip(chars, keys):
            values[key] = char


def _columns(fields: dict, start: str) -> list[str]:
    keys = [key for key, meta in fields.items() if str(meta.get("/TU") or "").startswith(start) and meta.get("/FT") == "/Tx"]
    return sorted(keys, key=_natural)


def fill_schedule(code: str, matter: dict, lines: list[dict]) -> bytes | None:
    path = DIR / f"{code}.pdf"
    if not path.exists():
        return None
    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    values: dict[str, str] = {}
    _fill_identity(values, fields, matter)
    hints = ROWS.get(code)
    if hints:
        descriptions = _columns(fields, hints[0])
        amounts = _columns(fields, hints[1]) if hints[1] else []
        for index, line in enumerate(lines):
            label = line["name"] + (f", {line['holder']}" if line.get("holder") else "")
            if index < len(descriptions):
                values[descriptions[index]] = label[:120]
            if hints[1] and index < len(amounts):
                values[amounts[index]] = _money(line["value"])
    known = {key: value for key, value in values.items() if key in fields and value}
    writer = PdfWriter()
    writer.append(reader)
    if known:
        writer.update_page_form_field_values(None, known, auto_regenerate=False)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def schedule_files(matter: dict, books: dict, chosen: list[dict]) -> list[tuple[str, bytes]]:
    lines = books.get("lines") or []
    picked = {
        "IHT405": [ln for ln in lines if _sole(ln) and ln["kind"] == "property"],
        "IHT406": [ln for ln in lines if _sole(ln) and ln["kind"] == "bank"],
        "IHT407": [ln for ln in lines if _sole(ln) and ln["kind"] == "goods"],
        "IHT411": [ln for ln in lines if _sole(ln) and ln["kind"] == "shares"],
        "IHT409": [ln for ln in lines if _sole(ln) and ln["kind"] == "pension"],
        "IHT404": [ln for ln in lines if ln["side"] == "asset" and ln["ownership"] != "sole" and not ln["abroad"]],
        "IHT417": [ln for ln in lines if ln["side"] == "asset" and ln["abroad"]],
        "IHT402": [],
        "IHT403": [],
    }
    files = []
    for item in chosen:
        pdf = fill_schedule(item["code"], matter, picked.get(item["code"]) or [])
        if pdf:
            files.append((item["code"], pdf))
    return files
