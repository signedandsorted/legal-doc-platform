import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient  # noqa: E402,F401

from app.main import app  # noqa: E402,F401
from tests.helpers import user_client  # noqa: E402

WILL = {
    "about_you": {"full_name": "Ada Lovelace", "date_of_birth": "1980-12-10", "address": "1 High St, London", "email": "ada@example.com", "marital_status": "Married", "domicile": "England or Wales"},
    "family": {"children": [{"full_name": "Byron King", "date_of_birth": "2015-01-01"}], "guardians": [{"full_name": "Mary Somerville", "address": "9 Park Rd"}]},
    "executors": {"executors": [{"full_name": "Charles Babbage", "address": "2 High St, London", "relationship": "Friend"}], "professional_executor": "Yes", "digital_executor": {"full_name": "Grace Hopper", "address": "5 Lane"}},
    "gifts": {"gifts": [{"type": "An item", "gift": "my piano", "beneficiary": "Mary Somerville"},
                        {"type": "A gift to charity", "gift": "£5,000", "beneficiary": "Cancer Research UK", "charity_number": "1089464"},
                        {"type": "My pet, with money for its care", "gift": "my dog Rex", "beneficiary": "Grace Hopper", "pet_money": "2000"}]},
    "residue": {"residuary_beneficiaries": [{"full_name": "Byron King", "share": "1"}, {"full_name": "Anne King", "share": "1"}], "inherit_age": "25", "substitution": "Their children take their share"},
    "trusts": {"life_interest": "Yes, over my share of my home", "life_tenant": "William King", "vulnerable_beneficiary": "Anne King"},
    "extras": {"funeral_wishes": "Cremation", "organ_donation": "I wish to donate my organs and tissue", "loans_forgiven": "£2,000 lent to my brother", "exclude_person": "Yes", "exclusion_name": "Ralph King", "exclusion_reason": "We have not spoken for 20 years", "letter_of_wishes": "Look after the garden."},
}


def test_services_and_health():
    with user_client() as client:
        assert client.get("/healthz").json()["ok"] is True
        assert {s["id"] for s in client.get("/api/services").json()} == {"will", "lpa_property", "lpa_health", "probate"}
        assert client.get("/").status_code == 200
        svc = client.get("/api/services/will").json()
        assert [s["id"] for s in svc["steps"]] == ["intro", "about_you", "family", "executors", "gifts", "residue", "trusts", "extras", "documents"]
        assert all(s.get("sources") for s in svc["steps"])


def test_will_flow_to_pdf_and_review():
    with user_client() as client:
        draft = client.post("/api/drafts", json={"service": "will", "answers": {}}).json()
        assert draft["missing"]
        assert client.get(f"/api/drafts/{draft['id']}/pdf").status_code == 400
        saved = client.put(f"/api/drafts/{draft['id']}", json={"answers": WILL}).json()
        assert saved["missing"] == []
        doc = client.get(f"/api/drafts/{draft['id']}/document").json()
        will = doc["sections"][0]
        text = " ".join(will["paragraphs"])
        for phrase in ("revoke all my earlier wills", "Byron King (beneficiary): 50%", "my piano", "may charge", "digital executor",
                       "guardian", "registered charity number 1089464", "my dog Rex", "for the rest of their life", "reach the age of 25",
                       "means-tested benefits", "release the following debts", "cremated", "donate my organs"):
            assert phrase in text, phrase
        assert len(will["notes"]) == len(will["paragraphs"])
        heads = [s["heading"] for s in doc["sections"]]
        assert any(h.startswith("Statement of reasons") for h in heads) and any(h.startswith("Letter of wishes") for h in heads)
        assert "Ralph King" not in text
        pdf = client.get(f"/api/drafts/{draft['id']}/pdf")
        assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
        assert client.post(f"/api/drafts/{draft['id']}/submit").json()["status"] == "submitted_for_review"
        assert client.put(f"/api/drafts/{draft['id']}", json={"answers": WILL}).status_code == 409


def test_will_conditional_questions_and_issues():
    with user_client() as client:
        a = {**WILL, "about_you": {**WILL["about_you"], "expecting_marriage": "Yes", "domicile": "Outside the UK", "assets_abroad": "Yes, and I have a separate will there"}, "family": {"children": [{"full_name": "Kid", "date_of_birth": "2020-01-01"}]}}
        d = client.post("/api/drafts", json={"service": "will", "answers": a}).json()
        assert any("future spouse" in m for m in d["missing"])
        msgs = " ".join(i["message"] for i in d["issues"])
        assert "outside England and Wales" in msgs and "assets abroad" in msgs and "not named guardians" in msgs
        a["about_you"]["partner_name"] = "Charles Babbage"
        d = client.put(f"/api/drafts/{d['id']}", json={"answers": a}).json()
        assert d["missing"] == []
        text = " ".join(client.get(f"/api/drafts/{d['id']}/document").json()["sections"][0]["paragraphs"])
        assert "expecting to marry" in text and "so far as they relate to my property in England and Wales" in text


def test_discretionary_trust_replaces_fixed_shares():
    with user_client() as client:
        a = {**WILL, "trusts": {"discretionary": "Yes"}}
        d = client.post("/api/drafts", json={"service": "will", "answers": a}).json()
        text = " ".join(client.get(f"/api/drafts/{d['id']}/document").json()["sections"][0]["paragraphs"])
        assert "discretionary trust" in text and "50%" not in text


def test_will_upload_suggests_old_executors():
    with user_client() as client:
        d = client.post("/api/drafts", json={"service": "will", "answers": {}}).json()
        txt = b"This is the last will of me, I, Ada Mary Lovelace, of 1 High St. I appoint Charles Babbage of 2 Low Rd to be my executor."
        r = client.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("old-will.txt", txt, "text/plain")}).json()
        assert r["kind"] == "Old will"
        assert {"step": "executors", "field": "executors"}.items() <= [s for s in r["suggestions"] if s["mode"] == "append"][0].items()


def test_frontend_assets_and_video_metadata():
    with user_client() as client:
        html = client.get("/").text
        assert "/static/app.js" in html and "Wills · Powers of attorney · Probate" in html
        assert client.get("/static/app.js").status_code == 200 and client.get("/static/styles.css").status_code == 200
        for sid in ("will", "lpa_property", "lpa_health", "probate"):
            svc = client.get(f"/api/services/{sid}").json()
            for st in svc["steps"]:
                v = st["video"]
                assert v is None or (v["src"].endswith(".mp4") and client.get(v["src"]).status_code == 200)
