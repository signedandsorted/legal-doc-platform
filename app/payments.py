"""The public document is free to prepare and paid to download.

The price is the amount taken. Stripe is the card taker. This module does not
mark a draft paid unless Stripe says the payment is complete.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time

import httpx
from fastapi import HTTPException

PRICES = {
    "will": (14900, "Will"),
    "lpa_property": (14900, "Property and financial affairs lasting power of attorney"),
    "lpa_health": (14900, "Health and welfare lasting power of attorney"),
    "poa_ordinary": (9900, "Ordinary power of attorney"),
    "probate": (39900, "Probate pack"),
    "prenup": (34900, "Prenuptial agreement"),
    "postnup": (34900, "Postnuptial agreement"),
    "nuptial": (34900, "Nuptial agreement"),
    "cohabitation": (24900, "Cohabitation agreement"),
    "employment_settlement": (29900, "Employment settlement agreement", "gbp"),
    "us_will": (12900, "US last will", "usd"),
    "us_trust": (29900, "US revocable trust and pour-over will", "usd"),
    "us_poa": (7900, "US durable financial power of attorney", "usd"),
    "us_health": (7900, "US advance healthcare directive", "usd"),
    "us_probate": (19900, "US probate checklist", "usd"),
}


def quote(service: str) -> dict:
    row = PRICES.get(service)
    if not row:
        raise HTTPException(400, "There is no public price for this document.")
    amount, name = row[0], row[1]
    currency = row[2] if len(row) > 2 else "gbp"
    if not amount:
        raise HTTPException(400, "There is no public price for this document.")
    pounds = amount / 100
    symbol = "$" if currency == "usd" else "£"
    label = f"{symbol}{pounds:.0f}" if pounds == int(pounds) else f"{symbol}{pounds:.2f}"
    return {"amount": amount, "currency": currency, "label": label, "name": name}


def describe(row: dict) -> dict:
    price = quote(row["service"])
    paid = (row.get("payment") or {}) if isinstance(row.get("payment"), dict) else {}
    done = paid.get("status") == "paid" and int(paid.get("amount") or 0) == price["amount"] and (paid.get("currency") or "gbp") == price["currency"]
    return {**price, "status": "paid" if done else "unpaid", "paid_at": paid.get("paid_at") or ""}


def require_paid(row: dict) -> None:
    payment = describe(row)
    if payment["status"] != "paid":
        raise HTTPException(402, {
            "message": f"Pay {payment['label']} to download this. The questions are free. Nothing has been taken yet.",
            "payment": payment,
        })


def _key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def start_checkout(row: dict, base: str, email: str) -> str:
    key = _key()
    if not key.startswith("sk_"):
        raise HTTPException(503, "Card payments are not connected yet. Add STRIPE_SECRET_KEY on the server. Nothing has been taken.")
    price = quote(row["service"])
    data = {
        "mode": "payment",
        "success_url": f"{base}/paid?draft={row['id']}&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/#/d/{row['id']}/review",
        "client_reference_id": row["id"],
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": price["currency"],
        "line_items[0][price_data][unit_amount]": str(price["amount"]),
        "line_items[0][price_data][product_data][name]": price["name"],
        "line_items[0][price_data][product_data][description]": (
            "For you to download and use yourself. A solicitor is optional. "
            "Paying asks for the document straight away. Once it is supplied, the 14-day right to cancel this download ends."
        ),
        "metadata[draft_id]": row["id"],
        "metadata[service]": row["service"],
    }
    if email and "@" in email:
        data["customer_email"] = email
    response = httpx.post("https://api.stripe.com/v1/checkout/sessions", data=data, auth=(key, ""), timeout=20)
    body = response.json()
    if response.status_code >= 400 or not body.get("url"):
        raise HTTPException(502, "The card page did not open. Nothing has been taken.")
    return body["url"]


def paid_record(session: dict, service: str) -> dict:
    price = quote(service)
    if session.get("payment_status") != "paid":
        raise HTTPException(402, "The payment is not complete. Nothing has been marked paid.")
    draft_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("draft_id")
    if not draft_id:
        raise HTTPException(400, "That payment is not tied to a document.")
    if int(session.get("amount_total") or 0) != price["amount"] or (session.get("currency") or "").lower() != price["currency"]:
        raise HTTPException(400, "The amount paid does not match the price. It has not been accepted.")
    return {
        "status": "paid",
        "amount": price["amount"],
        "currency": "gbp",
        "draft_id": draft_id,
        "session_id": session.get("id") or "",
        "paid_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def fetch_session(session_id: str) -> dict:
    key = _key()
    if not key.startswith("sk_"):
        raise HTTPException(503, "Card payments are not connected yet. Nothing has been taken.")
    if not session_id or not session_id.startswith("cs_"):
        raise HTTPException(400, "That is not a payment reference.")
    response = httpx.get(f"https://api.stripe.com/v1/checkout/sessions/{session_id}", auth=(key, ""), timeout=20)
    if response.status_code >= 400:
        raise HTTPException(402, "The payment could not be confirmed. Nothing has been marked paid.")
    return response.json()


def webhook_event(payload: bytes, signature: str) -> dict:
    """Accept a Stripe event only when the signature matches. Does not trust the body alone."""
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "The payment notification secret is not set.")
    parts = dict(item.split("=", 1) for item in signature.split(",") if "=" in item)
    stamp = parts.get("t", "")
    signed = parts.get("v1", "")
    if not stamp or not signed:
        raise HTTPException(400, "The payment notification was not signed.")
    if abs(time.time() - int(stamp)) > 300:
        raise HTTPException(400, "The payment notification is too old.")
    expected = hmac.new(secret.encode(), f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signed):
        raise HTTPException(400, "The payment notification did not match.")
    import json
    return json.loads(payload)
