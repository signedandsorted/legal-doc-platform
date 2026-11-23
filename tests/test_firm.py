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


def test_one_ledger_feeds_the_accounts_the_forms_and_the_draft():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={
            "kind": "probate", "client_name": "Ann Executor", "client_email": "ann@example.com",
            "deceased_name": "John Executor", "date_of_death": "2026-01-15",
        }).json()
        draft = c.post(f"/api/firm/matters/{matter['id']}/draft").json()
        saved = c.patch(f"/api/firm/matters/{matter['id']}", json={"books": {
            "lines": [
                {"name": "House", "value": 400000, "ownership": "sole"},
                {"name": "Bank", "holder": "Example Bank", "value": 10000},
                {"name": "Joint house", "value": 200000, "ownership": "joint_tenants"},
                {"name": "Card", "side": "debt", "value": 5000},
                {"name": "Funeral", "side": "debt", "funeral": True, "value": 4000},
            ],
            "people": [{"name": "Ann Executor", "share": 100}],
            "case": {"has_will": "Yes, I have the original", "applicant_role": "Executor named in the will or a codicil", "domicile": "Yes"},
        }})
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["figures"]["gross_iht"] == 610000
        assert body["figures"]["gross_probate"] == 410000
        assert body["figures"]["net_probate"] == 401000
        assert body["figures"]["net_iht"] == 601000
        assert body["figures"]["tax"] == 110400
        assert body["accounts"]["totals"]["still_to_collect"] == 410000
        assert body["accounts"]["totals"]["expected_net"] == 290600
        assert body["accounts"]["people"][0]["entitlement"] == 290600
        codes = [s["code"] for s in body["forms"]["schedule"]]
        assert "PA1P" in codes and "IHT400" in codes
        assert body["accounts"]["outside"][0]["name"] == "Joint house"
        assert body["accounts"]["step"]["capital_totals"]["balance"] == 290600
        assert any(s["code"].startswith("IHT400 · Houses") for s in body["forms"]["schedule"])
        assert any(d["id"] == "banks" and "mylostaccount.org.uk" in d["url"] for d in body["books"]["discovery"])
        account = c.get(f"/api/firm/matters/{matter['id']}/account.pdf")
        assert account.status_code == 200 and account.content.startswith(b"%PDF")
        editable = c.get(f"/api/firm/matters/{matter['id']}/account.html")
        assert b"Balance of capital" in editable.content
        found = c.get(f"/api/firm/matters/{matter['id']}/search?q=Example")
        assert found.json()["items"][0]["label"] == "Bank"
        books = found.json() and body["books"]
        books["notice"] = {"placed_on": "2026-01-15", "claims_to": "Example Firm, 1 High Street"}
        noted = c.patch(f"/api/firm/matters/{matter['id']}", json={"books": books})
        assert noted.status_code == 200, noted.text
        dates = {d["label"]: d["date"] for d in noted.json()["deadlines"]}
        assert dates["Section 27 notice: last day for claims"] == "2026-03-15"
        notice = c.post(f"/api/firm/matters/{matter['id']}/letters", json={"kind": "notice"})
        assert "Trustee Act 1925" in notice.json()["letter"]["body"]
        assert "John Executor" in notice.json()["letter"]["body"]
        letter = c.post(f"/api/firm/matters/{matter['id']}/letters", json={"kind": "bank"})
        assert "Example Bank" in letter.json()["letter"]["body"]
        answers = c.get(f"/api/drafts/{draft['draft_id']}").json()["answers"]
        assert answers["estate"]["funeral_costs"] == 4000
        assert answers["estate"]["assets"][0]["value"] == 400000
        exported = c.get(f"/api/firm/matters/{matter['id']}/export")
        assert exported.status_code == 200
        assert exported.json()["answers"]["deceased"]["full_name"] == "John Executor"


def test_uploaded_papers_fill_the_estate_and_nothing_is_filed():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor", "date_of_death": "2026-01-15"}).json()
        upload = c.post(
            f"/api/firm/matters/{matter['id']}/uploads",
            data={"kind": "Bank or valuation letter"},
            files={"file": ("bank.txt", "Barclays current account: £10,000.00\n", "text/plain")},
        )
        assert upload.status_code == 200, upload.text
        suggestion = upload.json()["suggestions"][0]
        applied = c.post(f"/api/firm/matters/{matter['id']}/apply", json={"suggestion_ids": [suggestion["id"]]})
        assert applied.status_code == 200, applied.text
        assert applied.json()["figures"]["gross_probate"] == 10000
        assert "death certificate" in " ".join(applied.json()["filing"]["blockers"]).lower()
        assert applied.json()["filing"]["hmcts"]["ready"] is False
        death = c.post(
            f"/api/firm/matters/{matter['id']}/uploads",
            data={"kind": "Death certificate"},
            files={"file": ("death.txt", "Certified copy of an entry of death. Date of death: 15 January 2026\n", "text/plain")},
        )
        assert death.status_code == 200
        pack = c.get(f"/api/firm/matters/{matter['id']}/pack")
        assert pack.status_code == 200
        assert pack.content.startswith(b"%PDF")
        recorded = c.patch(f"/api/firm/matters/{matter['id']}", json={"hmrc_code": "", "grant_filed_on": "2026-04-01", "grant_reference": "PR-1"})
        assert recorded.json()["filing"]["hmrc"]["grant_filed_on"] == "2026-04-01"
        assert "does not" in recorded.json()["filing"]["notice"].lower() or "Nothing" in recorded.json()["filing"]["notice"]
    with user_client() as c:
        assert c.post(f"/api/firm/matters/{matter['id']}/uploads", files={"file": ("x.txt", b"no", "text/plain")}).status_code == 403


