"""Postnuptial agreement for England and Wales. DRAFT WORDING: needs lawyer review."""
from .fields import GOV, PERSON, YES_NO

POSTNUP = {
    "id": "postnup",
    "title": "Postnuptial agreement",
    "short_title": "Postnup",
    "summary": "A postnuptial agreement signed after marriage to set out how assets should be treated. A solicitor checks it before you sign.",
    "category": "Agreements",
    "review_video": "postnup_review",
    "steps": [
        {
            "id": "intro", "title": "Before you start", "video": "postnup_intro",
            "guidance": [
                "A postnuptial agreement is signed after you are already married. Courts can take it into account if it is fair and both parties had independent advice.",
            ],
            "fields": [],
        },
        {
            "id": "parties", "title": "The parties", "video": "postnup_parties",
            "guidance": ["Enter the full legal names of both spouses."],
            "fields": [
                {"name": "party_a_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "party_b_name", "label": "Your spouse's full name", "type": "text", "required": True},
                {"name": "marriage_date", "label": "Date of marriage", "type": "date"},
            ],
        },
        {
            "id": "assets", "title": "Assets and intentions", "video": "postnup_assets",
            "guidance": ["Describe the assets and how you want them treated."],
            "fields": [
                {"name": "assets", "label": "Main assets to cover", "type": "textarea", "required": True},
                {"name": "intentions", "label": "What you both want the agreement to achieve", "type": "textarea", "required": True},
            ],
        },
        {
            "id": "review", "title": "Review", "video": "postnup_review",
            "guidance": ["A solicitor will review the draft."],
            "fields": [],
        },
    ],
}
