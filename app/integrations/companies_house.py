"""Companies House Public Data API client (free, HTTP Basic auth).

Source: https://developer-specs.company-information.service.gov.uk/guides/rateLimiting
(checked 2026-11-23). Official endpoints only. Never logs or returns the API key.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx

# Public Data API; rate limit 600 requests / 5 minutes.
BASE_URL = "https://api.company-information.service.gov.uk"
TIMEOUT_S = 10.0
MAX_429_RETRIES = 3
# In-memory cache: (estate_id or "", method, path, frozen params) -> json
_cache: dict[tuple, Any] = {}


class CompaniesHouseNotConfigured(RuntimeError):
    """Raised when COMPANIES_HOUSE_API_KEY is missing. Callers should show 'not configured yet'."""

    def __init__(self) -> None:
        super().__init__("not configured yet")


class CompaniesHouseClient:
    def __init__(self, estate_id: str | None = None, client: httpx.Client | None = None) -> None:
        key = os.environ.get("COMPANIES_HOUSE_API_KEY")
        if not key:
            raise CompaniesHouseNotConfigured()
        self.estate_id = estate_id or ""
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=BASE_URL,
            auth=(key, ""),
            timeout=TIMEOUT_S,
            headers={"User-Agent": "legal-doc-platform/probate-companies-house"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "CompaniesHouseClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        frozen = tuple(sorted((params or {}).items()))
        cache_key = (self.estate_id, path, frozen)
        if cache_key in _cache:
            return _cache[cache_key]
        retries = 0
        while True:
            try:
                response = self._client.get(path, params=params)
            except httpx.RequestError as exc:
                raise RuntimeError("Companies House request failed") from exc
            if response.status_code == 429 and retries < MAX_429_RETRIES:
                time.sleep(2 ** retries)
                retries += 1
                continue
            if response.status_code == 429:
                response.raise_for_status()
            response.raise_for_status()
            data = response.json()
            _cache[cache_key] = data
            return data

    def search_officers(self, query: str) -> list[dict[str, Any]]:
        data = self._request("/search/officers", params={"q": query})
        return list(data.get("items") or [])

    def get_officer_appointments(self, officer_id: str) -> list[dict[str, Any]]:
        data = self._request(f"/officers/{officer_id}/appointments")
        return list(data.get("items") or [])

    def get_company(self, number: str) -> dict[str, Any]:
        return self._request(f"/company/{number}")


def clear_cache() -> None:
    _cache.clear()


def apply_companies_house_matches(answers: dict) -> dict:
    """Copy ticked officer matches into the estate asset checklist. Idempotent. Does not call the API."""
    block = answers.get("companies_house") or {}
    officers = block.get("officers") or []
    estate = dict(answers.get("estate") or {})
    assets = list(estate.get("assets") or [])
    existing = {(x.get("description") or "").strip() for x in assets}
    for officer in officers:
        match = officer.get("match")
        if match not in (True, "Yes", "yes", "on", "true"):
            continue
        name = (officer.get("name") or "officer").strip()
        apps = (officer.get("appointments") or "appointment").strip()
        desc = "Companies House: %s — %s" % (name, apps)
        if desc in existing:
            continue
        assets.append({
            "description": desc,
            "category": "Stocks, shares or investments",
            "value": "0",
            "ownership": "Owned on their own",
            "abroad": "No",
        })
        existing.add(desc)
    estate["assets"] = assets
    out = dict(answers)
    out["estate"] = estate
    return out
