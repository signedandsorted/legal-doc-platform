"""HM Land Registry searches for the wills app: Land Charges K16 bankruptcy search (per
beneficiary) and PN1 index of proprietors' names search (for the deceased).

Josh approved live HMLR searches for the wills app on 23 Nov 2026, through the Titlefront
Limited HMLR account. THIS BUILD SHIPS WITH LIVE CALLS OFF: there is no live provider in the
code at all, so even with both flags on nothing can be sent to HMLR until a live provider is
added and the certificate is placed by Grok Bot (Chief of Staff). No keys or certificates here.

Fees (official, checked 2026-11-24):
- K16 official search: £6 per name electronic / £7 by post
  https://www.gov.uk/guidance/hm-land-registry-land-charges-fees
- PN1 search of the index of proprietors' names: £15 for each name searched
  https://www.gov.uk/government/publications/searches-of-the-index-of-proprietors-names/practice-guide-74-searches-of-the-index-of-proprietors-names

Flags are wills-scoped. Never reuse Titlefront (nshiff/autoenquire) env vars:
  WILLS_HMLR_ENABLED (default false), WILLS_HMLR_ALLOW_LIVE (default false),
  WILLS_HMLR_DAILY_CAP_GBP (default 50), WILLS_HMLR_BASE_URL (default "bgtest").
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import func, insert, select

from ..db import hmlr_spend

FEES_PENCE = {"K16": 600, "PN1": 1500}
FEE_SOURCES = {
    "K16": "https://www.gov.uk/guidance/hm-land-registry-land-charges-fees",
    "PN1": "https://www.gov.uk/government/publications/searches-of-the-index-of-proprietors-names/practice-guide-74-searches-of-the-index-of-proprietors-names",
}
FEES_CHECKED = "2026-11-24"
LABELS = {"K16": "Land Charges K16 bankruptcy search", "PN1": "PN1 search of the index of proprietors' names"}
NOT_ON = "HMLR searches are not switched on yet."
GRANT_KINDS = ("grant", "letters of administration")
MAX_NAMES = 10


class HmlrError(Exception):
    status = 400


class HmlrNotSwitchedOn(HmlrError):
    status = 503

    def __init__(self) -> None:
        super().__init__(NOT_ON)


class ConfirmationRequired(HmlrError):
    status = 409


class GrantRequired(HmlrError):
    status = 400


class DailyCapReached(HmlrError):
    status = 429


def _flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    enabled: bool
    allow_live: bool
    daily_cap_pence: int
    base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            cap = round(float(os.environ.get("WILLS_HMLR_DAILY_CAP_GBP") or 50) * 100)
        except ValueError:
            cap = 5000
        return cls(_flag("WILLS_HMLR_ENABLED"), _flag("WILLS_HMLR_ALLOW_LIVE"), max(cap, 0), os.environ.get("WILLS_HMLR_BASE_URL") or "bgtest")

    @property
    def switched_on(self) -> bool:
        return self.enabled and self.allow_live


class Provider(Protocol):
    name: str

    def search(self, search_type: str, full_name: str) -> dict: ...


class FixtureProvider:
    """Test provider. Returns canned results; makes no network calls."""
    name = "fixture"

    def __init__(self, results: dict | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.results = results or {}

    def search(self, search_type: str, full_name: str) -> dict:
        self.calls.append((search_type, full_name))
        return self.results.get((search_type, full_name), {"reference": f"FIXTURE-{search_type}-{len(self.calls)}", "result": "No entries found (fixture)"})


def live_provider(settings: Settings) -> Provider | None:
    """No live Business Gateway provider exists in this build. Returns None so nothing is called."""
    return None


def today_utc(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()


def spent_today_pence(conn, day: str) -> int:
    return int(conn.execute(select(func.coalesce(func.sum(hmlr_spend.c.fee_pence), 0)).where(hmlr_spend.c.day == day)).scalar() or 0)


def has_grant(uploads: list[dict]) -> bool:
    return any(any(k in (u.get("kind") or "").lower() for k in GRANT_KINDS) for u in uploads or [])


def _clean(search_type: str, names: list[str]) -> tuple[str, list[str]]:
    st = (search_type or "").upper()
    if st not in FEES_PENCE:
        raise HmlrError("Choose a K16 or PN1 search")
    clean = []
    for n in names or []:
        n = " ".join(str(n or "").split())[:120]
        if n and n not in clean:
            clean.append(n)
    if not clean:
        raise HmlrError("Add at least one name")
    if len(clean) > MAX_NAMES:
        raise HmlrError(f"Up to {MAX_NAMES} names at a time")
    return st, clean


def quote(conn, search_type: str, names: list[str], settings: Settings | None = None, now: datetime | None = None) -> dict:
    """What the confirmation screen shows. Never calls HMLR."""
    settings = settings or Settings.from_env()
    st, clean = _clean(search_type, names)
    fee = FEES_PENCE[st]
    spent = spent_today_pence(conn, today_utc(now))
    total = fee * len(clean)
    return {
        "switched_on": settings.switched_on, "message": "" if settings.switched_on else NOT_ON,
        "search_type": st, "label": LABELS[st], "names": clean, "fee_each": fee / 100, "total": total / 100,
        "fee_source": FEE_SOURCES[st], "fees_checked": FEES_CHECKED,
        "spent_today": spent / 100, "daily_cap": settings.daily_cap_pence / 100, "within_cap": spent + total <= settings.daily_cap_pence,
    }


def order(conn, search_type: str, names: list[str], *, confirm: bool, uploads: list[dict], draft_id: str, user_id: str,
          provider: Provider | None = None, settings: Settings | None = None, now: datetime | None = None) -> list[dict]:
    """Run confirmed searches, one ledger row per name. Order of checks: flags, confirmation,
    grant (PN1), daily cap, then the provider. Nothing is called unless every check passes."""
    settings = settings or Settings.from_env()
    if not settings.switched_on:
        raise HmlrNotSwitchedOn()
    provider = provider or live_provider(settings)
    if provider is None:
        raise HmlrNotSwitchedOn()
    st, clean = _clean(search_type, names)
    if confirm is not True:
        raise ConfirmationRequired("Please check the fee and confirm each search before it is ordered.")
    if st == "PN1" and not has_grant(uploads):
        raise GrantRequired("Upload the grant of probate or letters of administration before ordering a PN1 search.")
    day = today_utc(now)
    fee = FEES_PENCE[st]
    results = []
    for n in clean:
        spent = spent_today_pence(conn, day)
        if spent + fee > settings.daily_cap_pence:
            raise DailyCapReached(f"Today's HMLR spend cap of £{settings.daily_cap_pence / 100:.2f} would be passed (spent £{spent / 100:.2f}). Try again tomorrow or ask an admin.")
        res = provider.search(st, n)
        conn.execute(insert(hmlr_spend).values(id=str(uuid.uuid4()), day=day, search_type=st, name=n, fee_pence=fee, draft_id=draft_id, user_id=user_id,
                                               provider=provider.name, reference=str(res.get("reference") or ""), created_at=now or datetime.now(timezone.utc)))
        results.append({"name": n, "search_type": st, "fee": fee / 100, **res})
    return results


def ledger(conn, limit: int = 200) -> list[dict]:
    rows = conn.execute(select(hmlr_spend).order_by(hmlr_spend.c.created_at.desc()).limit(limit)).mappings().all()
    return [{**{k: v for k, v in dict(r).items() if k != "fee_pence"}, "fee": r["fee_pence"] / 100, "created_at": r["created_at"].isoformat()} for r in rows]
