"""Fixture SOAP clients for the HMLR K16 (Land Charges bankruptcy search) and PN1 (index of
proprietors' names) searches. TEST/FIXTURE ONLY: there is no network transport here.

The real Business Gateway service and element names are still to be confirmed from the HMLR BG
interface specifications, so the names below are placeholders kept in one place. A live client
must not be added until the certificate is placed by Grok Bot (Chief of Staff) and the wills
flags are switched on. Fees and rules live in hmlr.py.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Callable
from xml.sax.saxutils import escape

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
# Placeholder namespaces/operations until the BG interface specs are confirmed.
SERVICES = {
    "K16": {"operation": "LandChargesBankruptcySearchRequest", "ns": "urn:placeholder:hmlr:k16"},
    "PN1": {"operation": "IndexOfProprietorsNamesSearchRequest", "ns": "urn:placeholder:hmlr:pn1"},
}


def _split(full_name: str) -> tuple[str, str]:
    parts = full_name.split()
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def build_request(search_type: str, full_name: str, reference: str) -> str:
    svc = SERVICES[search_type]
    forenames, surname = _split(full_name)
    return (
        f'<soap:Envelope xmlns:soap="{SOAP_NS}"><soap:Body>'
        f'<req:{svc["operation"]} xmlns:req="{svc["ns"]}">'
        f"<req:ExternalReference>{escape(reference)}</req:ExternalReference>"
        f"<req:Forenames>{escape(forenames)}</req:Forenames><req:Surname>{escape(surname)}</req:Surname>"
        f"</req:{svc['operation']}></soap:Body></soap:Envelope>"
    )


def parse_response(xml_text: str) -> dict:
    """Read the reference, outcome and any entries from a (fixture) response envelope."""
    root = ET.fromstring(xml_text)
    fault = root.find(f".//{{{SOAP_NS}}}Fault")
    if fault is not None:
        raise RuntimeError((fault.findtext("faultstring") or "HMLR returned an error").strip())

    def first(tag: str) -> str:
        for el in root.iter():
            if el.tag.split("}")[-1] == tag:
                return (el.text or "").strip()
        return ""

    entries = [(el.text or "").strip() for el in root.iter() if el.tag.split("}")[-1] == "Entry"]
    return {"reference": first("HMLRReference"), "result": first("Outcome") or ("Entries found" if entries else "No entries found"), "entries": entries}


class SoapFixtureProvider:
    """Provider that builds the SOAP request and hands it to a fixture transport (a callable
    taking (search_type, request_xml) and returning response XML). No network."""
    name = "soap-fixture"

    def __init__(self, transport: Callable[[str, str], str]) -> None:
        self.transport = transport
        self.sent: list[tuple[str, str]] = []

    def search(self, search_type: str, full_name: str) -> dict:
        req = build_request(search_type, full_name, reference=f"WILLS-{search_type}-{len(self.sent) + 1}")
        self.sent.append((search_type, req))
        return parse_response(self.transport(search_type, req))
