import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient  # noqa: E402,F401

from app.doc_probate import plan  # noqa: E402
from app.main import app  # noqa: E402,F401
from tests.helpers import user_client  # noqa: E402


def answers(**over):
    a = {
        "deceased": {"full_name": "Sam Smith", "date_of_death": "2026-10-01", "address": "4 Mill Lane", "domicile": "Yes", "marital_status": "Widowed or a surviving civil partner", "death_certificate": "UK death certificate"},
        "will": {"has_will": "Yes, I have the original", "applicant_role": "Executor named in the will or a codicil", "applicant": {"full_name": "Pat Smith", "address": "5 Mill Lane", "email": "pat@example.com"}, "applicants": "1"},
        "estate": {"assets": [{"description": "Bank", "value": "200000", "ownership": "Owned on their own"},
                              {"description": "Joint account", "value": "10000", "ownership": "Joint tenants (passes automatically to the other owner)"}],
                   "debts": [{"description": "Card", "value": "1000"}], "funeral_costs": "4000"},
        "tax": {},
        "account": {"who_files": "I will file it myself"},
    }
    for k, v in over.items():
        a[k] = {**a[k], **v}
    return a


def test_simple_excepted_estate_online_five_values():
    p = plan(answers())
    v = p["values"]
    assert p["excepted"] and p["online"] and p["route"] == "Online on GOV.UK" and p["fee"] == 526
    assert (v["gross_iht"], v["net_iht"], v["net_qualifying"], v["gross_probate"], v["net_probate"]) == (210000, 205000, 205000, 200000, 195000)
    assert [f for f, _ in p["forms"]] == ["PA1P"]


def test_lost_will_goes_by_post_with_pa13():
    p = plan(answers(will={"has_will": "Yes, but the original is lost"}))
    assert not p["online"] and "PA1P" in p["route"] and "PA13" in [f for f, _ in p["forms"]]


def test_no_will_pa1a_and_unmarried_partner_blocked():
    p = plan(answers(will={"has_will": "No", "applicant_role": "Child aged 18 or over"}, deceased={"domicile": "No, outside the UK"}))
    assert "PA1A" in p["route"]
    p = plan(answers(will={"has_will": "No", "applicant_role": "Unmarried partner"}))
    assert p["blockers"] and p["route"].startswith("Blocked")


def test_large_estate_needs_iht400_and_tax_estimate():
    a = answers(estate={"assets": [{"description": "House", "value": "900000"}], "debts": [], "funeral_costs": "0"},
                tax={"home_to_descendants": "Yes", "home_value_to_descendants": "900000", "earlier_spouse_died": "Yes", "unused_nrb_percent": "100"})
    p = plan(a)
    forms = [f for f, _ in p["forms"]]
    assert not p["excepted"] and forms[:2] == ["PA1P", "IHT400"] and {"IHT402", "IHT435", "IHT436"} <= set(forms)
    # threshold 650k + 350k RNRB = 1m > 900k, so no tax, but full details still needed
    assert p["tax"]["tax"] == 0
    a["tax"] = {}
    p = plan(a)
    assert round(p["tax"]["tax"]) == round((900000 - 325000) * 0.4)


def test_triggers_force_full_details_and_small_estate_no_fee():
    p = plan(answers(tax={"gifts_with_reservation": True}))
    assert not p["excepted"] and "IHT400" in [f for f, _ in p["forms"]]
    p = plan(answers(estate={"assets": [{"description": "Cash", "value": "3000"}], "debts": [], "funeral_costs": "0"}))
    assert p["fee"] == 0


def test_tnrb_excepted_up_to_650k_and_charity_rate():
    p = plan(answers(estate={"assets": [{"description": "Bank", "value": "600000"}], "debts": [], "funeral_costs": "0"}, tax={"earlier_spouse_died": "Yes", "unused_nrb_percent": "100"}))
    assert p["excepted"]
    p = plan(answers(estate={"assets": [{"description": "Bank", "value": "1000000"}], "debts": [], "funeral_costs": "0"}, tax={"to_charity": "100000"}))
    assert p["tax"]["rate"] == 0.36


def test_probate_document_api():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": answers()}).json()
        assert d["missing"] == []
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        text = " ".join(x for s in doc["sections"] for x in s["paragraphs"])
        assert "Online on GOV.UK" in text and "£195,000.00" in text and "£526.00" in text
        assert "What is left for the grant" in text and "Joint account" in text
        assert "You chose to file the grant yourself" in " ".join(doc["next_steps"])
        asked = answers()
        asked["account"] = {"who_files": "I want the firm to file it for me"}
        asked_doc = c.get(f"/api/drafts/{c.post('/api/drafts', json={'service': 'probate', 'answers': asked}).json()['id']}/document").json()
        assert "asked the firm to file" in " ".join(asked_doc["next_steps"])
        assert "cannot sign in to HMCTS" in " ".join(asked_doc["next_steps"])
        assert any("applying-for-probate" in s["url"] for s in doc["sources"])
        blocked = c.post("/api/drafts", json={"service": "probate", "answers": answers(will={"applicant_role": "Unmarried partner", "has_will": "No"})}).json()
        assert c.get(f"/api/drafts/{blocked['id']}/document").status_code == 400
