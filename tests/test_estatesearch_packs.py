import httpx
import pytest

from app.integrations import estatesearch_pack as ep
from tests.helpers import user_client
from tests.test_probate import answers


def _a():
    a = answers()
    a["deceased"]["other_names"] = "Samuel Smith"
    a["deceased"]["date_of_birth"] = "1950-02-03"
    a["estatesearch"] = {"pkg_credit_liabilities": True, "pkg_will_register": False, "previous_addresses": "1 Old Road\n2 Older Road", "tracker": "Pack prepared"}
    return a


def test_blocked_without_both_death_certificate_and_authority():
    with pytest.raises(ep.PackBlocked) as e:
        ep.build_pack(_a(), [])
    assert len(e.value.missing) == 2
    with pytest.raises(ep.PackBlocked) as e:
        ep.build_pack(_a(), [{"kind": "Death certificate"}])
    assert e.value.missing == ["proof of authority: the grant, the will, or a signed engagement letter"]
    with pytest.raises(ep.PackBlocked):
        ep.build_pack(_a(), [{"kind": "Will"}])
    for auth in ("Will", "Grant of probate or letters of administration", "Signed engagement letter"):
        assert ep.build_pack(_a(), [{"kind": "Death certificate"}, {"kind": auth}])


def test_pack_contents_and_route_waiting(monkeypatch):
    monkeypatch.delenv("ESTATESEARCH_ENABLED", raising=False)
    p = ep.build_pack(_a(), [{"filename": "dc.pdf", "kind": "Death certificate"}, {"filename": "will.pdf", "kind": "Will"}])
    assert p["subject"]["other_names"] == "Samuel Smith" and p["subject"]["addresses_last_6_years"] == ["1 Old Road", "2 Older Road"]
    assert [x["id"] for x in p["packages"]] == ["credit_liabilities"] and p["total"] == "30.00"
    assert p["routes"][0]["status"] == "waiting for Titlefront account" and p["route"] == "yourself"
    assert [e["filename"] for e in p["evidence"]] == ["dc.pdf", "will.pdf"]
    doc = ep.pack_document(p)
    assert any("Earlier address: 1 Old Road" in x for s in doc["sections"] for x in s["paragraphs"])


def test_api_blocks_then_builds_pdf_and_tracker_persists(monkeypatch):
    monkeypatch.delenv("ESTATESEARCH_ENABLED", raising=False)
    sent = []
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, req: sent.append(req))
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": _a()}).json()
        r = c.get(f"/api/probate/drafts/{d['id']}/estatesearch/pack")
        assert r.status_code == 400 and len(r.json()["detail"]["missing"]) == 2
        for name, kind in (("dc.jpg", "Death certificate"), ("eng.jpg", "Signed engagement letter")):
            assert c.post(f"/api/drafts/{d['id']}/uploads", files={"file": (name, b"\xff\xd8\xff", "image/jpeg")}, data={"kind": kind}).status_code == 200
        assert c.get(f"/api/probate/drafts/{d['id']}/estatesearch/pack").json()["tracker"] == "Pack prepared"
        pdf = c.get(f"/api/probate/drafts/{d['id']}/estatesearch/pack.pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        a = _a(); a["estatesearch"]["tracker"] = "Report received"
        c.put(f"/api/drafts/{d['id']}", json={"answers": a})
        assert c.get(f"/api/probate/drafts/{d['id']}/estatesearch/pack").json()["tracker"] == "Report received"
    assert sent == []
