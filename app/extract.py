"""Read text from uploaded documents and suggest answers. Heuristic and local (no paid APIs).
Photos and scans are read with OCR. Suggestions are only offered; nothing is filled until asked."""
import io
import re
import zipfile
from xml.etree import ElementTree

MAX_TEXT = 200_000
NAME = r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\s+(\d{{4}})\b")
MONEY_RE = re.compile(r"([A-Za-z][A-Za-z &'\-]{2,40}?)[\s:\-]*£\s?([\d,]+(?:\.\d{2})?)")
CREDIT_HINT = re.compile(r"credit report|experian|equifax|transunion|estatesearch", re.I)
_DEBT_WORDS = ("card", "loan", "mortgage", "overdraft", "finance", "hp ")
STOP = {"The", "This", "My", "Will", "Testament", "Last", "Power", "Attorney", "Lasting", "Signed", "Dated", "Witness", "Executor", "Executors", "Trustees", "Trustee"}
_ENGINE = None


def _ocr_engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_image(data: bytes) -> str:
    """Read a photo or scan. Empty string if nothing can be read."""
    from PIL import Image
    img = Image.open(io.BytesIO(data)).convert("RGB")
    short = min(img.size)
    if short < 900:
        scale = 900 / short
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.LANCZOS)
    if max(img.size) > 2500:
        scale = 2500 / max(img.size)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result, _elapsed = _ocr_engine()(buf.getvalue())
    if not result:
        return ""
    lines = [text for _box, text, score in result if text and score >= 0.5]
    return "\n".join(lines)[:MAX_TEXT]


def ocr_pdf(data: bytes) -> str:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(data)
    parts = []
    try:
        for i in range(min(len(pdf), 4)):
            page = pdf[i]
            pil = page.render(scale=2).to_pil()
            raw = io.BytesIO()
            pil.save(raw, format="PNG")
            parts.append(ocr_image(raw.getvalue()))
            page.close()
    finally:
        pdf.close()
    return "\n".join(part for part in parts if part)[:MAX_TEXT]


def extract_text(filename: str, content_type: str, data: bytes) -> tuple[str, str]:
    """Returns (text, how). how is pdf, docx, text, ocr, scanned-pdf, image or unreadable."""
    name = filename.lower()
    try:
        if name.endswith(".pdf") or content_type == "application/pdf":
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:60])
            if len(text.strip()) >= 40:
                return text[:MAX_TEXT], "pdf"
            try:
                seen = ocr_pdf(data)
            except Exception:
                seen = ""
            if len(seen.strip()) > len(text.strip()):
                return seen[:MAX_TEXT], "ocr"
            return (text[:MAX_TEXT], "pdf") if text.strip() else ("", "scanned-pdf")
        if name.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                root = ElementTree.fromstring(z.read("word/document.xml"))
            paras = ["".join(t.text or "" for t in p.iter() if t.tag.endswith("}t")) for p in root.iter() if p.tag.endswith("}p")]
            return "\n".join(paras)[:MAX_TEXT], "docx"
        if name.endswith(".txt") or (content_type or "").startswith("text/"):
            return data.decode("utf-8", "replace")[:MAX_TEXT], "text"
        if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")) or (content_type or "").startswith("image/"):
            try:
                seen = ocr_image(data)
            except Exception:
                return "", "image"
            return (seen[:MAX_TEXT], "ocr") if seen.strip() else ("", "image")
    except Exception:  # unreadable file: keep it for the solicitor
        return "", "unreadable"
    return "", "image"


def credit_hits(text: str) -> list[tuple[str, str, str]]:
    """Accounts printed on a bureau or Estatesearch report. Nothing is inferred beyond the line."""
    hits = []
    seen = set()
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line or len(line) > 180:
            continue
        money = re.search(r"(?:£|GBP\s*)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", line, re.I)
        if not money:
            money = re.search(r"\bbalance\b[^0-9£]{0,16}(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})", line, re.I)
        if not money:
            continue
        amount = money.group(1)
        who = line[:money.start()]
        who = re.sub(r"\b(balance|credit report|experian|equifax|transunion|estatesearch|reference)\b", " ", who, flags=re.I)
        who = re.sub(r"[^A-Za-z0-9&'./\- ]", " ", who)
        who = " ".join(who.split()).strip(" -")
        if len(who) < 3 or len(who) > 60 or who.lower() in seen:
            continue
        seen.add(who.lower())
        side = "debt" if any(word in who.lower() for word in _DEBT_WORDS) else "asset"
        hits.append((who, amount, side))
        if len(hits) == 12:
            break
    return hits


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
    if "credit report" in t or "experian" in t or "equifax" in t or "transunion" in t:
        return "Credit report"
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
        if CREDIT_HINT.search(flat):
            for who, amount, side in credit_hits(text):
                add(
                    f"{who}: £{amount}",
                    "estate",
                    "assets",
                    {"description": f"{who} (credit report)", "value": amount.replace(",", ""), "holder": who, "side": side},
                    "append",
                )
        else:
            for m in list(MONEY_RE.finditer(flat))[:8]:
                desc = m.group(1).strip().rstrip(":-").strip()
                value = m.group(2).replace(",", "")
                add(f"{desc}: £{m.group(2)}", "estate", "assets", {"description": f"{desc} ({filename})", "value": value}, "append")
    return s


def _same(current: dict, value: dict) -> bool:
    for key in ("full_name", "description"):
        if value.get(key) and current.get(key) == value.get(key):
            return True
    return False


def fill_from_papers(answers: dict, suggestions: list[dict]) -> tuple[dict, list[str], list[str]]:
    """Copy readable names, dates and amounts into the draft. Never overwrites an answer already typed.
    Returns (answers, filled labels, notes that were not copied)."""
    answers = {k: dict(v) if isinstance(v, dict) else v for k, v in (answers or {}).items()}
    filled, notes = [], []
    for item in suggestions:
        if item.get("mode") == "note" or not item.get("step") or not item.get("field"):
            if item.get("label"):
                notes.append(item["label"])
            continue
        section = dict(answers.get(item["step"]) or {})
        if item.get("mode") == "append":
            value = item.get("value") if isinstance(item.get("value"), dict) else {}
            current = [x for x in (section.get(item["field"]) or []) if isinstance(x, dict) and any(x.values())]
            if any(_same(x, value) for x in current):
                continue
            current.append(value)
            section[item["field"]] = current
        else:
            if section.get(item["field"]) not in (None, ""):
                continue
            section[item["field"]] = item.get("value")
        answers[item["step"]] = section
        filled.append(item.get("label") or item["field"])
    return answers, filled, notes
