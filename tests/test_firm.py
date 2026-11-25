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
        book = c.get(f"/api/firm/matters/{matter['id']}/account.xlsx")
        assert book.status_code == 200, book.text
        assert book.content[:2] == b"PK"
        assert "estate account.xlsx" in book.headers["content-disposition"]

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
        filled = c.get(f"/api/firm/matters/{matter['id']}/iht400.pdf")
        assert filled.status_code == 200 and filled.content.startswith(b"%PDF")
        from pypdf import PdfReader
        import io
        got = PdfReader(io.BytesIO(filled.content)).get_fields()
        assert str(got["IHT400_01_01"].get("/V")) == "Executor"
        assert "400,000.00" in str(got["IHT400_164"].get("/V"))
        codes_chosen = {item["code"] for item in body["forms"]["chosen"]}
        assert "IHT405" in codes_chosen and "IHT406" in codes_chosen
        packed = c.get(f"/api/firm/matters/{matter['id']}/schedules.zip")
        assert packed.status_code == 200
        import zipfile
        archive = zipfile.ZipFile(io.BytesIO(packed.content))
        assert "IHT406.pdf" in archive.namelist()
        bank = PdfReader(io.BytesIO(archive.read("IHT406.pdf"))).get_fields()
        assert "John Executor" in str(bank["IHT406_01"].get("/V"))
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
        assert dates["Section 27 notice: last day for claims"] == "2026-03-16"  # two months + one day
        notice = c.post(f"/api/firm/matters/{matter['id']}/letters", json={"kind": "notice"})
        assert "Trustee Act 1925" in notice.json()["letter"]["body"]
        assert "John Executor" in notice.json()["letter"]["body"]
        asked = c.post(f"/api/firm/matters/{matter['id']}/letters", json={"kind": "credit"})
        assert "death certificate" in asked.json()["letter"]["body"]
        report = c.post(
            f"/api/firm/matters/{matter['id']}/uploads",
            data={"kind": "Credit report"},
            files={"file": ("experian.txt", "Experian credit report. Barclays card: £500.00\n", "text/plain")},
        )
        assert report.status_code == 200, report.text
        assert any("500" in s["label"] for s in report.json()["suggestions"])
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


def test_asset_search_records_a_fee_and_does_not_repeat_a_letter():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor", "date_of_death": "2026-01-15"}).json()
        first = c.post(f"/api/firm/matters/{matter['id']}/asset-search", json={"fee": 150, "targets": ["barclays", "nsandi"]})
        assert first.status_code == 200, first.text
        body = first.json()
        assert body["books"]["asset_search"]["fee"] == 150
        assert body["books"]["asset_search"]["paid"] is False
        titles = [letter["title"] for letter in body["books"]["letters"]]
        assert any("Barclays" in title for title in titles) and any("NS&I" in title for title in titles)
        second = c.post(f"/api/firm/matters/{matter['id']}/asset-search", json={"fee": 150, "paid": True, "targets": ["barclays"]})
        assert second.status_code == 200
        assert len(second.json()["books"]["letters"]) == len(titles)
        assert second.json()["books"]["asset_search"]["paid"] is True


def test_the_firm_can_add_or_remove_a_schedule():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor", "date_of_death": "2026-01-15"}).json()
        c.post(f"/api/firm/matters/{matter['id']}/draft")
        saved = c.patch(f"/api/firm/matters/{matter['id']}", json={"books": {
            "lines": [{"name": "House", "value": 400000}, {"name": "Bank", "value": 10000}],
            "case": {"has_will": "Yes, I have the original", "domicile": "Yes"},
        }})
        books = saved.json()["books"]
        books["form_choice"] = {"off": ["IHT406"], "on": ["IHT407"]}
        changed = c.patch(f"/api/firm/matters/{matter['id']}", json={"books": books})
        codes = {item["code"] for item in changed.json()["forms"]["chosen"]}
        assert "IHT405" in codes and "IHT406" not in codes and "IHT407" in codes
        packed = c.get(f"/api/firm/matters/{matter['id']}/schedules.zip")
        import zipfile
        import io
        names = zipfile.ZipFile(io.BytesIO(packed.content)).namelist()
        assert "IHT406.pdf" not in names and "IHT407.pdf" in names and "IHT405.pdf" in names


def test_a_credit_report_is_ticked_onto_the_estate_and_the_fee_is_a_cost():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor", "date_of_death": "2026-01-15"}).json()
        saved = c.patch(f"/api/firm/matters/{matter['id']}", json={"books": {"credit": {"agency": "Estatesearch", "reference": "ES-100", "fee": 210}}, "bill": {"entries": []}})
        assert saved.json()["books"]["credit"]["reference"] == "ES-100"
        assert saved.json()["books"]["credit"]["fee"] == 210
        billed = c.patch(f"/api/firm/matters/{matter['id']}", json={"bill": {"entries": [{"kind": "cost", "what": "Estatesearch search ES-100", "amount": 210}]}})
        assert billed.json()["bill"]["costs"] == 210
        report = c.post(
            f"/api/firm/matters/{matter['id']}/uploads",
            data={"kind": "Credit report"},
            files={"file": ("estatesearch.txt", "Estatesearch report\nBarclays current account balance £1,200.00\nHSBC credit card balance £300.00\n", "text/plain")},
        )
        assert report.status_code == 200, report.text
        picks = {item["label"]: item for item in report.json()["suggestions"]}
        bank = next(item for item in picks.values() if "1,200" in item["label"])
        card = next(item for item in picks.values() if "300" in item["label"])
        assert bank["value"]["side"] == "asset" and card["value"]["side"] == "debt"
        applied = c.post(f"/api/firm/matters/{matter['id']}/apply", json={"suggestion_ids": [bank["id"]]})
        assert applied.status_code == 200, applied.text
        assert applied.json()["figures"]["gross_probate"] == 1200
        names = [line["name"] for line in applied.json()["books"]["lines"]]
        assert any("Barclays" in name for name in names)
        assert not any("HSBC" in name for name in names)



