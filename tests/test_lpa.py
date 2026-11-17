import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient  # noqa: E402,F401

from app.main import app  # noqa: E402,F401
from tests.helpers import user_client  # noqa: E402

ADULT = {"date_of_birth": "1970-01-01", "address": "3 Low Rd"}
CP_OK = {"cp_over_18": True, "cp_not_attorney": True, "cp_not_family": True, "cp_not_partner": True, "cp_not_business": True, "cp_not_care_home": True}


def lpa(kind="lpa_property", **over):
    a = {
        "donor": {"full_name": "Jo Bloggs", "email": "jo@example.com", **ADULT},
        "attorneys": {"attorneys": [{"full_name": "Ann One", **ADULT}, {"full_name": "Bob Two", **ADULT}], "not_bankrupt": True},
        "decisions": {"decisions": "Jointly and severally"},
        "replacements": {"replacement_attorneys": [{"full_name": "Cal Three", **ADULT}]},
        "notify": {"people_to_notify": [{"full_name": "Dee Four", "address": "1 Lane"}]},
        "preferences": {"preferences": "Stay at home"},
        "certificate_provider": {"full_name": "Dr Eve Five", "address": "Surgery", "basis": "Relevant professional skills (doctor, solicitor, social worker etc.)", **CP_OK},
        "registration": {"applicant": "Me (the donor)", "correspondent": "Me (the donor)", "fee_reduction": "No, I will pay the full fee"},
    }
    if kind == "lpa_property":
        a["when"] = {"when_used": "As soon as it is registered"}
    else:
        a["life_sustaining"] = {"life_sustaining": "Option A: my attorneys can give or refuse consent"}
    for k, v in over.items():
        a[k] = {**a.get(k, {}), **v}
    return a


def make(client, kind, answers):
    return client.post("/api/drafts", json={"service": kind, "answers": answers}).json()


def test_lp1f_pack_maps_every_section():
    with user_client() as c:
        d = make(c, "lpa_property", lpa())
        assert d["missing"] == [] and [i for i in d["issues"] if i["level"] == "error"] == []
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        heads = [s["heading"] for s in doc["sections"]]
        for n in ("Section 1", "Section 2", "Section 3", "Section 4", "Section 5: when", "Section 6", "Section 7", "Section 10", "Sections 12 to 15", "Form LP3"):
            assert any(h.startswith(n) for h in heads), n
        assert doc["title"].startswith("LP1F") and any("lasting-power-of-attorney-forms" in s["url"] for s in doc["sources"])


def test_lp1h_life_sustaining_and_title():
    with user_client() as c:
        d = make(c, "lpa_health", lpa("lpa_health"))
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        assert doc["title"].startswith("LP1H")
        assert any(s["heading"] == "Section 5: life-sustaining treatment" and "Option A" in s["paragraphs"][0] for s in doc["sections"])


def test_certificate_provider_rules_block_document():
    with user_client() as c:
        d = make(c, "lpa_property", lpa(certificate_provider={"full_name": "Ann One", "cp_not_family": False}))
        msgs = " ".join(i["message"] for i in d["issues"] if i["level"] == "error")
        assert "certificate provider cannot be one of your attorneys" in msgs and "eligibility" in msgs
        assert c.get(f"/api/drafts/{d['id']}/document").status_code == 400


def test_attorney_rules():
    with user_client() as c:
        a = lpa(replacements={"replacement_attorneys": [{"full_name": "Ann One", **ADULT}]}, decisions={"decisions": "Only one attorney"})
        a["attorneys"]["attorneys"].append({"full_name": "Kid", "date_of_birth": "2020-01-01", "address": "x"})
        a["notify"]["people_to_notify"].append({"full_name": "Bob Two", "address": "y"})
        d = make(c, "lpa_property", a)
        msgs = " ".join(i["message"] for i in d["issues"])
        assert "under 18" in msgs and "both an attorney and a replacement" in msgs and "cannot also be a person to notify" in msgs and "choose how they make decisions" in msgs


def test_mixed_decisions_need_wording_and_go_on_continuation_sheet():
    with user_client() as c:
        d = make(c, "lpa_property", lpa(decisions={"decisions": "Jointly for some decisions, jointly and severally for others"}))
        assert any("Which decisions must be made jointly" in m for m in d["missing"])
        d = make(c, "lpa_property", lpa(decisions={"decisions": "Jointly for some decisions, jointly and severally for others", "joint_decisions": "Selling my house"}))
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        assert any(s["heading"].startswith("Continuation sheet 2") for s in doc["sections"])


def test_more_than_four_attorneys_use_continuation_sheet_1():
    with user_client() as c:
        a = lpa()
        a["attorneys"]["attorneys"] = [{"full_name": f"Att {i}", **ADULT} for i in range(6)]
        d = make(c, "lpa_property", a)
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        cont = [s for s in doc["sections"] if s["heading"].startswith("Continuation sheet 1")][0]
        assert len(cont["paragraphs"]) == 2


def test_property_lpa_needs_bankruptcy_confirmation_and_fee_reduction_mentions_lpa120():
    with user_client() as c:
        a = lpa(registration={"fee_reduction": "Yes, reduction (income under £12,000)"})
        a["attorneys"]["not_bankrupt"] = False
        d = make(c, "lpa_property", a)
        assert any("bankrupt" in m for m in d["missing"])
        a["attorneys"]["not_bankrupt"] = True
        d = make(c, "lpa_property", a)
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        assert "LPA120" in " ".join(p for s in doc["sections"] for p in s["paragraphs"])
