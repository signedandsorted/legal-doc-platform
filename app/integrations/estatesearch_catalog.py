"""Estatesearch package catalog (prices as published by Estatesearch, ex VAT) and the
ESTATESEARCH_ENABLED switch. No live calls, no emails, no credentials in this module.

Titlefront Limited is the account holder. While ESTATESEARCH_ENABLED is false (the default)
only the "order it yourself" route is offered: https://direct.estatesearch.co.uk/

Sources:
- Credit & Liabilities Search, Financial Profile Standard/Premium:
  https://www.estatesearch.co.uk/service/credit-liabilities-search/ (re-checked 2026-11-24)
- The rest were recorded from the linked service pages on 2026-11-23.
- Service list: https://www.estatesearch.co.uk/wp-sitemap-posts-service-1.xml
"""
from __future__ import annotations

import os
from decimal import ROUND_HALF_UP, Decimal

ORDER_YOURSELF_URL = "https://direct.estatesearch.co.uk/"
VAT_RATE = Decimal("0.20")
CL = "https://www.estatesearch.co.uk/service/credit-liabilities-search/"

PACKAGES = [
    {"id": "credit_liabilities", "name": "Credit & Liabilities Search", "ex_vat": "25.00", "source": CL, "checked": "2026-11-24", "price_prefix": ""},
    {"id": "financial_standard", "name": "Financial Profile Standard", "ex_vat": "165.00", "source": CL, "checked": "2026-11-24", "price_prefix": ""},
    {"id": "financial_premium", "name": "Financial Profile Premium", "ex_vat": "210.00", "source": CL, "checked": "2026-11-24", "price_prefix": ""},
    {"id": "identity_bankruptcy", "name": "Identity checks / bankruptcy search", "ex_vat": "4.00", "source": "https://www.estatesearch.co.uk/service/identity-checks-bankruptcy/", "checked": "2026-11-23", "price_prefix": "from "},
    {"id": "will_register", "name": "Will Register Search", "ex_vat": "54.17", "source": "https://www.estatesearch.co.uk/service/will-register-search/", "checked": "2026-11-23", "price_prefix": ""},
    {"id": "s27_notices", "name": "s.27 Gazette notices (or prepare the notice yourself on the section 27 step)", "ex_vat": "102.50", "source": "https://www.estatesearch.co.uk/service/s-27-gazette-notices/", "checked": "2026-11-23", "price_prefix": ""},
    {"id": "share_valuation", "name": "Share valuations", "ex_vat": "10.00", "source": "https://www.estatesearch.co.uk/wp-sitemap-posts-service-1.xml", "checked": "2026-11-23", "price_prefix": ""},
    {"id": "share_sale", "name": "Share sales and transfers", "ex_vat": "55.00", "source": "https://www.estatesearch.co.uk/wp-sitemap-posts-service-1.xml", "checked": "2026-11-23", "price_prefix": ""},
]
PRICE_ON_REQUEST = [
    "Digital Assets Search", "High Net Worth bolt-on", "International Profile Search", "Missing Will Service", "Missing Will Insurance",
    "No Section 27 Insurance", "Early Distribution Insurance", "Unoccupied Property Insurance", "Missing Share Certificates", "Share Verification",
    "Vehicle Valuations", "Estatesearch Will Search", "Financial Asset Search for the Living", "Will Bank Management", "Local Newspaper Notices",
]
SERVICE_LIST_URL = "https://www.estatesearch.co.uk/wp-sitemap-posts-service-1.xml"
BY_ID = {p["id"]: p for p in PACKAGES}


def enabled() -> bool:
    return (os.environ.get("ESTATESEARCH_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")


def _money(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def quote(selected: list[str]) -> dict:
    """Total = sum of chosen packages + 20% VAT. Unknown ids are ignored."""
    lines = [BY_ID[i] for i in dict.fromkeys(selected or []) if i in BY_ID]
    subtotal = sum((Decimal(p["ex_vat"]) for p in lines), Decimal("0"))
    vat = subtotal * VAT_RATE
    return {"lines": [{"id": p["id"], "name": p["name"], "ex_vat": p["ex_vat"], "price_prefix": p["price_prefix"]} for p in lines],
            "subtotal": _money(subtotal), "vat": _money(vat), "total": _money(subtotal + vat),
            "from_prices": any(p["price_prefix"] for p in lines)}


def routes() -> list[dict]:
    out = [{"id": "yourself", "label": "You can order this yourself", "url": ORDER_YOURSELF_URL}]
    if enabled():
        out.insert(0, {"id": "titlefront", "label": "Titlefront orders this search for you", "url": ""})
    return out


def catalog() -> dict:
    return {"packages": PACKAGES, "price_on_request": PRICE_ON_REQUEST, "service_list": SERVICE_LIST_URL, "routes": routes(), "enabled": enabled(),
            "vat_rate": "20%", "note": "Prices are as published by Estatesearch, before VAT. Nothing is ordered or sent from this page."}
