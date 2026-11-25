import json
from pathlib import Path

import pytest

from app.guide_probate import PROBATE
from app.integrations import gazette
from tests.helpers import user_client
from tests.test_probate import answers

FEED = json.loads((Path(__file__).parent / "fixtures" / "gazette_2903.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clear():
    gazette.clear_cache()
    yield
    gazette.clear_cache()


def _fetch(payload, calls):
    def fetch(url, params):
        calls.append((url, params))
        return payload
    return fetch


def test_feed_fixture_parses_into_notices():
    notices = gazette.parse_feed(FEED)
    assert len(notices) == 2
    n = notices[0]
    assert n["notice_code"] == "2903" and n["name"] and n["published"]
    assert n["url"].startswith("https://www.thegazette.co.uk/notice/")


def test_empty_result_handled():
    calls = []
    assert gazette.search("Zzqxvy Nobody", fetch=_fetch({"title": "Search Result", "f:total": "0"}, calls)) == []
    assert gazette.parse_feed({}) == []


def test_one_request_per_action_and_cached():
    calls = []
    f = _fetch(FEED, calls)
    gazette.search("Smith", fetch=f, now=1000)
    gazette.search("smith", fetch=f, now=2000)
    assert len(calls) == 1
    q = calls[0][1]
    assert q["noticetype"] == "2903" and q["text"] == "Smith"


@pytest.mark.parametrize("pub,deadline", [("2026-01-15", "2026-03-16"), ("2026-12-31", "2027-03-01"), ("2026-08-31", "2026-11-01")])
def test_claim_deadline_is_two_months_and_a_day(pub, deadline):
    assert gazette.claim_deadline(pub) == deadline
    assert gazette.claim_deadline("") == ""


def test_s27_pack_prefills_and_flags_missing():
    a = answers()
    a["notice_s27"] = {"claims_to": "Pat Smith, 5 Mill Lane", "publication_date": "2026-12-03", "has_land": "Yes"}
    p = gazette.s27_pack(a)
    assert p["fields"]["deceased_name"] == "Sam Smith"
    assert p["fields"]["claim_deadline"] == "2027-02-04"
    assert p["missing"] == []
    assert any("local to the land" in x for x in p["checklist"])
    assert {f["ex_vat"] for f in p["fees"]} == {"96.55", "87.55", "240.00"}
    assert "nothing is sent" in p["note"]
    empty = gazette.s27_pack({})
    assert "Planned publication date" in empty["missing"]


def test_guide_step_and_api():
    step = next(s for s in PROBATE["steps"] if s["id"] == "notice_s27")
    assert step["tool"] == "gazette_s27"
    assert any("does not file, place or submit" in g for g in step["guidance"])
    with user_client() as c:
        a = answers()
        a["notice_s27"] = {"publication_date": "2026-01-15"}
        d = c.post("/api/drafts", json={"service": "probate", "answers": a}).json()
        r = c.get(f"/api/probate/drafts/{d['id']}/s27-pack")
        assert r.status_code == 200 and r.json()["fields"]["claim_deadline"] == "2026-03-16"
        assert c.get("/api/probate/gazette?name=Smith&date_from=bad").status_code == 400
