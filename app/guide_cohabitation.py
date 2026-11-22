"""Cohabitation agreement. DRAFT WORDING: needs lawyer review."""
from .fields import GOV, PERSON, YES_NO

COHABITATION = {
    "id": "cohabitation",
    "title": "Cohabitation agreement",
    "short_title": "Cohabitation",
    "summary": "An agreement for unmarried couples living together covering property, money and arrangements if you separate. A solicitor checks it before you sign.",
    "category": "Agreements",
    "review_video": "cohab_review",
    "steps": [
        {
            "id": "intro", "title": "Before you start", "video": "cohab_intro",
            "guidance": [
                "Unmarried couples do not have the same automatic rights as married couples. A cohabitation agreement can set out who owns what and what happens if you separate.",
            ],
            "fields": [],
        },
        {
            "id": "parties", "title": "The parties", "video": "cohab_parties",
            "guidance": ["Enter both full names."],
            "fields": [
                {"name": "party_a_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "party_b_name", "label": "Your partner's full name", "type": "text", "required": True},
                {"name": "address", "label": "Address where you live together", "type": "textarea"},
            ],
        },
        {
            "id": "property", "title": "Property and money", "video": "cohab_property",
            "guidance": ["Describe the home, who paid what, and how you want things treated if you separate."],
            "fields": [
                {"name": "property_details", "label": "Property and ownership details", "type": "textarea", "required": True},
                {"name": "arrangements", "label": "What should happen if you separate", "type": "textarea", "required": True},
            ],
        },
        {
            "id": "review", "title": "Review", "video": "cohab_review",
            "guidance": ["A solicitor will review the draft."],
            "fields": [],
        },
    ],
}
