"""Prenuptial agreement for England and Wales. DRAFT WORDING: needs lawyer review."""
from .fields import GOV, PERSON, YES_NO

PRENUP = {
    "id": "prenup",
    "title": "Prenuptial agreement",
    "short_title": "Prenup",
    "summary": "A clear prenuptial agreement that sets out how assets should be treated if the marriage ends. Both parties receive independent legal advice before signing.",
    "category": "Agreements",
    "steps": [
        {
            "id": "intro", "title": "Before you start",
            "guidance": [
                "A prenuptial agreement is signed before marriage. In England and Wales it is not automatically binding, but a court will usually follow it if it is fair, both parties had independent legal advice, and there was full disclosure.",
                "This service gathers the information. A solicitor then drafts the final agreement and arranges independent advice for each of you.",
                "Do not sign anything until you have both spoken to your own solicitors.",
            ],
            "fields": [],
        },
        {
            "id": "parties", "title": "About both of you",
            "guidance": ["Use full legal names. The agreement is between the two people who intend to marry."],
            "fields": [
                {"name": "party_a_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "party_b_name", "label": "Your partner's full name", "type": "text", "required": True},
                {"name": "wedding_date", "label": "Expected wedding or civil partnership date", "type": "date"},
                {"name": "address", "label": "Address where you will live (or current address)", "type": "textarea"},
            ],
        },
        {
            "id": "assets", "title": "Assets and disclosure",
            "guidance": [
                "Full disclosure is essential. List the main assets each of you is bringing into the marriage (property, savings, pensions, business interests).",
                "Be as clear as you can. Your solicitor will refine the list.",
            ],
            "fields": [
                {"name": "assets_a", "label": "Your main assets and approximate values", "type": "textarea", "required": True},
                {"name": "assets_b", "label": "Your partner's main assets and approximate values", "type": "textarea", "required": True},
                {"name": "intentions", "label": "What you both want the agreement to achieve", "type": "textarea", "required": True},
                {"name": "exclude_assets", "label": "Any assets you want to keep completely separate", "type": "textarea"},
            ],
        },
        {
            "id": "arrangements", "title": "How assets should be treated",
            "guidance": ["Describe what should happen to the home, savings, and other assets if the marriage ends."],
            "fields": [
                {"name": "home", "label": "What should happen to the family home?", "type": "textarea"},
                {"name": "income", "label": "Any income or maintenance arrangements you want to set out", "type": "textarea"},
                {"name": "other", "label": "Anything else important", "type": "textarea"},
            ],
        },
        {
            "id": "review", "title": "Review and next steps",
            "guidance": [
                "A solicitor will review everything, prepare the formal agreement, and arrange for each of you to receive independent legal advice before signing.",
                "You will also need to exchange full financial disclosure.",
            ],
            "fields": [],
        },
    ],
}
