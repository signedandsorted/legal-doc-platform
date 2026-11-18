import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from sqlalchemy import select

from app.capacity import CONSENT, MAX_STATEMENT_BYTES, consent_hash, content_sha256, document_version_hash, looks_like_video
from app.db import capacity_statements, engine
from app.statement_crypto import decrypt, encrypt
from tests.helpers import admin_client, user_client
from tests.test_app import WILL
from tests.test_lpa import lpa


def webm(payload: bytes = b"supporting-statement") -> bytes:
    return b"\x1aE\xdf\xa3" + payload


def post_statement(client, draft_id, data=None, **fields):
    body = {
        "consent": "true",
        "confirmed": "true",
        "prompt_set_id": "will-banks-v-goodfellow-2026-11",
        "source": "camera",
        "duration_seconds": "45",
    }
    body.update(fields)
    return client.post(
        f"/api/drafts/{draft_id}/capacity-statements",
        files={"file": ("statement.webm", data or webm(), "video/webm")},
        data=body,
    )


def test_encrypt_roundtrip_and_tamper():
    plain = webm(b"hello-capacity")
    blob = encrypt(plain)
    assert not blob.startswith(plain)
    assert plain not in blob
    assert decrypt(blob) == plain
    damaged = blob[:-1] + bytes([blob[-1] ^ 1])
    try:
        decrypt(damaged)
        assert False, "tampered ciphertext should not decrypt"
    except ValueError:
        pass


def test_version_hash_is_stable():
    a = {"about_you": {"full_name": "Ada"}, "gifts": []}
    b = {"gifts": [], "about_you": {"full_name": "Ada"}}
    assert document_version_hash(a) == document_version_hash(b)
    assert document_version_hash(a) != document_version_hash({"about_you": {"full_name": "Bob"}})


def test_looks_like_video_accepts_webm_and_mp4():
    assert looks_like_video(webm(), "video/webm", "x.webm")
    assert looks_like_video(b"xxxxftypmp42" + b"0" * 8, "video/mp4", "x.mp4")
    assert not looks_like_video(b"MZ not a video", "application/octet-stream", "x.exe")
    assert not looks_like_video(b"short", "video/webm", "x.webm")


def test_will_guide_and_confirm_and_play():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "will", "answers": WILL}).json()
        guide = c.get(f"/api/drafts/{d['id']}/capacity-statement").json()
        assert guide["available"] is True
        assert guide["current"] is None
        assert "does not prove" in guide["disclaimer"]
        assert "UK GDPR" in guide["consent"]
        assert guide["consent_text_hash"] == consent_hash()
        assert CONSENT in guide["consent"] or guide["consent"] == CONSENT
        assert "Banks v Goodfellow" in guide["legal_basis"]
        ids = [p["id"] for p in guide["prompts"]]
        assert ids == ["identity", "nature_and_effect", "property", "claims", "free_choice"]
        assert all("Capacity Vault" not in p["text"] for p in guide["prompts"])
        assert "Capacity Vault" not in guide["title"]
        r = post_statement(c, d["id"], medical_assessment_interest="true")
        assert r.status_code == 200, r.text
        body = r.json()
        current = body["current"]
        assert current["is_current"] is True
        assert current["source"] == "camera"
        assert current["medical_assessment_interest"] is True
        assert current["matches_current_document"] is True
        assert current["document_version_hash"] == document_version_hash(WILL)
        assert current["content_sha256"] == content_sha256(webm())
        assert current["user_id"]
        assert current["ip"]
        played = c.get(f"/api/drafts/{d['id']}/capacity-statements/{current['id']}/video")
        assert played.status_code == 200
        assert played.content == webm()
        assert played.headers["x-content-sha256"] == current["content_sha256"]
        # ciphertext stays out of the metadata and is not stored in the clear
        with engine().connect() as conn:
            stored = conn.execute(select(capacity_statements.c.encrypted_data).where(capacity_statements.c.id == current["id"])).scalar_one()
        assert stored != webm()
        assert stored.startswith(b"SAS1")
        assert decrypt(stored) == webm()


def test_retake_keeps_history_and_marks_previous():
    first, second = webm(b"first-take............"), webm(b"second-take...........")
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "will", "answers": WILL}).json()
        a = post_statement(c, d["id"], data=first).json()["current"]["id"]
        b = post_statement(c, d["id"], data=second, source="upload").json()
        assert b["current"]["id"] != a
        assert b["current"]["source"] == "upload"
        hist = {s["id"]: s for s in b["history"]}
        assert hist[a]["is_current"] is False
        assert hist[b["current"]["id"]]["is_current"] is True
        assert c.get(f"/api/drafts/{d['id']}/capacity-statements/{a}/video").content == first
        assert c.get(f"/api/drafts/{d['id']}/capacity-statements/{b['current']['id']}/video").content == second


