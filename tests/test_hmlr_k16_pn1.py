from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine

from app.db import metadata
from app.integrations import hmlr
from app.integrations.hmlr_soap import SoapFixtureProvider, build_request, parse_response
from tests.helpers import user_client
from tests.test_probate import answers

FX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 24, 15, 0, tzinfo=timezone.utc)
ON = hmlr.Settings(True, True, 5000, "bgtest")


def transport(search_type, request_xml):
    return (FX / ("hmlr_k16_clear.xml" if search_type == "K16" else "hmlr_pn1_found.xml")).read_text()


@pytest.fixture()
def conn():
    eng = create_engine("sqlite://")
    metadata.create_all(eng, tables=[metadata.tables["hmlr_spend"]])
    with eng.begin() as c:
        yield c


def test_soap_request_and_fixture_responses():
    xml = build_request("K16", "Pat O'Neil & Smith", "WILLS-K16-1")
    assert "LandChargesBankruptcySearchRequest" in xml and "O'Neil &amp;</req:Forenames>" in xml and "<req:Surname>Smith</req:Surname>" in xml
    k16 = parse_response(transport("K16", xml))
    assert k16["reference"] == "K16-FIXTURE-0001" and k16["entries"] == []
    pn1 = parse_response(transport("PN1", ""))
    assert pn1["entries"] and pn1["result"] == "Entries found"
    with pytest.raises(RuntimeError, match="Invalid name"):
        parse_response((FX / "hmlr_fault.xml").read_text())


def _order(conn, st, names, p, confirm=True, uploads=(), settings=ON):
    return hmlr.order(conn, st, names, confirm=confirm, uploads=list(uploads), draft_id="d", user_id="u", provider=p, settings=settings, now=NOW)


def test_confirmation_required_no_call(conn):
    p = SoapFixtureProvider(transport)
    with pytest.raises(hmlr.ConfirmationRequired):
        _order(conn, "K16", ["Pat Smith"], p, confirm=False)
    assert p.sent == []


def test_pn1_without_grant_refused(conn):
    p = SoapFixtureProvider(transport)
    with pytest.raises(hmlr.GrantRequired):
        _order(conn, "PN1", ["Sam Smith"], p)
    assert p.sent == []
    r = _order(conn, "PN1", ["Sam Smith"], p, uploads=[{"kind": "Grant of probate or letters of administration"}])
    assert r[0]["reference"] == "PN1-FIXTURE-0001" and r[0]["fee"] == 15.0


def test_cap_refuses_ninth_k16_with_soap_fixture(conn):
    p = SoapFixtureProvider(transport)
    _order(conn, "K16", [f"Person {i}" for i in range(8)], p)
    with pytest.raises(hmlr.DailyCapReached):
        _order(conn, "K16", ["Person 9"], p)
    assert len(p.sent) == 8
    assert len(hmlr.ledger(conn)) == 8


def test_flags_off_no_outbound_call(conn, monkeypatch):
    sent = []
    monkeypatch.setattr(httpx.Client, "send", lambda self, req, *a, **k: sent.append(req))
    p = SoapFixtureProvider(transport)
    with pytest.raises(hmlr.HmlrNotSwitchedOn):
        _order(conn, "K16", ["Pat Smith"], p, settings=hmlr.Settings(False, False, 5000, "bgtest"))
    assert p.sent == [] and sent == []


def test_api_confirm_and_grant_rules_with_fixture(monkeypatch):
    monkeypatch.setenv("WILLS_HMLR_ENABLED", "true")
    monkeypatch.setenv("WILLS_HMLR_ALLOW_LIVE", "true")
    p = SoapFixtureProvider(transport)
    monkeypatch.setattr(hmlr, "live_provider", lambda settings: p)
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": answers()}).json()
        q = c.post(f"/api/probate/drafts/{d['id']}/hmlr/quote", json={"search_type": "K16", "names": ["Pat Smith"]}).json()
        assert q["switched_on"] and q["total"] == 6.0 and q["daily_cap"] == 50.0
        assert c.post(f"/api/probate/drafts/{d['id']}/hmlr/order", json={"search_type": "K16", "names": ["Pat Smith"]}).status_code == 409
        assert c.post(f"/api/probate/drafts/{d['id']}/hmlr/order", json={"search_type": "PN1", "names": ["Sam Smith"], "confirm": True}).status_code == 400
        assert p.sent == []
        ok = c.post(f"/api/probate/drafts/{d['id']}/hmlr/order", json={"search_type": "K16", "names": ["Pat Smith"], "confirm": True})
        assert ok.status_code == 200 and ok.json()["results"][0]["reference"] == "K16-FIXTURE-0001"
