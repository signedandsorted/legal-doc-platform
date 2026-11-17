from .guide_lpa import LPA_HEALTH, LPA_PROPERTY
from .guide_probate import PROBATE

PERSON = [
    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
    {"name": "address", "label": "Address", "type": "textarea", "required": True},
    {"name": "relationship", "label": "Relationship to you", "type": "text"},
]

PERSON_DOB = PERSON[:2] + [{"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True}] + PERSON[2:]

WILL = {
    "id": "will",
    "title": "Make a will",
    "summary": "A will for England and Wales. You answer the questions, we prepare the draft, and a solicitor checks it before you sign.",
    "steps": [
        {
            "id": "intro",
            "title": "Before you start",
            "video": "will_intro",
            "guidance": [
                "A will says who looks after your estate (your executors), who receives it (your beneficiaries) and who cares for your children under 18 (guardians).",
                "You will need the full names and addresses of the people you want to include, and a rough idea of what you own and owe.",
                "Getting married or entering a civil partnership usually cancels an earlier will, so you should make a new one afterwards.",
                "Your answers are saved as you go. You can come back to them later with your reference number.",
            ],
            "fields": [],
        },
        {
            "id": "about_you",
            "title": "About you",
            "guidance": [
                "Use your full legal name as it appears on your passport or driving licence, and list any other names you have used or own assets under.",
            ],
            "fields": [
                {"name": "full_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "other_names", "label": "Other names you have used (optional)", "type": "text"},
                {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True},
                {"name": "address", "label": "Your address", "type": "textarea", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "marital_status", "label": "Marital status", "type": "select", "required": True, "options": ["Single", "Married", "Civil partnership", "Separated", "Divorced", "Widowed", "Living with a partner"]},
            ],
        },
        {
            "id": "executors",
            "title": "Your executors",
            "guidance": [
                "Executors deal with your estate after you die. Choose one to four adults you trust. They can also be beneficiaries.",
                "A replacement executor steps in if a first choice cannot or will not act.",
            ],
            "fields": [
                {"name": "executors", "label": "Executors", "type": "list", "min": 1, "max": 4, "fields": PERSON},
                {"name": "replacement_executor", "label": "Replacement executor (optional)", "type": "group", "fields": [dict(f, required=False) for f in PERSON]},
            ],
        },
        {
            "id": "guardians",
            "title": "Children and guardians",
            "guidance": [
                "If you have children under 18 you can name guardians to look after them if there is no surviving parent with parental responsibility.",
                "Ask your guardians first. Leave this blank if it does not apply.",
            ],
            "fields": [
                {"name": "children", "label": "Your children (optional)", "type": "list", "min": 0, "max": 10, "fields": [{"name": "full_name", "label": "Full name", "type": "text", "required": True}, {"name": "date_of_birth", "label": "Date of birth", "type": "date"}]},
                {"name": "guardians", "label": "Guardians (optional)", "type": "list", "min": 0, "max": 2, "fields": PERSON},
            ],
        },
        {
            "id": "gifts",
            "title": "Gifts",
            "guidance": [
                "Gifts of particular items or sums of money are paid before the rest of your estate is shared out.",
                "Describe items clearly, for example \"my gold wedding ring\" rather than \"my jewellery\".",
            ],
            "fields": [
                {"name": "gifts", "label": "Gifts (optional)", "type": "list", "min": 0, "max": 20, "fields": [
                    {"name": "gift", "label": "What you are giving", "type": "text", "required": True},
                    {"name": "beneficiary", "label": "Who receives it", "type": "text", "required": True},
                ]},
            ],
        },
        {
            "id": "residue",
            "title": "The rest of your estate",
            "guidance": [
                "Your residuary estate is everything left after debts, funeral costs, expenses and gifts.",
                "Give each person a share. Shares are worked out in proportion, so 1 and 1 means half each.",
                "Say what happens if a beneficiary dies before you. The usual choice is that their children take their share.",
            ],
            "fields": [
                {"name": "residuary_beneficiaries", "label": "Residuary beneficiaries", "type": "list", "min": 1, "max": 10, "fields": [
                    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
                    {"name": "relationship", "label": "Relationship to you", "type": "text"},
                    {"name": "share", "label": "Share", "type": "number", "required": True},
                ]},
                {"name": "substitution", "label": "If a beneficiary dies before me", "type": "select", "required": True, "options": ["Their children take their share", "Their share goes to the other residuary beneficiaries"]},
                {"name": "ultimate_beneficiary", "label": "If none of them survive me, the estate goes to (optional)", "type": "text"},
            ],
        },
        {
            "id": "wishes",
            "title": "Funeral wishes",
            "guidance": [
                "Funeral wishes are not legally binding, but your executors will usually follow them.",
            ],
            "fields": [
                {"name": "funeral_wishes", "label": "Funeral wishes (optional)", "type": "select", "options": ["No preference", "Burial", "Cremation"]},
                {"name": "funeral_notes", "label": "Anything else (optional)", "type": "textarea"},
            ],
        },
    ],
    "next_steps": [
        "A solicitor reviews your draft and contacts you with any questions.",
        "Sign the final will in front of two independent adult witnesses who are both present at the same time. They then sign in front of you.",
        "A witness must not be a beneficiary, or the husband, wife or civil partner of a beneficiary, or that person's gift can fail.",
        "Keep the signed original somewhere safe and tell your executors where it is. You can also store it with the Probate Service.",
        "Review your will after major life events: marriage, divorce, children, a house move or a large change in your finances.",
    ],
}

SERVICES = {s["id"]: s for s in (WILL, LPA_PROPERTY, LPA_HEALTH, PROBATE)}
