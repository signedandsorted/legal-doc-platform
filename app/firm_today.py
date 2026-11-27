"""The practice home: what is open today, and one search across the files.

Tasks and appointments sit on the matter. The bank figure is whatever was typed
from the statement. This is not a feed from the bank.
"""
from uuid import uuid4


def _date(value) -> str:
    text = str(value or "").strip()[:10]
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    return ""


def clean_work(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    tasks, appointments = [], []
    for item in (raw.get("tasks") or [])[:200]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:160]
        if not title:
            continue
        tasks.append({
            "id": str(item.get("id") or "")[:12] or uuid4().hex[:8],
            "title": title,
            "due": _date(item.get("due")),
            "who": str(item.get("who") or "").strip()[:120],
            "done": item.get("done") in (True, "Yes", "yes", "on"),
        })
    for item in (raw.get("appointments") or [])[:200]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:160]
        if not title:
            continue
        appointments.append({
            "id": str(item.get("id") or "")[:12] or uuid4().hex[:8],
            "title": title,
            "on": _date(item.get("on")),
            "time": str(item.get("time") or "").strip()[:8],
            "where": str(item.get("where") or "").strip()[:160],
        })
    return {"tasks": tasks, "appointments": appointments}


def add_task(work: dict, raw: dict) -> dict:
    work = clean_work(work)
    title = str(raw.get("title") or "").strip()[:160]
    if not title:
        raise ValueError("Name the task")
    work["tasks"].append({
        "id": uuid4().hex[:8],
        "title": title,
        "due": _date(raw.get("due")),
        "who": str(raw.get("who") or "").strip()[:120],
        "done": False,
    })
    return work


def set_task(work: dict, task_id: str, done: bool) -> dict:
    work = clean_work(work)
    found = False
    for task in work["tasks"]:
        if task["id"] == task_id:
            task["done"] = bool(done)
            found = True
    if not found:
        raise ValueError("That task is not on the file")
    return work


def add_appointment(work: dict, raw: dict) -> dict:
    work = clean_work(work)
    title = str(raw.get("title") or "").strip()[:160]
    if not title:
        raise ValueError("Name the appointment")
    work["appointments"].append({
        "id": uuid4().hex[:8],
        "title": title,
        "on": _date(raw.get("on")),
        "time": str(raw.get("time") or "").strip()[:8],
        "where": str(raw.get("where") or "").strip()[:160],
    })
    return work


def today(rows: list[dict], client: dict, residuals: list[dict]) -> dict:
    tasks, appointments, nxt = [], [], []
    open_count = 0
    for row in rows:
        if row.get("status") != "closed":
            open_count += 1
        if row.get("next"):
            nxt.append({"id": row["id"], "title": row["title"], "next": row["next"]["title"], "client_name": row.get("client_name") or ""})
        work = row.get("work") or {}
        for task in work.get("tasks") or []:
            if task.get("done"):
                continue
            tasks.append({**task, "matter_id": row["id"], "matter": row["title"]})
        for item in work.get("appointments") or []:
            appointments.append({**item, "matter_id": row["id"], "matter": row["title"]})
    tasks.sort(key=lambda item: (item.get("due") or "9999", item["title"]))
    appointments.sort(key=lambda item: (item.get("on") or "9999", item.get("time") or ""))
    return {
        "open": open_count,
        "tasks": tasks[:12],
        "tasks_open": len(tasks),
        "appointments": appointments[:8],
        "next": nxt[:8],
        "client_agrees": bool(client.get("agrees")),
        "cash_book": client.get("cash_book") or 0,
        "ledger_total": client.get("ledger_total") or 0,
        "adjusted_bank": client.get("adjusted_bank") or 0,
        "residuals": residuals[:12],
        "last_signoff": (client.get("signoffs") or [None])[-1],
        "breaches": list(reversed(client.get("breaches") or []))[:5],
        "note": "The bank figure is the balance typed from the statement. This desk is not connected to the bank, and a sign-off is refused while the three figures do not agree.",
    }


def find(query: str, rows: list[dict]) -> list[dict]:
    needle = " ".join(str(query or "").casefold().split())
    if len(needle) < 2:
        return []
    hits = []
    for row in rows:
        hay = " ".join([row.get("title") or "", row.get("client_name") or "", row.get("deceased_name") or ""]).casefold()
        if needle in hay:
            hits.append({"kind": "Matter", "id": row["id"], "label": row["title"], "detail": row.get("client_name") or ""})
        for task in (row.get("work") or {}).get("tasks") or []:
            if needle in task["title"].casefold():
                hits.append({"kind": "Task", "id": row["id"], "label": task["title"], "detail": row["title"]})
        for item in (row.get("work") or {}).get("appointments") or []:
            if needle in item["title"].casefold() or needle in item.get("where", "").casefold():
                hits.append({"kind": "Appointment", "id": row["id"], "label": item["title"], "detail": row["title"]})
        if len(hits) >= 30:
            break
    return hits[:30]
