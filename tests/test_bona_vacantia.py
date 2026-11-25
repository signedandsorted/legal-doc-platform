import json
from pathlib import Path

import httpx
import pytest

from app.doc_probate import probate_issues
from app.guide_probate import PROBATE
from app.integrations import bona_vacantia as bv
from tests.helpers import user_client
from tests.test_probate import answers

FIXTURE = (Path(__file__).parent / "fixtures" / "unclaimed_estates.csv").read_text(encoding="utf-8")
CSV_URL = "https://assets.publishing.service.gov.uk/media/abc123/UnclaimedEstatesList.csv"


def _client(fail=False, calls=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        if fail:
            return httpx.Response(503)
        if request.url.path.startswith("/api/content/"):
            return httpx.Response(200, json={"details": {"attachments": [{"content_type": "text/csv", "url": CSV_URL}]}})
        if str(request.url) == CSV_URL:
            return httpx.Response(200, text=FIXTURE)
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    return tmp_path


def test_parses_fixture_and_surname_search_is_case_insensitive():
    rows = bv.parse_csv(FIXTURE)
    assert len(rows) == 4
    hits = bv.search(rows, "aDAMS")
    assert {h["bv_reference"] for h in hits} == {"BV21511643/1", "ESTA26#4064/1", "BV2022729/1"}
    assert bv.search(rows, "adams", "david")[0]["place_of_death"] == "Kendal Cumbria"
    assert bv.search(rows, "Nobody") == []


def test_finds_current_csv_link_not_hard_coded():
    with _client() as c:
        assert bv.current_csv_url(c) == CSV_URL


def test_downloads_at_most_once_a_day():
    calls = []
    with _client(calls=calls) as c:
        bv.lookup("Adams", client=c, now=1_000_000)
        n = len(calls)
        bv.lookup("Abbott", client=c, now=1_000_000 + 3600)
        assert len(calls) == n
        bv.lookup("Abbott", client=c, now=1_000_000 + 25 * 3600)
        assert len(calls) == 2 * n


def test_download_failure_falls_back_to_cache_and_says_when():
    with _client() as c:
        first = bv.lookup("Adams", client=c, now=1_000_000)
    with _client(fail=True) as c:
        later = bv.lookup("Adams", client=c, now=1_000_000 + 2 * 86400)
    assert later["stale"] is True
    assert first["fetched_at"] in later["note"]
    assert len(later["matches"]) == 3


def test_no_cache_and_no_download_is_a_clear_error():
    with _client(fail=True) as c, pytest.raises(bv.BonaVacantiaUnavailable):
        bv.lookup("Adams", client=c)


def test_guide_step_and_claim_note():
    step = next(s for s in PROBATE["steps"] if s["id"] == "bona_vacantia")
    assert step["tool"] == "bona_vacantia"
    assert any("does not file or submit" in g for g in step["guidance"])
    a = answers()
    a["bona_vacantia"] = {"result": "Possible match found", "bv_reference": "BV2022729/1"}
    msgs = [i["message"] for i in probate_issues(a)]
    assert any("BV2022729/1" in m and "yourself" in m for m in msgs)


def test_api_requires_sign_in_and_searches(monkeypatch):
    monkeypatch.setattr(bv, "load", lambda client=None, now=None: {"rows": bv.parse_csv(FIXTURE), "fetched_at": "2026-11-24T12:00+00:00", "source_url": CSV_URL, "stale": False, "note": ""})
    from tests.helpers import anon_client
    with anon_client() as c:
        assert c.get("/api/probate/bona-vacantia?surname=Adams").status_code == 401
    with user_client() as c:
        r = c.get("/api/probate/bona-vacantia?surname=adams&forename=elsie")
        assert r.status_code == 200
        body = r.json()
        assert [m["bv_reference"] for m in body["matches"]] == ["BV2022729/1"]
        assert body["claim_url"].startswith("https://www.gov.uk/")
