import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

WILL = {
    "about_you": {"full_name": "Ada Lovelace", "date_of_birth": "1980-12-10", "address": "1 High St, London", "email": "ada@example.com", "marital_status": "Married"},
    "executors": {"executors": [{"full_name": "Charles Babbage", "address": "2 High St, London", "relationship": "Friend"}]},
    "guardians": {},
    "gifts": {"gifts": [{"gift": "my piano", "beneficiary": "Mary Somerville"}]},
    "residue": {"residuary_beneficiaries": [{"full_name": "Byron King", "share": "1"}, {"full_name": "Anne King", "share": "1"}], "substitution": "Their children take their share"},
    "wishes": {"funeral_wishes": "Cremation"},
}


def test_services_and_health():
    with TestClient(app) as client:
        assert client.get("/healthz").json()["ok"] is True
        assert {s["id"] for s in client.get("/api/services").json()} == {"will", "lpa_property", "lpa_health", "probate"}
        assert client.get("/").status_code == 200
        assert client.get("/static/videos/will_intro.mp4").status_code == 200


def test_will_flow_to_pdf_and_review():
    with TestClient(app) as client:
        draft = client.post("/api/drafts", json={"service": "will", "answers": {}}).json()
        assert draft["missing"]
        assert client.get(f"/api/drafts/{draft['id']}/pdf").status_code == 400
        saved = client.put(f"/api/drafts/{draft['id']}", json={"answers": WILL}).json()
        assert saved["missing"] == []
        doc = client.get(f"/api/drafts/{draft['id']}/document").json()
        text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
        assert "revoke all my earlier wills" in text and "Byron King (beneficiary): 50%" in text and "my piano" in text
        pdf = client.get(f"/api/drafts/{draft['id']}/pdf")
        assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
        assert client.post(f"/api/drafts/{draft['id']}/submit").json()["status"] == "submitted_for_review"
        assert client.put(f"/api/drafts/{draft['id']}", json={"answers": WILL}).status_code == 409
