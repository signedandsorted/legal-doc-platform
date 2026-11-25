"""The public download is charged. A draft is not marked paid without Stripe."""
import hashlib
import hmac
import json
import time

from app.payments import paid_record, quote, webhook_event
from fastapi import HTTPException


def test_each_public_document_has_a_price():
    assert quote("will")["label"] == "£149"
    assert quote("lpa_health")["amount"] == 14900
    assert quote("probate")["label"] == "£399"
    assert quote("employment_settlement")["label"] == "£299"


def test_a_short_payment_is_refused():
    try:
        paid_record({"payment_status": "paid", "amount_total": 100, "currency": "gbp", "client_reference_id": "d1", "id": "cs_test"}, "will")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("a short payment was accepted")


def test_webhook_rejects_a_bad_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    payload = json.dumps({"type": "checkout.session.completed"}).encode()
    stamp = str(int(time.time()))
    good = hmac.new(b"whsec_test", f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    event = webhook_event(payload, f"t={stamp},v1={good}")
    assert event["type"] == "checkout.session.completed"
    try:
        webhook_event(payload, f"t={stamp},v1={'0' * 64}")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("a bad signature was accepted")
