import httpx
import pytest

from app.integrations.companies_house import (
    CompaniesHouseClient,
    CompaniesHouseNotConfigured,
    clear_cache,
)


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


def _client(handler, monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key-not-real")
    transport = httpx.MockTransport(handler)
    return CompaniesHouseClient(estate_id="estate-1", client=httpx.Client(transport=transport, base_url="https://api.company-information.service.gov.uk"))


def test_missing_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    with pytest.raises(CompaniesHouseNotConfigured, match="not configured yet"):
        CompaniesHouseClient()


def test_search_officers_parses_items(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/officers"
        assert request.url.params.get("q") == "Jane Smith"
        return httpx.Response(
            200,
            json={"items": [{"title": "Jane SMITH", "date_of_birth": {"month": 4, "year": 1952}}]},
            request=request,
        )

    with _client(handler, monkeypatch) as ch:
        items = ch.search_officers("Jane Smith")
    assert items[0]["title"] == "Jane SMITH"
    assert items[0]["date_of_birth"]["year"] == 1952


def test_appointments_and_company(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/appointments"):
            return httpx.Response(200, json={"items": [{"appointed_to": {"company_number": "01234567"}}]}, request=request)
        if request.url.path == "/company/01234567":
            return httpx.Response(200, json={"company_name": "Example Ltd", "company_number": "01234567"}, request=request)
        return httpx.Response(404, json={"error": "not found"}, request=request)

    with _client(handler, monkeypatch) as ch:
        apps = ch.get_officer_appointments("abc123")
        company = ch.get_company("01234567")
    assert apps[0]["appointed_to"]["company_number"] == "01234567"
    assert company["company_name"] == "Example Ltd"


def test_429_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": "rate limit"}, request=request)
        return httpx.Response(200, json={"items": [{"title": "ok"}]}, request=request)

    with _client(handler, monkeypatch) as ch:
        items = ch.search_officers("ok")
    assert calls["n"] == 2
    assert items[0]["title"] == "ok"


def test_cache_is_per_estate(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"items": [{"n": calls["n"]}]}, request=request)

    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key-not-real")
    transport = httpx.MockTransport(handler)
    raw = httpx.Client(transport=transport, base_url="https://api.company-information.service.gov.uk")
    ch = CompaniesHouseClient(estate_id="e1", client=raw)
    ch.search_officers("same")
    ch.search_officers("same")
    assert calls["n"] == 1
    ch.close()
