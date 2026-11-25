from app.guide_probate import PROBATE
from app.integrations import asset_trace as at
from tests.helpers import user_client
from tests.test_probate import answers


def test_pack_renders_with_estate_data_and_flags_missing():
    a = answers()
    p = at.pack(a)
    rows = {r["label"]: r["value"] for r in p["details"]["rows"]}
    assert rows["Full name"] == "Sam Smith" and rows["Last address"] == "4 Mill Lane"
    assert "Date of birth" in p["details"]["missing"] and "Other addresses in the last 6 years" in p["details"]["missing"]
    a["deceased"]["date_of_birth"] = "1950-01-01"
    a["discovery"] = {"previous_addresses": "1 Old Road"}
    assert at.pack(a)["details"]["missing"] == []


def test_services_and_no_closed_register():
    ids = {s["id"] for s in at.SERVICES}
    assert {"mylostaccount", "gretel", "dns", "tell_us_once", "pension_tracing", "credit_report", "probate_search"} == ids
    assert not any("unclaimedassets" in s["url"].lower() for s in at.SERVICES)
    step = next(s for s in PROBATE["steps"] if s["id"] == "discovery")
    assert step["tool"] == "find_notify"
    assert {"trace_" + i for i in ids} <= {f["name"] for f in step["fields"]}


def test_tracker_status_persists():
    with user_client() as c:
        a = answers()
        d = c.post("/api/drafts", json={"service": "probate", "answers": a}).json()
        a["discovery"] = {"trace_gretel": "Submitted", "trace_dns": "Reply received", "trace_pension_tracing": "bogus"}
        c.put(f"/api/drafts/{d['id']}", json={"answers": a})
        st = {s["id"]: s["status"] for s in c.get(f"/api/probate/drafts/{d['id']}/find-notify").json()["services"]}
        assert st["gretel"] == "Submitted" and st["dns"] == "Reply received" and st["pension_tracing"] == "Not started"
