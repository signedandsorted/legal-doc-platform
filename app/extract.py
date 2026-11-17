"""Read text from uploaded documents and suggest answers. Heuristic and local (no paid APIs).
Suggestions are only offered to the user; nothing is filled in without them choosing it."""
import io
import re
import zipfile
from xml.etree import ElementTree

MAX_TEXT = 200_000
NAME = r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\s+(\d{{4}})\b")
MONEY_RE = re.compile(r"([A-Za-z][A-Za-z &'\-]{2,40}?)[\s:\-]*£\s?([\d,]+(?:\.\d{2})?)")
STOP = {"The", "This", "My", "Will", "Testament", "Last", "Power", "Attorney", "Lasting", "Signed", "Dated", "Witness", "Executor", "Executors", "Trustees", "Trustee"}


def extract_text(filename: str, content_type: str, data: bytes) -> tuple[str, str]:
    """Returns (text, how). Images are stored but not OCR'd on the free plan."""
    name = filename.lower()
    try:
        if name.endswith(".pdf") or content_type == "application/pdf":
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:60])
            return text[:MAX_TEXT], "pdf" if text.strip() else "scanned-pdf"
        if name.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                root = ElementTree.fromstring(z.read("word/document.xml"))
            paras = ["".join(t.text or "" for t in p.iter() if t.tag.endswith("}t")) for p in root.iter() if p.tag.endswith("}p")]
            return "\n".join(paras)[:MAX_TEXT], "docx"
        if name.endswith(".txt") or content_type.startswith("text/"):
            return data.decode("utf-8", "replace")[:MAX_TEXT], "text"
    except Exception:  # unreadable file: keep it for the solicitor
        return "", "unreadable"
    return "", "image"


def detect_kind(text: str) -> str | None:
    t = text.lower()
    if "enduring power of attorney" in t:
        return "Enduring power of attorney (EPA)"
    if "lasting power of attorney" in t or re.search(r"\blp1[fh]\b", t):
        return "Existing LPA"
    if "codicil" in t[:2000]:
        return "Codicil"
    if "last will" in t or "testament" in t or re.search(r"\bthis is the (last )?will\b", t):
        return "Old will"
    if "entry of death" in t or "death certificate" in t:
        return "Death certificate"
    return None


def _iso(m: re.Match) -> str:
    month = MONTHS.split("|").index(m.group(2)) + 1
    return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"


def _clean(name: str) -> str | None:
    words = [w for w in name.split() if w not in STOP]
    return " ".join(words) if len(words) >= 2 else None


def _names_after(pattern: str, text: str) -> list[str]:
    out = []
    for m in re.finditer(pattern + r"\s+" + NAME, text):
        n = _clean(m.group(1))
        if n and n not in out:
            out.append(n)
    return out


def suggest(service_id: str, text: str, upload_id: str, filename: str) -> list[dict]:
    if not text.strip():
        return []
    flat = " ".join(text.split())
    s = []

    def add(label, step, field, value, mode="set"):
        s.append({"id": f"{upload_id}:{len(s)}", "upload_id": upload_id, "source": filename, "label": label, "step": step, "field": field, "value": value, "mode": mode})

    maker = re.search(r"\bI,?\s+" + NAME + r",?\s+of\b", flat)
    appointed = _names_after(r"\bI appoint(?: my \w+)?", flat)
    executors = [n for n in appointed if re.search(re.escape(n) + r"[^.]{0,120}executor", flat, re.I)] or appointed
    guardians = [n for n in appointed if re.search(re.escape(n) + r"[^.]{0,120}guardian", flat, re.I)]
    attorneys = []
    for m in re.finditer(r"\b[Aa]ttorneys?(?: (?:is|are))?[:\s]+((?:[A-Z][a-zA-Z'\-]+(?:\s+and\s+|,\s*|\s+)?){2,12})", flat):
        for part in re.split(r",\s*|\s+and\s+", m.group(1)):
            n = _clean(part.strip())
            if n and n not in attorneys:
                attorneys.append(n)
    gifts_to = _names_after(r"\bto my (?:wife|husband|partner|son|daughter|brother|sister|mother|father|friend|grandson|granddaughter|nephew|niece|civil partner)", flat)
    if service_id == "will":
        if maker:
            add(f"Your name in the old will: {maker.group(1)}", "about_you", "full_name", maker.group(1))
        for n in [x for x in executors if x not in guardians][:4]:
            add(f"Executor in the old will: {n}", "executors", "executors", {"full_name": n}, "append")
        for n in guardians[:2]:
            add(f"Guardian in the old will: {n}", "family", "guardians", {"full_name": n}, "append")
        for n in gifts_to[:6]:
            add(f"Beneficiary in the old will: {n}", "residue", "residuary_beneficiaries", {"full_name": n, "share": "1"}, "append")
        d = DATE_RE.search(flat[-3000:]) or DATE_RE.search(flat)
        if d:
            add(f"The old will looks dated {d.group(0)}. Your new will revokes it once signed.", None, None, None, "note")
    elif service_id.startswith("lpa_"):
        if maker:
            add(f"Donor name: {maker.group(1)}", "donor", "full_name", maker.group(1))
        for n in (attorneys or appointed)[:4]:
            add(f"Attorney in your existing document: {n}", "attorneys", "attorneys", {"full_name": n}, "append")
        if "enduring power of attorney" in flat.lower():
            add("This looks like an enduring power of attorney (EPA). It can still be used for financial decisions once registered. A solicitor will advise whether you also need an LPA.", None, None, None, "note")
    elif service_id == "probate":
        if maker:
            add(f"Name of the person who died (from the will): {maker.group(1)}", "deceased", "full_name", maker.group(1))
        dm = re.search(r"date (?:and place )?of death[:\s]+" + DATE_RE.pattern, flat, re.I)
        if dm:
            add(f"Date of death: {dm.group(1)} {dm.group(2)} {dm.group(3)}", "deceased", "date_of_death", f"{int(dm.group(3)):04d}-{MONTHS.split('|').index(dm.group(2)) + 1:02d}-{int(dm.group(1)):02d}")
        for n in executors[:4]:
            add(f"Executor named in the will: {n}", None, None, None, "note")
        for m in list(MONEY_RE.finditer(flat))[:8]:
            desc = m.group(1).strip().rstrip(":-").strip()
            value = m.group(2).replace(",", "")
            add(f"{desc}: £{m.group(2)}", "estate", "assets", {"description": f"{desc} ({filename})", "value": value}, "append")
    return s
