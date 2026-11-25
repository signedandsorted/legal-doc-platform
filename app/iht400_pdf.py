"""Fill HMRC's own IHT400. We do not redraw the form.

The PDF in app/forms is the fillable file from GOV.UK. When HMRC publish a new one,
replace that file (or call refresh_official_form). Fields are matched by name and,
if HMRC rename a field, by the tooltip. Boxes that are printed but not fields,
including several asset lines on the current form, are written on the additional
information page instead of being left only in someone's head.
"""
import re
from io import BytesIO
from pathlib import Path

import httpx
from pypdf import PdfReader, PdfWriter

FORM_PATH = Path(__file__).resolve().parent / "forms" / "iht400-fillable.pdf"
SOURCE_PAGE = "https://www.gov.uk/government/publications/inheritance-tax-inheritance-tax-account-iht400"
SOURCE_NOTE = FORM_PATH.with_suffix(".url")


def refresh_official_form() -> str:
    """Download the IHT400 currently linked from GOV.UK and store it. Returns the URL used."""
    page = httpx.get(SOURCE_PAGE, timeout=30, follow_redirects=True)
    page.raise_for_status()
    match = re.search(r"https://assets\.publishing\.service\.gov\.uk/[^\"']+iht400-fillable\.pdf", page.text)
    if not match:
        raise RuntimeError("GOV.UK did not link a fillable IHT400")
    url = match.group(0)
    download = httpx.get(url, timeout=60, follow_redirects=True)
    download.raise_for_status()
    if not download.content.startswith(b"%PDF"):
        raise RuntimeError("The download was not a PDF")
    FORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    FORM_PATH.write_bytes(download.content)
    SOURCE_NOTE.write_text(url)
    return url


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _split_name(full: str) -> tuple[str, str]:
    parts = [p for p in (full or "").split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def _date_parts(iso: str) -> tuple[str, str, str]:
    bits = (iso or "").split("-")
    if len(bits) != 3:
        return "", "", ""
    year, month, day = bits
    return day, month, year


def _by_tooltip(fields: dict, tooltip: str) -> str | None:
    for name, meta in fields.items():
        if str(meta.get("/TU") or "").startswith(tooltip):
            return name
    return None


def _put(values: dict, fields: dict, name: str, tooltip: str, value: str) -> None:
    if not value:
        return
    key = name if name in fields else _by_tooltip(fields, tooltip)
    if key:
        values[key] = value


def fill_iht400(matter: dict, compiled: dict) -> tuple[bytes, list[str]]:
    if not FORM_PATH.exists():
        raise FileNotFoundError("The official IHT400 file is not on the server")
    reader = PdfReader(str(FORM_PATH))
    fields = reader.get_fields() or {}
    books = compiled["books"]
    case = books["case"]
    figures = compiled["figures"]
    fore, sur = _split_name(matter.get("deceased_name") or "")
    day, month, year = _date_parts(matter.get("date_of_death") or "")
    bday, bmonth, byear = _date_parts(case.get("date_of_birth") or "")
    sole = [ln for ln in books["lines"] if ln["side"] == "asset" and ln["ownership"] != "joint_tenants" and not ln["abroad"]]
    banks = sum(ln["value"] for ln in sole if ln["kind"] == "bank")
    houses = sum(ln["value"] for ln in sole if ln["kind"] == "property")
    shares = sum(ln["value"] for ln in sole if ln["kind"] == "shares")
    goods = sum(ln["value"] for ln in sole if ln["kind"] == "goods")
    funeral = sum(ln["value"] for ln in books["lines"] if ln.get("funeral"))
    debts = [ln for ln in books["lines"] if ln["side"] == "debt" and not ln.get("funeral") and not ln.get("joint")]
    notes = [
        "Figures taken from the firm's list. A solicitor checks them before this form is posted.",
        f"Gross for Inheritance Tax {_money(figures['gross_iht'])}.",
        f"Net for Inheritance Tax {_money(figures['net_iht'])}.",
        f"Tax estimate {_money(figures['tax'])}. This is not HMRC's own arithmetic.",
    ]
    if houses:
        notes.append(f"Box 51, deceased's residence, {_money(houses)}. The box on page 7 of this file is not a field, so it is written here.")
    if banks:
        notes.append(f"Box 52, bank and building society accounts in the sole name, {_money(banks)}.")
    if goods:
        notes.append(f"Box 55, household and personal goods, {_money(goods)}.")
    if shares:
        notes.append(f"Box 63, listed stocks and shares, {_money(shares)}.")
    for ln in sole:
        notes.append(f"{ln['name']}" + (f", {ln['holder']}" if ln["holder"] else "") + f": {_money(ln['value'])}.")
    values: dict[str, str] = {}
    _put(values, fields, "IHT400_01_01", "Deceased's name: Surname", sur)
    _put(values, fields, "IHT400_01_02", "Deceased's name: Surname", fore)
    _put(values, fields, "IHT400_02_01", "Date of death  DD", day)
    _put(values, fields, "IHT400_02_02", "Month of death  MM", month)
    _put(values, fields, "IHT400_02_03", "Year of death YYYY", year)
    _put(values, fields, "IHT400_05_01", "Deceased's date of birth  DD", bday)
    _put(values, fields, "IHT400_05_02", "Deceased's month of birth MM", bmonth)
    _put(values, fields, "IHT400_05_03", "Deceased's year of birth", byear)
    _put(values, fields, "IHT400_11", "Deceased's last known permanent address", case.get("address") or "")
    _put(values, fields, "IHT400_17_01", "Name and address of the firm or person dealing with the estate", matter.get("client_name") or "")
    _put(values, fields, "Capacity", "Please state your capacity", case.get("applicant_role") or "")
    if funeral:
        _put(values, fields, "IHT400_96_01", "Funeral costs", _money(funeral))
        _put(values, fields, "IHT400_96", "Total cost of funeral", _money(funeral))
    if debts:
        _put(values, fields, "IHT400_97_01", "Creditor's name and description of the liability", debts[0]["name"])
        _put(values, fields, "IHT400_97_02", "Amount", _money(debts[0]["value"]))
    _put(values, fields, "IHT400_164", "Additional information", " ".join(notes)[:1800])
    will = case.get("has_will") or ""
    if will.startswith("Yes"):
        values["IHT400_24"] = "/Yes"
    elif will == "No":
        values["IHT400_24"] = "/No"
    if banks:
        values["IHT400_33"] = "/Yes"
        values["IHT400_IHT406"] = "/IHT406"
    if houses:
        values["IHT400_32"] = "/Yes"
        values["IHT400_IHT405"] = "/IHT405"
    if goods:
        values["IHT400_34"] = "/Yes"
        values["IHT400_IHT407"] = "/IHT407"
    if shares:
        values["IHT400_38"] = "/Yes"
        values["IHT400_IHT411"] = "/IHT411"
    writer = PdfWriter()
    writer.append(reader)
    known = {k: v for k, v in values.items() if k in fields}
    missing = [k for k in values if k not in fields]
    writer.update_page_form_field_values(None, known, auto_regenerate=False)
    out = BytesIO()
    writer.write(out)
    return out.getvalue(), missing
