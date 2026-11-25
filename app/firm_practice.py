"""What a private-client firm records before it acts. This is the firm's own file, not a check bought from a data company."""

HELD = ("Not known yet", "With the firm", "With the client", "At a bank", "At the Principal Registry", "Not a will")
IDENTITY = ("Not seen", "Seen", "Certified copy on the file")
RISK = ("Ordinary", "Higher")


def _date(value) -> str:
    text = str(value or "").strip()[:10]
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    return ""


def clean_practice(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    checked = str(raw.get("conflict_checked_on") or "").strip()[:10]
    if len(checked) != 10 or checked[4] != "-":
        checked = ""
    return {
        "identity": raw.get("identity") if raw.get("identity") in IDENTITY else "Not seen",
        "id_provider": str(raw.get("id_provider") or "").strip()[:80],
        "id_reference": str(raw.get("id_reference") or "").strip()[:80],
        "id_checked_on": _date(raw.get("id_checked_on")),
        "source": str(raw.get("source") or "").strip()[:400],
        "risk": raw.get("risk") if raw.get("risk") in RISK else "Ordinary",
        "risk_note": str(raw.get("risk_note") or "").strip()[:400],
        "will_held": raw.get("will_held") if raw.get("will_held") in HELD else "Not known yet",
        "will_ref": str(raw.get("will_ref") or "").strip()[:80],
        "conflict_checked_on": checked,
        "conflict_note": str(raw.get("conflict_note") or "").strip()[:400],
    }


def _same(left: str, right: str) -> bool:
    a, b = (left or "").casefold().strip(), (right or "").casefold().strip()
    if len(a) < 4 or len(b) < 4:
        return False
    return a == b or (len(a) >= 8 and a in b) or (len(b) >= 8 and b in a)


def conflicts(matter: dict, others: list[dict]) -> list[dict]:
    """Other matters that already use this client or this person who died."""
    names = [matter.get("client_name") or "", matter.get("deceased_name") or ""]
    found = []
    for other in others:
        if other["id"] == matter["id"]:
            continue
        theirs = [other.get("client_name") or "", other.get("deceased_name") or ""]
        if any(_same(name, theirs_name) for name in names for theirs_name in theirs):
            found.append({
                "id": other["id"],
                "title": other.get("title") or "",
                "kind": other.get("kind") or "",
                "client_name": other.get("client_name") or "",
                "deceased_name": other.get("deceased_name") or "",
            })
    return found[:20]


def search_names(query: str, matter: dict, others: list[dict]) -> list[dict]:
    """Matters on this desk whose title, client or person who died contains the words typed."""
    parts = [part.strip() for part in query.replace(";", ",").split(",") if len(part.strip()) >= 3]
    if not parts:
        return conflicts(matter, others)
    found = []
    for other in others:
        if other["id"] == matter["id"]:
            continue
        hay = " ".join([other.get("title") or "", other.get("client_name") or "", other.get("deceased_name") or ""]).casefold()
        if any(part.casefold() in hay for part in parts):
            found.append({
                "id": other["id"],
                "title": other.get("title") or "",
                "kind": other.get("kind") or "",
                "client_name": other.get("client_name") or "",
                "deceased_name": other.get("deceased_name") or "",
            })
    return found[:20]
