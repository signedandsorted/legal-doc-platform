"""Prenuptial agreement for England and Wales. DRAFT WORDING: needs lawyer review."""
from .fields import GOV, PERSON, YES_NO

PRENUP = {
    "id": "prenup",
    "title": "Prenuptial agreement",
    "short_title": "Prenup",
    "summary": "A prenuptial agreement to set out how assets should be treated if the marriage ends. A solicitor checks it before you sign.",
    "category": "Agreements",
    "steps": [
        {
            "id": "intro", "title": "Before you start",
            "guidance": [
                "A prenuptial agreement is signed before marriage. It is not automatically binding in England and Wales, but courts take it into account if it is fair and both parties had independent advice.",
                "Both of you should have separate legal advice. This service helps you gather the information; a solicitor finalises it.",
            ],
            "fields": [],
        },
        {
            "id": "parties", "title": "The parties",
            "guidance": ["Enter the full legal names of both people who will marry."],
            "fields": [
                {"name": "party_a_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "party_b_name", "label": "Your partner's full name", "type": "text", "required": True},
                {"name": "wedding_date", "label": "Expected wedding date", "type": "date"},
            ],
        },
        {
            "id": "assets", "title": "Assets and intentions",
            "guidance": ["Describe the main assets each of you is bringing into the marriage and how you want them treated."],
            "fields": [
                {"name": "assets_a", "label": "Your main assets", "type": "textarea", "required": True},
                {"name": "assets_b", "label": "Your partner's main assets", "type": "textarea", "required": True},
                {"name": "intentions", "label": "What you both want the agreement to achieve", "type": "textarea", "required": True},
            ],
        },
        {
            "id": "review", "title": "Review",
            "guidance": ["A solicitor will review the draft and arrange for both parties to receive independent advice."],
            "fields": [],
        },
    ],
}
