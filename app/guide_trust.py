"""Register a UK trust. The pack is typed into HMRC's own service. This site does not register it."""
from .fields import GOV

CHECK = "https://www.gov.uk/guidance/check-if-you-need-to-register-a-trust"
REGISTER = GOV["trust_register"]["url"]

ALIVE = "It is in my will and I am still alive"
DEATH = "A death has already created it"
LIFE = "It is a lifetime trust and the deed has been signed"
IMPOSED = "No, a court or a statute imposed it"

TRUST = {
    "id": "trust_register",
    "title": "Register a trust",
    "short_title": "Trust registration",
    "category": "Trusts",
    "summary": "For a trust in England and Wales. It says whether HMRC's Trust Registration Service needs it, and it prepares the particulars the lead trustee types in. This site does not register the trust.",
    "steps": [
        {
            "id": "exists",
            "title": "Does the trust exist yet?",
            "guidance": [
                "A trust written only in a will does not exist while you are alive, so it is not registered then.",
                "After a death, the trustees usually have to register it. A will trust that holds only assets from the estate, and which ends within two years of the death, is one of the exclusions.",
                "A lifetime trust is registered by the lead trustee on HMRC's own service, usually within 90 days of it being created.",
            ],
            "sources": [GOV["trust_register"], {"title": "GOV.UK: check if you need to register a trust", "url": CHECK}],
            "fields": [
                {"name": "when", "label": "Which trust is this?", "type": "select", "required": True, "options": [ALIVE, DEATH, LIFE]},
                {"name": "express", "label": "Was the trust set up on purpose?", "type": "select", "required": True, "options": ["Yes, it was set up on purpose", IMPOSED]},
            ],
        },
        {
            "id": "rule",
            "title": "Tax and exclusions",
            "guidance": [
                "If the trustees have to pay UK income tax, capital gains tax, inheritance tax, or stamp duty land tax, the trust is registered even where an exclusion would otherwise apply.",
                "The exclusions below are the common ones. The full list is on GOV.UK. A penalty of up to £5,000 can follow if a trust that should be registered is not.",
            ],
            "sources": [{"title": "GOV.UK: check if you need to register a trust", "url": CHECK}],
            "fields": [
                {"name": "tax", "label": "Do the trustees have to pay UK tax on the trust's income or assets?", "type": "select", "required": True, "options": ["No", "Not yet", "Yes"]},
                {"name": "exclusion", "label": "Does an exclusion apply?", "type": "select", "required": True, "options": [
                    "None",
                    "A charity is the only beneficiary",
                    "It is a will trust, it holds only estate assets, and it will end within 2 years of the death",
                    "It only holds a house or an account owned as joint tenants",
                    "It is a pilot trust of £100 or less set up before 6 October 2020",
                ]},
                {"name": "created", "label": "Date the trust was created, or the date of death if it comes from a will", "type": "date"},
            ],
        },
        {
            "id": "people",
            "title": "What HMRC asks for",
            "guidance": [
                "Use the names as they appear on the trust deed or the will. The lead trustee is the person who signs in to HMRC.",
                "This list is what you type in. It is not sent to HMRC from here.",
            ],
            "sources": [GOV["trust_register"]],
            "fields": [
                {"name": "name", "label": "Name of the trust", "type": "text", "required": True},
                {"name": "settlor", "label": "Settlor, the person who created it", "type": "text", "required": True},
                {"name": "trustees", "label": "Trustees, one on each line, and say which is the lead trustee", "type": "textarea", "required": True},
                {"name": "beneficiaries", "label": "Beneficiaries, or the class of people who can benefit", "type": "textarea", "required": True},
                {"name": "assets", "label": "What the trust holds", "type": "textarea", "required": True},
            ],
        },
        {
            "id": "done",
            "title": "After HMRC has registered it",
            "guidance": [
                "Leave this blank until the lead trustee has finished on HMRC's service. The reference they give is the proof. A tick here is not registration.",
            ],
            "sources": [GOV["trust_register"]],
            "fields": [
                {"name": "urn", "label": "HMRC trust reference, if they have already given one", "type": "text"},
            ],
        },
    ],
    "next_steps": [
        "Open GOV.UK and follow Register a trust as a trustee. The lead trustee uses their own Government Gateway account.",
        "Type in the particulars from this pack. This website does not send them.",
        "Write the reference HMRC gives back onto this file. Until that reference exists, the trust is not registered.",
    ],
}


def decide(answers: dict) -> dict:
    exists = answers.get("exists") or {}
    rule = answers.get("rule") or {}
    when = exists.get("when") or ""
    taxable = rule.get("tax") == "Yes"
    exclusion = rule.get("exclusion") or "None"
    if when == ALIVE:
        return {
            "register": False,
            "why": "A trust written into a will does not exist while you are alive, so it is not registered now. After the death, the trustees register it unless it only holds estate assets and ends within two years.",
            "deadline": "Not now.",
        }
    if exists.get("express") == IMPOSED and not taxable:
        return {
            "register": False,
            "why": "A trust imposed only by a court or by a statute is not registered as an express trust. If the trustees later have to pay UK tax, that changes and it is registered.",
            "deadline": "Not required on these answers.",
        }
    if exclusion != "None" and not taxable:
        return {
            "register": False,
            "why": "On these answers an exclusion applies and the trust does not pay UK tax. Keep the reason with the trust papers. If the trust continues, or tax becomes due, register it then.",
            "deadline": "Not required on these answers.",
        }
    if taxable:
        deadline = "Register within 90 days of the trustees becoming liable to UK tax. Use the date on the GOV.UK page if the liability is older than that."
    else:
        deadline = "Register within 90 days of the trust being created, or of it becoming registrable."
    return {
        "register": True,
        "why": "This is a UK express trust, and either no exclusion applies or the trustees have to pay UK tax. The lead trustee registers it on HMRC's Trust Registration Service.",
        "deadline": deadline,
    }
