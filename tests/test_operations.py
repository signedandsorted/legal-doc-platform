"""Every letter the desk offers, and the buttons that write them, produce a file."""
from tests.helpers import admin_client

LETTERS = [
    "lex_care", "lex_quote", "lex_progress", "lex_change", "lex_complaint", "lex_review", "lex_undertaking", "lex_conflict",
    "act1975", "golden", "couple", "file_summary", "old_will", "retainer",
    "bank", "beneficiary", "grant", "notice", "credit", "estatesearch",
    "will_ipw", "will_sww", "will_probate", "will_local", "pension",
]


def test_every_letter_and_the_main_desk_paths():
    with admin_client() as c:
        home = c.get("/")
        assert home.status_code == 200
        assert "England and Wales" in home.text and "United States" in home.text
        assert c.get("/firm").status_code == 200
        services = {row["id"] for row in c.get("/api/services").json()}
        assert {"will", "probate", "us_will", "us_trust"} <= services

        opened = c.post("/api/firm/matters", json={
            "kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor", "date_of_death": "2026-01-15",
        })
        assert opened.status_code == 200, opened.text
        matter = opened.json()
        mid = matter["id"]
        quoted = c.post(f"/api/firm/matters/{mid}/lexcel", json={"quote": {
            "fee": "900", "fee_earner": "Ada Stone", "fee_earner_status": "Solicitor",
            "supervisor": "Sam Partner", "supervisor_status": "Partner", "objectives": "Get the grant",
        }, "conflict_q": "John Executor"})
        assert quoted.status_code == 200

        made = []
        for kind in LETTERS:
            letter = c.post(f"/api/firm/matters/{mid}/letters", json={"kind": kind})
            assert letter.status_code == 200, (kind, letter.text)
            body = letter.json()["letter"]
            assert body["title"] and body["body"], kind
            made.append(body["title"])
        assert "900" in c.post(f"/api/firm/matters/{mid}/letters", json={"kind": "lex_quote"}).json()["letter"]["body"]

        saved = c.get(f"/api/firm/matters/{mid}").json()["books"]["letters"]
        assert len(saved) >= len(LETTERS)
        sample = saved[-1]
        pdf = c.get(f"/api/firm/matters/{mid}/letters/{sample['id']}.pdf")
        docx = c.get(f"/api/firm/matters/{mid}/letters/{sample['id']}.docx")
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
        assert docx.status_code == 200 and docx.content[:2] == b"PK"

        trust = c.post("/api/firm/matters", json={"kind": "trust", "client_name": "The Trustees", "title": "Family trust"})
        assert trust.status_code == 200, trust.text
        added = c.patch(f"/api/firm/matters/{trust.json()['id']}", json={"trust": {"lines": [{"name": "House", "pot": "capital", "amount": 10}]}})
        assert added.status_code == 200
        assert added.json()["trust"]["capital"]["balance"] == 10

        deputy = c.post("/api/firm/matters", json={"kind": "deputyship", "client_name": "The deputy", "title": "Deputyship"})
        assert deputy.status_code == 200
        paid = c.patch(f"/api/firm/matters/{deputy.json()['id']}", json={"deputy": {"lines": [{"name": "Care", "pot": "money", "out": "Yes", "amount": 25}]}})
        assert paid.status_code == 200
        assert paid.json()["deputy"]["money"]["balance"] == -25

        unknown = c.post(f"/api/firm/matters/{mid}/letters", json={"kind": "not-a-letter"})
        assert unknown.status_code == 400
        assert made