def test_rejects_without_consent_or_confirm_or_bad_file():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "will", "answers": WILL}).json()
        assert post_statement(c, d["id"], consent="false").status_code == 400
        assert post_statement(c, d["id"], confirmed="no").status_code == 400
        bad = c.post(
            f"/api/drafts/{d['id']}/capacity-statements",
            files={"file": ("note.txt", b"not a video at all!!", "text/plain")},
            data={"consent": "true", "confirmed": "true", "prompt_set_id": "will-banks-v-goodfellow-2026-11", "source": "upload"},
        )
        assert bad.status_code == 400
        huge = c.post(
            f"/api/drafts/{d['id']}/capacity-statements",
            files={"file": ("statement.webm", webm() + b"0" * (MAX_STATEMENT_BYTES), "video/webm")},
            data={"consent": "true", "confirmed": "true", "prompt_set_id": "will-banks-v-goodfellow-2026-11", "source": "camera"},
        )
        assert huge.status_code == 400


def test_stale_after_answers_change():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "will", "answers": WILL}).json()
        post_statement(c, d["id"])
        changed = {**WILL, "extras": {**WILL["extras"], "funeral_wishes": "Burial"}}
        assert c.put(f"/api/drafts/{d['id']}", json={"answers": changed}).status_code == 200
        guide = c.get(f"/api/drafts/{d['id']}/capacity-statement").json()
        assert guide["current"]["matches_current_document"] is False
        assert guide["document_version_hash"] != guide["current"]["document_version_hash"]


def test_other_user_and_anon_cannot_see_or_play():
    with user_client() as owner:
        d = owner.post("/api/drafts", json={"service": "will", "answers": WILL}).json()
        sid = post_statement(owner, d["id"]).json()["current"]["id"]
        path = f"/api/drafts/{d['id']}/capacity-statement"
        play = f"/api/drafts/{d['id']}/capacity-statements/{sid}/video"
        with user_client() as other:
            assert other.get(path).status_code == 404
            assert other.get(play).status_code == 404
            assert post_statement(other, d["id"]).status_code == 404
        # logged-out client from a new anonymous session
    from tests.helpers import anon_client
    with anon_client() as anon:
        assert anon.get(f"/api/drafts/{d['id']}/capacity-statement").status_code == 401
        assert anon.get(f"/api/drafts/{d['id']}/capacity-statements/{sid}/video").status_code == 401


def test_not_available_for_probate():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": {}}).json()
        assert c.get(f"/api/drafts/{d['id']}/capacity-statement").status_code == 404


def test_lpa_uses_mental_capacity_act_prompts():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "lpa_property", "answers": lpa()}).json()
        guide = c.get(f"/api/drafts/{d['id']}/capacity-statement").json()
        assert "Mental Capacity Act 2005" in guide["legal_basis"]
        assert guide["prompt_set_id"] == "lpa-mca-2005-ss2-3-2026-11"
        ids = [p["id"] for p in guide["prompts"]]
        assert "understand_retain_weigh" in ids
        r = post_statement(c, d["id"], prompt_set_id="lpa-mca-2005-ss2-3-2026-11")
        assert r.status_code == 200, r.text
        # will prompt set is rejected on an LPA
        assert post_statement(c, d["id"], prompt_set_id="will-banks-v-goodfellow-2026-11").status_code == 400


def test_admin_lists_and_plays_and_audit():
    with user_client() as c, admin_client() as adm:
        d = c.post("/api/drafts", json={"service": "will", "answers": {"about_you": {"full_name": "Zed Client"}}}).json()
        sid = post_statement(c, d["id"]).json()["current"]["id"]
        listed = adm.get("/api/admin/capacity-statements").json()
        match = [s for s in listed if s["id"] == sid]
        assert match and match[0]["owner_email"] == c.email
        detail = adm.get(f"/api/admin/capacity-statements/{sid}").json()
        assert detail["content_sha256"] and detail["document_version_hash"] and detail["ip"]
        played = adm.get(f"/api/admin/capacity-statements/{sid}/video")
        assert played.status_code == 200 and played.content == webm()
        view = adm.get(f"/api/admin/drafts/{d['id']}").json()
        assert view["capacity_statements"][0]["id"] == sid
        summary = adm.get("/api/admin/summary").json()
        assert summary["capacity_statements"] >= 1
        actions = [a["action"] for a in adm.get("/api/admin/audit?limit=80").json()]
        for a in ("capacity_statement_added", "admin_play_capacity_statement", "admin_view_capacity_statement"):
            assert a in actions
        # a client cannot use the admin routes
        assert c.get("/api/admin/capacity-statements").status_code == 403
        assert c.get(f"/api/admin/capacity-statements/{sid}/video").status_code == 403
