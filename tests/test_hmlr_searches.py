from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import create_engine

from app.db import metadata
from app.guide_probate import PROBATE
from app.integrations import hmlr
from tests.helpers import user_client
from tests.test_probate import answers

NOW = datetime(2026, 11, 24, 15, 0, tzinfo=timezone.utc)
ON = hmlr.Settings(enabled=True, allow_live=True, daily_cap_pence=5000, base_url="bgtest")


@pytest.fixture()
def conn():
    eng = create_engine("sqlite://")
    metadata.create_all(eng, tables=[metadata.tables["hmlr_spend"]])
    with eng.begin() as c:
        yield c


def _order(conn, st, names, provider, confirm=True, uploads=(), settings=ON):
    return hmlr.order(conn, st, names, confirm=confirm, uploads=list(uploads), draft_id="d1", user_id="u1", provider=provider, settings=settings, now=NOW)


def test_defaults_are_off(monkeypatch):
    for k in ("WILLS_HMLR_ENABLED", "WILLS_HMLR_ALLOW_LIVE", "WILLS_HMLR_DAILY_CAP_GBP", "WILLS_HMLR_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    s = hmlr.Settings.from_env()
    assert (s.enabled, s.allow_live, s.daily_cap_pence, s.base_url) == (False, False, 5000, "bgtest")
    assert hmlr.live_provider(hmlr.Settings(True, True, 5000, "bgtest")) is None  # no live path in this build


def test_cap_refuses_ninth_k16_in_a_day(conn):
    p = hmlr.FixtureProvider()
    for i in range(8):
        _order(conn, "K16", [f"Beneficiary {i}"], p)
    assert hmlr.spent_today_pence(conn, "2026-11-24") == 4800
    with pytest.raises(hmlr.DailyCapReached):
        _order(conn, "K16", ["Beneficiary 9"], p)
    assert len(p.calls) == 8


def test_confirmation_required(conn):
    p = hmlr.FixtureProvider()
    with pytest.raises(hmlr.ConfirmationRequired):
        _order(conn, "K16", ["Pat Smith"], p, confirm=False)
    assert p.calls == [] and hmlr.spent_today_pence(conn, "2026-11-24") == 0


def test_pn1_needs_grant_upload(conn):
    p = hmlr.FixtureProvider()
    with pytest.raises(hmlr.GrantRequired):
        _order(conn, "PN1", ["Sam Smith"], p, uploads=[{"kind": "Death certificate"}])
    assert p.calls == []
    out = _order(conn, "PN1", ["Sam Smith"], p, uploads=[{"kind": "Grant of probate or letters of administration"}])
    assert out[0]["fee"] == 15.0 and p.calls == [("PN1", "Sam Smith")]


def test_flags_off_no_outbound_call(conn, monkeypatch):
    sent = []
    monkeypatch.setattr(httpx.Client, "send", lambda self, req, *a, **k: sent.append(req))
    p = hmlr.FixtureProvider()
    for s in (hmlr.Settings(False, False, 5000, "bgtest"), hmlr.Settings(True, False, 5000, "bgtest"), hmlr.Settings(False, True, 5000, "bgtest")):
        with pytest.raises(hmlr.HmlrNotSwitchedOn):
            _order(conn, "K16", ["Pat Smith"], p, settings=s)
    with pytest.raises(hmlr.HmlrNotSwitchedOn):  # both flags on but no live provider exists
        hmlr.order(conn, "K16", ["Pat Smith"], confirm=True, uploads=[], draft_id="d", user_id="u", settings=ON, now=NOW)
    assert p.calls == [] and sent == []


def test_quote_shows_fee_spend_and_cap(conn):
    q = hmlr.quote(conn, "k16", ["Pat Smith", "Jo Smith"], settings=ON, now=NOW)
    assert q["fee_each"] == 6.0 and q["total"] == 12.0 and q["daily_cap"] == 50.0 and q["spent_today"] == 0
    assert q["fee_source"].startswith("https://www.gov.uk/")


def test_api_shows_not_switched_on(monkeypatch):
    monkeypatch.delenv("WILLS_HMLR_ENABLED", raising=False)
    monkeypatch.delenv("WILLS_HMLR_ALLOW_LIVE", raising=False)
    assert any(s["id"] == "hmlr" and s["tool"] == "hmlr" for s in PROBATE["steps"])
    with user_client() as c:
        assert c.get("/api/probate/hmlr/status").json()["message"] == hmlr.NOT_ON
        d = c.post("/api/drafts", json={"service": "probate", "answers": answers()}).json()
        r = c.post(f"/api/probate/drafts/{d['id']}/hmlr/order", json={"search_type": "K16", "names": ["Pat Smith"], "confirm": True})
        assert r.status_code == 503 and "not switched on" in r.json()["detail"]
        assert c.get("/api/probate/admin/hmlr-ledger").status_code == 403


def test_admin_sees_ledger():
    from tests.helpers import admin_client
    with admin_client() as c:
        r = c.get("/api/probate/admin/hmlr-ledger")
        assert r.status_code == 200 and r.json()["daily_cap"] == 50.0 and isinstance(r.json()["rows"], list)
