"""A UK trust can be prepared for HMRC's service. The site does not register it."""
from tests.helpers import admin_client, user_client

LIFE = {
    "exists": {"when": "It is a lifetime trust and the deed has been signed", "express": "Yes, it was set up on purpose"},
    "rule": {"tax": "No", "exclusion": "None", "created": "2026-11-01"},
    "people": {"name": "The Nora Trust", "settlor": "Nora Client", "trustees": "Nora Client, lead trustee", "beneficiaries": "Her children", "assets": "The house"},
    "done": {},
}


def test_a_lifetime_trust_needs_hmrc_and_a_will_trust_does_not_yet():
    with user_client() as c:
        services = {row["id"] for row in c.get("/api/services").json()}
        assert "trust_register" in services
        draft = c.post("/api/drafts", json={"service": "trust_register", "answers": LIFE}).json()
        doc = c.get(f"/api/drafts/{draft['id']}/document").json()
        text = " ".join(p for section in doc["sections"] for p in section["paragraphs"])
        assert "not register the trust" in text.lower() or "does not register" in text.lower()
        assert "90 days" in text
        alive = dict(LIFE)
        alive["exists"] = {"when": "It is in my will and I am still alive", "express": "Yes, it was set up on purpose"}
        waiting = c.post("/api/drafts", json={"service": "trust_register", "answers": alive}).json()
        waiting_text = " ".join(p for section in c.get(f"/api/drafts/{waiting['id']}/document").json()["sections"] for p in section["paragraphs"])
        assert "not registered now" in waiting_text


def test_a_firm_trust_file_starts_the_pack():
    with admin_client() as c:
        opened = c.post("/api/firm/matters", json={"kind": "trust", "client_name": "The trustees", "title": "Family trust"})
        assert opened.status_code == 200, opened.text
        started = c.post(f"/api/firm/matters/{opened.json()['id']}/trust-register")
        assert started.status_code == 200, started.text
        assert started.json()["draft_id"]
