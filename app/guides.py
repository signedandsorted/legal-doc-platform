from .guide_lpa import LPA_HEALTH, LPA_PROPERTY

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

PROBATE = {
    "id": "probate",
    "title": "Probate helper",
    "summary": "A step-by-step checklist for dealing with the estate of someone who has died in England or Wales, with a summary a solicitor can check.",
    "steps": [
        {
            "id": "intro",
            "title": "Before you start",
            "guidance": [
                "We are sorry for your loss. This helper walks you through the main steps of administering an estate and records what you know so far.",
                "Probate is the legal right to deal with someone's estate. It is called a grant of probate if there is a will, or letters of administration if there is not.",
                "You may not need probate for small estates or where everything was jointly owned; banks set their own limits.",
            ],
            "fields": [],
        },
        {
            "id": "deceased",
            "title": "About the person who died",
            "guidance": ["A death must normally be registered within 5 days in England and Wales. You will need the death certificate for most steps."],
            "fields": [
                {"name": "full_name", "label": "Their full name", "type": "text", "required": True},
                {"name": "date_of_death", "label": "Date of death", "type": "date", "required": True},
                {"name": "address", "label": "Their last address", "type": "textarea", "required": True},
                {"name": "death_registered", "label": "Has the death been registered?", "type": "select", "required": True, "options": ["Yes", "No"]},
            ],
        },
        {
            "id": "will",
            "title": "The will",
            "guidance": [
                "If there is a will, the executors named in it apply for probate. If there is no will, the closest relatives apply under the intestacy rules.",
                "Look for the original signed will. A copy is not usually enough.",
            ],
            "fields": [
                {"name": "has_will", "label": "Is there a will?", "type": "select", "required": True, "options": ["Yes, I have the original", "Yes, but I only have a copy", "No", "Not sure"]},
                {"name": "applicant", "label": "You (the person applying)", "type": "group", "fields": PERSON + [{"name": "email", "label": "Email", "type": "email", "required": True}]},
            ],
        },
        {
            "id": "estate",
            "title": "Value of the estate",
            "guidance": [
                "List what they owned (property, money, investments, possessions) and what they owed at the date of death. Estimates are fine for now.",
                "Inheritance Tax may be due if the estate is worth more than the tax-free thresholds. Many estates are \"excepted estates\" that do not need a full Inheritance Tax account; check GOV.UK for the current thresholds.",
            ],
            "fields": [
                {"name": "assets", "label": "Assets", "type": "list", "min": 0, "max": 30, "fields": [
                    {"name": "description", "label": "Description", "type": "text", "required": True},
                    {"name": "value", "label": "Value (£)", "type": "number", "required": True},
                    {"name": "jointly_owned", "label": "Jointly owned?", "type": "select", "options": ["No", "Yes"]},
                ]},
                {"name": "debts", "label": "Debts and funeral costs", "type": "list", "min": 0, "max": 30, "fields": [
                    {"name": "description", "label": "Description", "type": "text", "required": True},
                    {"name": "value", "label": "Amount (£)", "type": "number", "required": True},
                ]},
                {"name": "gifts_in_last_7_years", "label": "Gifts they made in the 7 years before death (optional)", "type": "textarea"},
            ],
        },
    ],
    "next_steps": [
        "Report the estate's value to HMRC. If Inheritance Tax is due or the estate is not an excepted estate, send form IHT400 and wait 20 working days before applying for probate.",
        "Apply for probate on GOV.UK (or by post on form PA1P with a will, PA1A without one). Check the current application fee on GOV.UK.",
        "Once you have the grant, collect the assets, pay the debts, taxes and expenses, and keep a record of everything.",
        "Consider placing a deceased estates notice in The Gazette to protect you from unknown creditors.",
        "Wait at least 6 months from the grant before distributing in full, because claims under the Inheritance (Provision for Family and Dependants) Act 1975 can be made in that time.",
        "Prepare estate accounts and distribute the estate to the beneficiaries.",
    ],
}

SERVICES = {s["id"]: s for s in (WILL, LPA_PROPERTY, LPA_HEALTH, PROBATE)}
