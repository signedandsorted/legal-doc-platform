"""Read the signed-in mailbox from Microsoft Graph and file a message onto a matter.

The only address used is graph.microsoft.com. A token from anywhere else is refused.
Nothing is sent, and a message is not stored unless Graph returned it.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.microsoft.com/v1.0"


def public_outlook(saved: dict | None) -> dict:
    saved = saved or {}
    return {"connected": bool(saved.get("access_token"))}


def merge_outlook(saved: dict | None, incoming: dict) -> dict:
    saved = dict(saved or {})
    token = str(incoming.get("access_token") or "").strip()
    if token:
        if len(token) < 20 or len(token) > 8000 or any(ch.isspace() for ch in token):
            raise ValueError("Paste the Outlook access token from Microsoft Graph")
        saved["access_token"] = token
    if not saved.get("access_token"):
        raise ValueError("Paste the Outlook access token")
    return saved


def _get(token: str, path: str) -> dict:
    if not path.startswith("/"):
        raise ValueError("Bad Outlook request")
    request = urllib.request.Request(
        GRAPH + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "signed-and-sorted"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise PermissionError("Outlook refused the token") from exc
        raise RuntimeError(f"Outlook returned {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Outlook could not be reached") from exc
    try:
        return json.loads(raw.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Outlook did not return mail") from exc


def _sender(item: dict) -> str:
    email = ((item.get("from") or {}).get("emailAddress") or {})
    name = str(email.get("name") or "").strip()
    address = str(email.get("address") or "").strip()
    return (name + (" <" + address + ">" if address else "")).strip()[:180]


def summarise_messages(payload) -> list[dict]:
    found = []
    for item in (payload.get("value") or [])[:20]:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        found.append({
            "id": str(item["id"])[:400],
            "subject": str(item.get("subject") or "(no subject)")[:200],
            "from": _sender(item),
            "on": str(item.get("receivedDateTime") or "")[:25],
            "preview": str(item.get("bodyPreview") or "").strip()[:400],
        })
    return found


def summarise_events(payload) -> list[dict]:
    found = []
    for item in (payload.get("value") or [])[:10]:
        if not isinstance(item, dict):
            continue
        start = ((item.get("start") or {}).get("dateTime") or "")[:16]
        found.append({"subject": str(item.get("subject") or "Appointment")[:160], "start": start})
    return found


def fetch_mailbox(token: str) -> dict:
    messages = summarise_messages(_get(token, "/me/messages?$top=20&$select=id,subject,from,receivedDateTime,bodyPreview&$orderby=receivedDateTime%20desc"))
    events = summarise_events(_get(token, "/me/events?$top=8&$select=subject,start&$orderby=start/dateTime"))
    return {"messages": messages, "events": events}


def fetch_message(token: str, message_id: str) -> dict:
    safe = urllib.parse.quote(str(message_id or ""), safe="")
    if not safe:
        raise ValueError("Choose a message")
    rows = summarise_messages({"value": [_get(token, f"/me/messages/{safe}?$select=id,subject,from,receivedDateTime,bodyPreview")]})
    if not rows:
        raise RuntimeError("Outlook did not return that message")
    return rows[0]