def test_a_repeated_name_is_shown_and_the_practice_file_is_kept():
    with admin_client() as c:
        first = c.post("/api/firm/matters", json={"kind": "will", "client_name": "Ann Executor"}).json()
        second = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Ann Executor", "deceased_name": "John Executor"}).json()
        hits = c.get(f"/api/firm/matters/{second['id']}/conflicts")
        assert hits.status_code == 200
        assert first["id"] in {row["id"] for row in hits.json()["matches"]}
        saved = c.patch(f"/api/firm/matters/{second['id']}", json={"practice": {"identity": "Seen", "will_held": "With the firm", "will_ref": "Safe 4", "risk": "Higher", "source": "Sale of the house"}})
        practice = saved.json()["practice"]
        assert practice["identity"] == "Seen" and practice["will_ref"] == "Safe 4" and practice["risk"] == "Higher"


def test_firm_accounts_a_trust_and_a_deputyship_stay_separate():
    with admin_client() as c:
        matter = c.post("/api/firm/matters", json={"kind": "trust", "client_name": "The trustees", "title": "King trust"}).json()
        assert matter["kind_label"] == "Trust"
        assert any(stage["id"] == "money" for stage in matter["stages"])
        saved = c.patch(f"/api/firm/matters/{matter['id']}", json={
            "trust": {"lines": [{"name": "House", "pot": "capital", "amount": 1000}, {"name": "Rent", "pot": "income", "amount": 100, "out": "Yes"}]},
            "bill": {"entries": [{"kind": "time", "what": "Advice", "hours": 2, "rate": 250}, {"kind": "bill", "what": "Bill 1", "amount": 500}, {"kind": "paid", "what": "On account", "amount": 200}]},
        })
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["trust"]["capital"]["balance"] == 1000
        assert body["trust"]["income"]["balance"] == -100
        assert body["bill"]["unbilled"] == 0
        assert body["bill"]["outstanding"] == 300
        deputy = c.post("/api/firm/matters", json={"kind": "deputyship", "client_name": "Ada King"}).json()
        recorded = c.patch(f"/api/firm/matters/{deputy['id']}", json={"deputy": {"lines": [{"name": "Pension", "amount": 800}, {"name": "Care", "amount": 300, "out": "Yes"}]}})
        assert recorded.json()["deputy"]["money"]["balance"] == 500
        accounts = c.get("/api/firm/accounts").json()
        assert accounts["totals"]["outstanding"] == 300
        assert accounts["totals"]["paid"] == 200


def test_lexcel_requirements_are_on_the_file():
    with admin_client() as c:
        opened = c.post("/api/firm/matters", json={"kind": "will", "client_name": "Pat Client", "title": "Will of Pat Client"})
        assert opened.status_code == 200, opened.text
        matter = opened.json()
        clauses = {item["clause"]: item for item in matter["lexcel"]["items"]}
        assert "6.2" in clauses and "client-care letter" in clauses["6.2"]["desk"]
        assert "7.1" in clauses and "5.11" in clauses
        assert matter["lexcel"]["open"] == len(clauses)
        saved = c.post(f"/api/firm/matters/{matter['id']}/lexcel", json={"done": ["letter", "no-such"]})
        assert saved.status_code == 200
        again = {item["id"]: item["done"] for item in saved.json()["matter"]["lexcel"]["items"]}
        assert again["letter"] is True and again["strategy"] is False
        other = c.post("/api/firm/matters", json={"kind": "probate", "client_name": "Someone Else", "deceased_name": "Pat Client", "title": "Estate of Pat Client"})
        assert other.status_code == 200
        found = c.get(f"/api/firm/matters/{matter['id']}/conflicts", params={"q": "Pat Client"})
        assert found.status_code == 200
        assert any(hit["id"] == other.json()["id"] for hit in found.json()["matches"])
        quoted = c.post(f"/api/firm/matters/{matter['id']}/lexcel", json={"quote": {"fee": "450", "fee_earner": "Ada Stone", "fee_earner_status": "Solicitor"}})
        kept = {item["id"]: item["done"] for item in quoted.json()["matter"]["lexcel"]["items"]}
        assert kept["letter"] is True and quoted.json()["matter"]["lexcel"]["quote"]["fee"] == "450"
        letter = c.post(f"/api/firm/matters/{matter['id']}/letters", json={"kind": "lex_quote"})
        assert letter.status_code == 200, letter.text
        assert "450" in letter.json()["letter"]["body"] and "Costs estimate" in letter.json()["letter"]["title"]


