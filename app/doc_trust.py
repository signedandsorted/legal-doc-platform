"""The particulars for HMRC's Trust Registration Service. Nothing is sent."""
from .common import issue
from .guide_trust import CHECK, REGISTER, decide


def trust_issues(answers: dict, uploads_text: str = "") -> list[dict]:
    decision = decide(answers)
    done = answers.get("done") or {}
    if not decision["register"]:
        return [issue("warning", decision["why"])]
    if not str(done.get("urn") or "").strip():
        return [issue("warning", "HMRC has not yet given a reference. The pack can be typed in. The trust is not registered until the lead trustee finishes HMRC's own service.")]
    return []


def build_trust(service_id: str, answers: dict, uploads=None) -> dict:
    decision = decide(answers)
    people = answers.get("people") or {}
    rule = answers.get("rule") or {}
    done = answers.get("done") or {}
    name = (people.get("name") or "the trust").strip()
    urn = str(done.get("urn") or "").strip()
    sections = [
        {"heading": "Does it have to be registered?", "paragraphs": [decision["why"], "Deadline: " + decision["deadline"]]},
        {"heading": "Particulars to type into HMRC's service", "paragraphs": [
            f"Trust: {name}.",
            f"Created, or date of death: {rule.get('created') or '[date not entered]'}.",
            f"Settlor: {people.get('settlor') or '[not entered]'}.",
            f"Trustees: {people.get('trustees') or '[not entered]'}.",
            f"Beneficiaries: {people.get('beneficiaries') or '[not entered]'}.",
            f"Assets: {people.get('assets') or '[not entered]'}.",
            f"UK tax due: {rule.get('tax') or '[not answered]'}.",
            f"Exclusion claimed: {rule.get('exclusion') or 'None'}.",
            f"HMRC reference: {urn or 'not yet given'}.",
        ]},
        {"heading": "What this pack does not do", "paragraphs": [
            "It does not register the trust. HMRC's Trust Registration Service is the only place that does that.",
            "It does not give a Unique Taxpayer Reference. The lead trustee gets that from HMRC, if the trust needs one.",
            "A blank reference means it has not been registered.",
        ]},
    ]
    return {
        "title": f"Trust registration pack — {name}",
        "notice": "Take this to HMRC's Trust Registration Service. Nothing has been sent. The trust is not registered until HMRC gives a reference.",
        "sections": sections,
        "next_steps": [
            f"Open {REGISTER} and sign in as the lead trustee.",
            f"If you are not sure the trust has to be registered, check {CHECK} first.",
            "Type in the particulars above. Then write HMRC's reference back onto this file.",
        ],
        "sources": [
            {"title": "GOV.UK: Register a trust as a trustee", "url": REGISTER},
            {"title": "GOV.UK: check if you need to register a trust", "url": CHECK},
        ],
    }
