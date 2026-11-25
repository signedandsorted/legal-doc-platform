"""Pull a matter from Actionstep into this desk.

Actionstep stays the case system. This module reads the matter name, reference
and people. It does not write back, and it does not take a matter that Actionstep
has not returned. The token is the firm's. A call is refused unless the address
Actionstep gave them is one of Actionstep's own hosts.
"""
from urllib.parse import urlparse
import json
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_SUFFIXES = (".actionstep.com", ".actionstepstaging.com")
TOKEN_URL = "https://api.actionstep.com/api/oauth/token"


def clean_endpoint(url: str) -> str:
    text = (url or "").strip()
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host.endswith(suffix) for suffix in ALLOWED_SUFFIXES):
        raise ValueError("Use the https address Actionstep returned with the token")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("The Actionstep address must not include a login or a query")
    path = parsed.path.rstrip("/")
    if not path.endswith("/api"):
        path = "/api"
    return f"https://{host}{path}/"


def rest_url(endpoint: str, resource: str) -> str:
    return clean_endpoint(endpoint) + "rest/" + resource.lstrip("/")


def _rows(payload, key: str) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    block = payload.get(key)
    if isinstance(block, list):
        return [item for item in block if isinstance(item, dict)]
    if isinstance(block, dict):
        return [block]
    return []


def summarise_actions(payload) -> list[dict]:
    found = []
    for item in _rows(payload, "actions"):
        action_id = str(item.get("id") or "").strip()
        if not action_id:
            continue
        found.append({
            "id": action_id[:40],
            "name": str(item.get("name") or "Matter")[:160],
            "reference": str(item.get("reference") or "")[:80],
            "status": str(item.get("status") or "")[:40],
        })
    return found[:50]


def people_from(payload) -> list[dict]:
    named = {str(item.get("id")): item for item in _rows(payload, "participants")}
    people = []
    seen = set()
    for seat in _rows(payload, "actionparticipants"):
        link = (seat.get("links") or {}).get("participant")
        person = named.get(str(link)) or {}
        name = str(person.get("displayName") or person.get("firstName") or "").strip()
        email = ""
        for field in ("email", "eMail"):
            if person.get(field):
                email = str(person[field])
                break
        role = str(seat.get("participantType") or (seat.get("links") or {}).get("participantType") or "")
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        people.append({"name": name[:160], "email": email[:254], "role": role[:80]})
    return people[:12]


def guess_kind(name: str) -> str:
    text = (name or "").lower()
    if "probate" in text or "estate of" in text:
        return "probate"
    if "health" in text and "attorney" in text:
        return "lpa_health"
    if "attorney" in text or "lpa" in text:
        return "lpa_property"
    if "trust" in text:
        return "trust"
    return "will"


def deceased_name(matter_name: str, people: list[dict]) -> str:
    for person in people:
        if "deceased" in person.get("role", "").lower() or "deceased" in person.get("name", "").lower():
            return person["name"].replace("Deceased", "").strip(" -:")[:160]
    if matter_name.lower().startswith("estate of "):
        return matter_name[10:].strip()[:160]
    return ""


def public_connection(saved: dict | None) -> dict:
    saved = saved or {}
    return {
        "connected": bool(saved.get("access_token") and saved.get("api_endpoint")),
        "api_endpoint": saved.get("api_endpoint") or "",
        "orgkey": saved.get("orgkey") or "",
        "can_refresh": bool(saved.get("refresh_token") and saved.get("client_id") and saved.get("client_secret")),
    }


def merge_connection(saved: dict | None, incoming: dict) -> dict:
    saved = dict(saved or {})
    endpoint = incoming.get("api_endpoint")
    if endpoint:
        saved["api_endpoint"] = clean_endpoint(str(endpoint))
    for key, limit in (("access_token", 4000), ("refresh_token", 4000), ("client_id", 120), ("client_secret", 200), ("orgkey", 80)):
        value = incoming.get(key)
        if value:
            saved[key] = str(value).strip()[:limit]
    if not saved.get("access_token") or not saved.get("api_endpoint"):
        raise ValueError("Paste the access token and the API address Actionstep returned")
    return saved


def _call(url: str, token: str, data: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/vnd.api+json", "User-Agent": "signed-and-sorted"}
    if data is None:
        headers["Authorization"] = f"Bearer {token}"
    else:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise PermissionError("Actionstep refused the token") from exc
        raise RuntimeError(f"Actionstep returned {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Actionstep could not be reached") from exc
    try:
        return json.loads(raw.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Actionstep did not return a matter list") from exc


def refresh_connection(saved: dict) -> dict:
    payload = _call(TOKEN_URL, "", {
        "grant_type": "refresh_token",
        "refresh_token": saved.get("refresh_token") or "",
        "client_id": saved.get("client_id") or "",
        "client_secret": saved.get("client_secret") or "",
    })
    if payload.get("access_token"):
        saved["access_token"] = str(payload["access_token"])[:4000]
    if payload.get("refresh_token"):
        saved["refresh_token"] = str(payload["refresh_token"])[:4000]
    if payload.get("api_endpoint"):
        saved["api_endpoint"] = clean_endpoint(str(payload["api_endpoint"]))
    if payload.get("orgkey"):
        saved["orgkey"] = str(payload["orgkey"])[:80]
    return saved


def fetch_actions(saved: dict) -> list[dict]:
    url = rest_url(saved["api_endpoint"], "actions?pageSize=25")
    return summarise_actions(_call(url, saved["access_token"]))


def fetch_people(saved: dict, action_id: str) -> list[dict]:
    safe = urllib.parse.quote(str(action_id), safe="")
    url = rest_url(saved["api_endpoint"], f"actionparticipants?action={safe}&include=participant")
    return people_from(_call(url, saved["access_token"]))
