import re
from pathlib import Path

import httpx

from app.guide_probate import PROBATE
from app.integrations import estatesearch_catalog as es
from tests.helpers import user_client


def test_total_is_sum_plus_20_percent_vat():
    q = es.quote(["credit_liabilities", "financial_standard", "nope", "credit_liabilities"])
    assert [l["id"] for l in q["lines"]] == ["credit_liabilities", "financial_standard"]
    assert (q["subtotal"], q["vat"], q["total"]) == ("190.00", "38.00", "228.00")
    assert es.quote(["will_register"])["total"] == "65.00"  # 54.17 * 1.2 = 65.004
    assert es.quote([])["total"] == "0.00"


def test_flag_off_only_order_yourself(monkeypatch):
    monkeypatch.delenv("ESTATESEARCH_ENABLED", raising=False)
    assert [r["id"] for r in es.routes()] == ["yourself"]
    assert es.routes()[0]["url"] == "https://direct.estatesearch.co.uk/"
    monkeypatch.setenv("ESTATESEARCH_ENABLED", "true")
    assert [r["id"] for r in es.routes()] == ["titlefront", "yourself"]


def test_flag_off_no_outbound_http_or_email(monkeypatch):
    monkeypatch.delenv("ESTATESEARCH_ENABLED", raising=False)
    sent, mails = [], []
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, req: sent.append(req))  # real network transport only
    import app.mailer as mailer
    for name in ("send", "_send_resend", "_send_smtp"):
        monkeypatch.setattr(mailer, name, lambda *a, **k: mails.append(a))
    with user_client() as c:
        cat = c.get("/api/probate/estatesearch/catalog").json()
        assert cat["enabled"] is False and len(cat["packages"]) == 8
        assert c.get("/api/probate/estatesearch/quote?ids=credit_liabilities").json()["total"] == "30.00"
    assert sent == [] and mails == []


def test_no_firm_desk_wording_in_new_templates():
    step = next(s for s in PROBATE["steps"] if s["id"] == "estatesearch")
    text = " ".join(step["guidance"]) + Path("app/integrations/estatesearch_catalog.py").read_text()
    js = Path("static/app.js").read_text()
    tool = js[js.index("async estatesearch(box"):js.index("async hmlr(box")]
    for t in (text, tool):
        assert not re.search(r"firm desk|busbys", t, re.I)
    assert any("order this yourself" in g for g in step["guidance"])
