"""Firm desk is staff-only, and the public probate page shows what to have ready."""
from tests.helpers import admin_client, user_client


def test_clients_cannot_open_the_firm_desk():
    with user_client() as c:
        assert c.get("/api/firm/matters").status_code == 403
        assert c.get("/firm").status_code == 200
        assert "Firm desk" in c.get("/firm").text


def test_staff_run_a_probate_matter_and_the_public_list_matches():
    with admin_client() as c:
        opened = c.post("/api/firm/matters", json={
            "kind": "probate",
            "client_name": "Ann Executor",
            "client_email": "ann@example.com",
            "deceased_name": "John Executor",
            "date_of_death": "2026-01-15",
        })
        assert opened.status_code == 200, opened.text
        matter = opened.json()
        assert matter["title"] == "Estate of John Executor"
        assert matter["deadlines"][0]["date"] == "2026-07-31"
        assert matter["next"]["title"]
        first = matter["stages"][0]["items"][0]["id"]
        patched = c.patch(f"/api/firm/matters/{matter['id']}", json={"item_id": first, "item_status": "received", "grant_date": "2026-03-01"})
        assert patched.status_code == 200, patched.text
        assert patched.json()["deadlines"][1]["date"] == "2026-09-01"
        letter = c.post(f"/api/firm/matters/{matter['id']}/assist", json={"action": "request"})
        assert letter.status_code == 200
        assert "Death certificate" in letter.json()["letter"]["body"]
        assert "Ann Executor" in letter.json()["letter"]["body"]
        draft = c.post(f"/api/firm/matters/{matter['id']}/draft")
        assert draft.status_code == 200
        assert c.get(f"/api/drafts/{draft.json()['draft_id']}").status_code == 200
        again = c.post(f"/api/firm/matters/{matter['id']}/draft")
        assert again.json()["draft_id"] == draft.json()["draft_id"]

    with user_client() as c:
        probate = c.get("/api/services/probate").json()
        titles = [it["title"] for stage in probate["prepare"] for it in stage["items"]]
        assert "Death certificate" in titles
        assert "Identity of the client" not in titles
        html = c.get("/").text
        assert "/firm" in html
