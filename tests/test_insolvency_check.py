from datetime import datetime, timezone

import httpx

from app.doc_probate import probate_issues
from app.guide_probate import PROBATE
from app.probate_tools import stamp_insolvency_checks
from tests.helpers import user_client
from tests.test_probate import answers

T1 = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 11, 25, 9, 30, tzinfo=timezone.utc)


def test_guide_step_is_a_link_out_only():
    step = next(s for s in PROBATE["steps"] if s["id"] == "insolvency")
    assert step["tool"] == "insolvency"
    assert any(s["url"] == "https://www.gov.uk/search-bankruptcy-insolvency-register" for s in step["sources"])
    assert any("does not file or submit" in g for g in step["guidance"])
    assert any("£6 per name" in g for g in step["guidance"])


def test_result_saved_per_beneficiary_with_timestamp():
    new = {"insolvency": {"checks": [
        {"name": "Pat Smith", "role": "Beneficiary", "result": "Clear: no entry found"},
        {"name": "Jo Smith", "role": "Beneficiary", "result": "Not checked yet"},
    ]}}
    out = stamp_insolvency_checks({}, new, now=T1)
    pat, jo = out["insolvency"]["checks"]
    assert pat["recorded_at"] == "2026-11-24T12:00:00+00:00"
    assert "recorded_at" not in jo
    # unchanged result keeps its first timestamp even if the browser dropped it
    again = stamp_insolvency_checks(out, {"insolvency": {"checks": [
        {"name": "Pat Smith", "role": "Beneficiary", "result": "Clear: no entry found"},
        {"name": "Jo Smith", "role": "Beneficiary", "result": "Possible match found"},
    ]}}, now=T2)
    pat2, jo2 = again["insolvency"]["checks"]
    assert pat2["recorded_at"] == "2026-11-24T12:00:00+00:00"
    assert jo2["recorded_at"] == "2026-11-25T09:30:00+00:00"


def test_possible_match_warns_before_distribution():
    a = answers()
    a["insolvency"] = {"checks": [{"name": "Jo Smith", "result": "Possible match found"}]}
    assert any("Jo Smith" in i["message"] and i["level"] == "warning" for i in probate_issues(a))


def test_no_outbound_http_to_insolvency_service(monkeypatch):
    calls = []
    real_send = httpx.Client.send

    def spy(self, request, *args, **kwargs):
        if "insolvency" in str(request.url):
            calls.append(str(request.url))
        return real_send(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", spy)
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": answers()}).json()
        body = dict(answers())
        body["insolvency"] = {"checks": [{"name": "Pat Smith", "role": "Beneficiary", "result": "Clear: no entry found"}]}
        saved = c.put(f"/api/drafts/{d['id']}", json={"answers": body}).json()
        assert saved["answers"]["insolvency"]["checks"][0]["recorded_at"]
    assert [u for u in calls if "insolvencydirect" in u or "search-bankruptcy" in u] == []
