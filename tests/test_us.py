"""United States documents follow the state. They are not England and Wales forms."""
from app.doc_us import build_us, us_issues
from app.payments import quote


def _about(state):
    return {"about": {"full_name": "Ada King", "date_of_birth": "1980-01-01", "state": state, "county": "King",
                      "address": "1 Main", "marital": "Married", "spouse": "Charles King", "has_children": "No",
                      "owns_home": "Yes", "outside": True}}


def test_prices_are_in_dollars():
    assert quote("us_will")["label"] == "$129" and quote("us_will")["currency"] == "usd"
    assert quote("us_trust")["label"] == "$299"
    assert quote("will")["currency"] == "gbp"


def test_california_will_uses_two_witnesses_and_community_property():
    doc = build_us("us_will", {**_about("California"), "people": {"primary": {"full_name": "Grace Hopper"}}, "gifts": {"residue": "my children, equally"}})
    text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
    assert "two adult witnesses" in text
    assert "community-property" in text
    assert "not an England and Wales" in text
    assert us_issues("us_will", _about("California")) == []


def test_louisiana_is_not_a_common_law_will():
    doc = build_us("us_will", _about("Louisiana"))
    text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
    assert "not a Louisiana notarial testament" in text
    assert any("Do not sign" in i["message"] for i in us_issues("us_will", _about("Louisiana")))


def test_pennsylvania_does_not_pretend_witnesses_are_the_only_rule():
    doc = build_us("us_will", _about("Pennsylvania"))
    text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
    assert "even with no witnesses" in text
    assert "safer" in text


def test_a_trust_does_not_claim_the_house_is_already_in_it():
    answers = {**_about("Texas"), "people": {"primary": {"full_name": "Grace Hopper"}}, "gifts": {"residue": "my spouse", "funded": True, "home": "1 Main, Austin"}}
    text = " ".join(p for s in build_us("us_trust", answers)["sections"] for p in s["paragraphs"])
    assert "does not change a deed" in text
    assert "pour-over" in text.lower() or "Pour-over" in text or "pour-over will" in text
