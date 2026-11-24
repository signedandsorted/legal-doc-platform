from app.doc_probate import plan, values
from app.guide_probate import PROBATE
from app.integrations.companies_house import apply_companies_house_matches
from tests.test_probate import answers


def test_guide_has_companies_house_step():
    step = next(s for s in PROBATE["steps"] if s["id"] == "companies_house")
    assert step["title"] == "Check Companies House"
    assert step["video"] == "probate_estate"  # reuse existing clip; do not invent a new render
    assert any("does not file or submit" in g for g in step["guidance"])


def test_ticked_officers_join_asset_checklist():
    a = answers(estate={"assets": [{"description": "Bank", "value": "200000", "ownership": "Owned on their own"}], "debts": [], "funeral_costs": "0"})
    a["companies_house"] = {"officers": [
        {"name": "Jane Smith", "dob_month_year": "4/1952", "appointments": "Example Ltd (director)", "match": True},
        {"name": "Other Person", "appointments": "Other Ltd", "match": False},
    ]}
    out = apply_companies_house_matches(a)
    descs = [x["description"] for x in out["estate"]["assets"]]
    assert "Bank" in descs
    assert "Companies House: Jane Smith — Example Ltd (director)" in descs
    assert all("Other Person" not in d for d in descs)
    again = apply_companies_house_matches(out)
    assert descs == [x["description"] for x in again["estate"]["assets"]]


def test_plan_includes_matched_company_interest():
    a = answers(estate={"assets": [{"description": "Bank", "value": "200000", "ownership": "Owned on their own"}], "debts": [], "funeral_costs": "0"})
    a["companies_house"] = {"officers": [
        {"name": "Jane Smith", "appointments": "Example Ltd (director)", "match": True},
    ]}
    v = values(a)
    assert v["gross_iht"] >= 200000
    p = plan(a)
    assert p
