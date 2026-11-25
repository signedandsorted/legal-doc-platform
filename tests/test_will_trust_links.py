import copy

from app.doc_will import build_will, will_issues
from app.guides import SERVICES
from tests.test_app import WILL

TRUSTS_URL = "https://www.gov.uk/trusts-taxes"


def test_trust_step_cites_govuk_trust_pages():
    step = next(s for s in SERVICES["will"]["steps"] if s["id"] == "trusts")
    urls = {s["url"] for s in step["sources"]}
    assert {TRUSTS_URL, "https://www.gov.uk/trusts-taxes/types-of-trust", "https://www.gov.uk/guidance/register-a-trust-as-a-trustee"} <= urls


def test_draft_with_a_trust_includes_govuk_link():
    doc = build_will(None, WILL)
    sec = next(s for s in doc["sections"] if s["heading"].startswith("Trust guidance from GOV.UK"))
    assert any(TRUSTS_URL in p for p in sec["paragraphs"])
    will_text = " ".join(doc["sections"][0]["paragraphs"])
    assert TRUSTS_URL not in will_text  # links never go into the will wording itself
    assert any(TRUSTS_URL in i["message"] for i in will_issues(WILL))


def test_draft_without_a_trust_has_no_trust_links():
    a = copy.deepcopy(WILL)
    a["trusts"] = {"life_interest": "No", "discretionary": "No"}
    doc = build_will(None, a)
    assert not any(s["heading"].startswith("Trust guidance") for s in doc["sections"])
