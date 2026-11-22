import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from tests.helpers import user_client  # noqa: E402

ADULT = {"date_of_birth": "1970-01-01", "address": "3 Low Rd"}


def general(**over):
    a = {
        "type": {
            "poa_type": "General power of attorney (Powers of Attorney Act 1971, section 10)",
            "understood_capacity": True,
        },
        "donor": {"full_name": "Jo Bloggs", "email": "jo@example.com", "address": "1 High St", "date_of_birth": "1970-01-01"},
        "attorneys": {"attorneys": [{"full_name": "Ann One", **ADULT}], "how_they_act": "Only one attorney"},
        "authority": {"end_wish": "No extra end date — I will revoke it if I need to, and it will end if I lose capacity, die or become bankrupt"},
    }
    a.update(over)
    return a


def test_services_include_ordinary_poa_with_sources():
    with user_client() as c:
        ids = {s["id"] for s in c.get("/api/services").json()}
        assert "poa_ordinary" in ids
        svc = c.get("/api/services/poa_ordinary").json()
        assert svc["short_title"] == "Ordinary power of attorney"
        assert [s["id"] for s in svc["steps"]] == ["intro", "type", "donor", "attorneys", "authority"]
        assert all(s.get("sources") for s in svc["steps"])
        assert any("ukpga/1971/27/schedule/1" in src["url"] for st in svc["steps"] for src in st["sources"])
        assert all(s.get("video") and s["video"]["src"].endswith(".mp4") for s in svc["steps"])
        assert svc["review_video"]["src"].endswith("poa_review.mp4")


def test_general_power_uses_section_10_schedule_1_form():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "poa_ordinary", "answers": general()}).json()
        assert d["missing"] == []
        assert not [i for i in d["issues"] if i["level"] == "error"]
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
        assert doc["title"].startswith("General power of attorney")
        assert "Schedule 1" in text
        assert "section 10 of the Powers of Attorney Act 1971" in text
        assert "This General Power of Attorney is made this" in text
        assert "Ann One" in text
        assert "mental incapacity" in text.lower() or "lose mental capacity" in text.lower()
        assert "not legal advice" in (doc["notice"] + text).lower()
        assert "Office of the Public Guardian" in text
        assert any("ukpga/1971/27/section/10" in s["url"] for s in doc["sources"])
        assert any("practice-guide-9" in s["url"] for s in doc["sources"])


def test_specific_power_requires_a_task_and_flags_solicitor_review():
    with user_client() as c:
        a = general()
        a["type"]["poa_type"] = "Specific (limited) power of attorney for one exact task"
        d = c.post("/api/drafts", json={"service": "poa_ordinary", "answers": a}).json()
        assert any("exact task" in i["message"] for i in d["issues"] if i["level"] == "error")
        assert c.get(f"/api/drafts/{d['id']}/document").status_code == 400
        a["authority"]["task"] = "to complete the sale of my property at 1 High Street under the contract dated 1 May 2026"
        d = c.post("/api/drafts", json={"service": "poa_ordinary", "answers": a}).json()
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
        assert doc["title"].startswith("Specific power of attorney")
        assert "limited purpose only" in text
        assert "1 High Street" in text
        assert "not a general power of attorney under section 10" in text
        assert any("solicitor must review" in i["message"].lower() or "solicitor must review" in text.lower() for i in d["issues"])


def test_capacity_confirmation_is_required_and_two_attorneys_need_a_choice():
    with user_client() as c:
        a = general()
        a["type"]["understood_capacity"] = False
        a["attorneys"] = {"attorneys": [{"full_name": "Ann One", **ADULT}, {"full_name": "Bob Two", **ADULT}], "how_they_act": "Only one attorney"}
        d = c.post("/api/drafts", json={"service": "poa_ordinary", "answers": a}).json()
        msgs = " ".join(i["message"] for i in d["issues"] if i["level"] == "error")
        assert "not a substitute for a lasting power of attorney" in msgs
        assert "jointly and severally" in msgs
