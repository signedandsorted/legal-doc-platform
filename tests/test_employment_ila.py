import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.guides import SERVICES


def test_employment_settlement_ila_registered():
    svc = SERVICES.get("employment_settlement_ila")
    assert svc is not None, "employment_settlement_ila service not registered"
    # basic fields present
    assert svc["title"].startswith("Employment settlement")
    step_ids = [s["id"] for s in svc["steps"]]
    expected = ["upload", "questionnaire", "quote", "conflict", "booking", "certificate"]
    for eid in expected:
        assert eid in step_ids, f"step {eid} missing in employment_settlement_ila"


def test_employment_settlement_ila_not_listed_publicly():
    """ILA stays registered but off the public services list."""
    svc = SERVICES.get("employment_settlement_ila")
    assert svc is not None
    assert svc.get("hidden") is True
