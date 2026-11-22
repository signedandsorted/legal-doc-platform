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
        assert {s["id"] for s in client.get("/api/services").json()} == {"will", "lpa_property", "lpa_health", "poa_ordinary", "probate", "prenup", "postnup", "cohabitation", "employment_settlement"}
        assert client.get("/").status_code == 200
        svc = client.get("/api/services/will").json()
        assert [s["id"] for s in svc["steps"]] == ["intro", "about_you", "family", "executors", "gifts", "residue", "trusts", "business", "extras", "documents"]
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
                assert v is None or (".mp4" in v["src"].split("?")[0] and client.get(v["src"]).status_code == 200)
                if v:
                    assert "presenters" in v
                    for p in v["presenters"]:
                        assert p["id"] in ("female", "male") and ".mp4" in p["src"].split("?")[0]
                        assert client.get(p["src"]).status_code == 200


def test_frontend_has_accounts_admin_and_ai_label():
    with user_client() as client:
        html, js = client.get("/").text, client.get("/static/app.js").text
        assert 'id="acct"' in html
        assert "X-CSRF-Token" in js and "#/login" in js and "/api/admin/" in js
        assert "Your reference number" not in js  # no more reference-number-only access
        assert "AI-generated video: the presenter is not a real person and the voice is an AI-generated voice" in js
        assert "Choose a presenter" in js and "ldp-presenter" in js


def test_index_sets_csrf_cookie_and_page_paths_serve_the_app():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert c.cookies.get("sas_csrf")
        assert "no-store" in r.headers.get("cache-control", "").lower() or "no-cache" in r.headers.get("cache-control", "").lower()
        js = c.get("/static/app.js")
        assert js.status_code == 200 and "ensureCsrf" in js.text
        cc = js.headers.get("cache-control", "").lower()
        assert "no-store" in cc or "no-cache" in cc
        for path in ("/wills", "/lpa", "/login", "/admin"):
            page = c.get(path)
            assert page.status_code == 200, path
            assert "text/html" in page.headers.get("content-type", "")
            assert "/static/app.js" in page.text
        missing = c.get("/api/definitely-missing")
        assert missing.status_code == 404
        assert missing.headers.get("content-type", "").startswith("application/json")


def test_start_button_is_visible_and_assets_are_cache_busted():
    import hashlib
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import app

    js_ver = hashlib.sha256(Path("static/app.js").read_bytes()).hexdigest()[:12]
    css_ver = hashlib.sha256(Path("static/styles.css").read_bytes()).hexdigest()[:12]
    with TestClient(app) as c:
        for path in ("/", "/wills", "/lpa", "/login"):
            r = c.get(path)
            assert r.status_code == 200, path
            assert "text/html" in r.headers.get("content-type", "")
            assert "no-store" in r.headers.get("cache-control", "").lower()
            assert f"/static/app.js?v={js_ver}" in r.text
            assert f"/static/styles.css?v={css_ver}" in r.text
        js = c.get(f"/static/app.js?v={js_ver}")
        assert js.status_code == 200
        text = js.text
        assert "data-start=" in text
        assert "function goToSignIn" in text and "function bindStart" in text
        assert "Please create an account or sign in" in text
        assert "Starting…" in text
        # logged-out Start must not silently no-op: it shows a sign-in page
        assert 'location.hash = dest' in text or "goToSignIn(" in text



def test_security_headers_on_pages_and_api():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        for path in ("/", "/login", "/api/services", "/healthz"):
            r = c.get(path)
            assert r.status_code == 200, path
            csp = r.headers.get("content-security-policy", "")
            assert "default-src 'self'" in csp, path
            assert "frame-ancestors 'none'" in csp, path
            assert "media-src 'self' blob:" in csp, path
            assert r.headers.get("x-frame-options") == "DENY", path
            assert r.headers.get("x-content-type-options") == "nosniff", path
            assert r.headers.get("referrer-policy") == "same-origin", path


def test_app_js_rejects_prototype_polluting_form_keys():
    from pathlib import Path
    text = Path("static/app.js").read_text(encoding="utf-8")
    assert "function safeFormKey" in text
    assert '"__proto__"' in text and '"constructor"' in text and '"prototype"' in text



def test_will_business_step_is_a_solicitor_placeholder():
    from tests.helpers import user_client
    with user_client() as client:
        a = {**WILL, "business": {"owns_business": "Yes", "business_type": "Partnership", "business_details": "Smith & Co, leave my share to Byron King", "talked_to_co_owners": "Not yet", "has_agreement": "Not sure", "separate_planning": "Yes"}}
        d = client.post("/api/drafts", json={"service": "will", "answers": a}).json()
        msgs = " ".join(i["message"] for i in d["issues"])
        assert "Business Relief" in msgs and "co-owners" in msgs
        doc = client.get(f"/api/drafts/{d['id']}/document").json()
        text = " ".join(p for s in doc["sections"] for p in s["paragraphs"])
        assert "Smith & Co" in text and "For solicitor drafting" in text
        assert "Business Relief" in " ".join(n for s in doc["sections"] for n in (s.get("notes") or [])) or "Business Relief" in text
