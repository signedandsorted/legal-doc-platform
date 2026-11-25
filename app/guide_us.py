"""United States documents. State law decides how they are signed. This is not an England and Wales will."""
from .us_states import STATES

YES_NO = ["No", "Yes"]
MARITAL = ["Single", "Married", "Domestic partnership or civil union", "Divorced", "Widowed"]
PERSON = [{"name": "full_name", "label": "Full legal name", "type": "text", "required": True},
          {"name": "address", "label": "City and state", "type": "text"}]


def _about(kind: str) -> dict:
    return {
        "id": "about", "title": "You and your state",
        "guidance": [
            "The state is where you live now. The signing rules in the draft follow that state.",
            "If you move, make a new document in the new state. Do not write on this one.",
            "Louisiana does not use a common-law will. The draft will say so, and it will not pretend a printout is a notarial testament.",
        ],
        "sources": [
            {"title": "Cornell Legal Information Institute: wills", "url": "https://www.law.cornell.edu/wex/wills"},
        ],
        "fields": [
            {"name": "full_name", "label": "Your full legal name", "type": "text", "required": True},
            {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True},
            {"name": "state", "label": "State where you live", "type": "select", "required": True, "options": list(STATES)},
            {"name": "county", "label": "County (or parish, in Louisiana)", "type": "text", "required": True},
            {"name": "address", "label": "Home address", "type": "text", "required": True},
            {"name": "email", "label": "Email", "type": "email"},
            {"name": "marital", "label": "Relationship status", "type": "select", "required": True, "options": MARITAL},
            {"name": "spouse", "label": "Spouse or partner's full legal name", "type": "text", "required": True,
             "show_if": {"field": "marital", "in": ["Married", "Domestic partnership or civil union"]}},
            {"name": "has_children", "label": "Do you have children, including adopted children?", "type": "select", "required": True, "options": YES_NO},
            {"name": "children", "label": "Children", "type": "list", "min": 1, "fields": PERSON,
             "show_if": {"field": "has_children", "in": ["Yes"]}},
            {"name": "owns_home", "label": "Do you own a home in your own name?", "type": "select", "required": True, "options": YES_NO},
            {"name": "outside", "label": "I understand retirement accounts and life insurance pass by beneficiary form, not by this document, unless I name this plan on those forms", "type": "checkbox", "required": True},
        ],
    }


def _people(executor_label: str) -> dict:
    return {
        "id": "people", "title": "Who acts for you",
        "guidance": [
            "Name adults. Name a backup. Do not name the same person as the only witness and the only beneficiary.",
            executor_label,
        ],
        "fields": [
            {"name": "primary", "label": "First choice", "type": "group", "fields": PERSON},
            {"name": "backup", "label": "Backup", "type": "group", "fields": [{"name": "full_name", "label": "Full legal name", "type": "text"}, {"name": "address", "label": "City and state", "type": "text"}]},
            {"name": "guardian", "label": "Guardian of minor children, if you have any", "type": "text"},
        ],
    }


US_WILL = {
    "id": "us_will",
    "country": "us",
    "title": "Last will and testament",
    "short_title": "US will",
    "category": "United States",
    "summary": "A last will for the state where you live. Two witnesses in most states. Louisiana is a different form. A trust is a separate choice if you want assets kept out of probate.",
    "steps": [
        _about("will"),
        _people("The executor collects what you own, pays debts, and gives what is left to the people you name. The court still has to appoint them."),
        {
            "id": "gifts", "title": "Who receives what",
            "guidance": ["Name the person and the gift. What you do not list, and what is not in a beneficiary form, falls into the residue."],
            "fields": [
                {"name": "gifts", "label": "Specific gifts", "type": "list", "fields": [
                    {"name": "item", "label": "Gift", "type": "text", "required": True},
                    {"name": "to", "label": "Who receives it", "type": "text", "required": True},
                ]},
                {"name": "residue", "label": "Who receives the rest, and in what shares", "type": "textarea", "required": True},
                {"name": "pets", "label": "Pets, and who should care for them", "type": "textarea"},
                {"name": "digital", "label": "Digital accounts you want someone to be able to reach", "type": "textarea"},
            ],
        },
    ],
    "next_steps": [
        "Read the signing instructions for your state on the draft. They are not the same in Louisiana or, for witnesses, in Pennsylvania.",
        "Sign the paper. Do not sign a scanned copy and email it back as the original.",
        "Keep the original. Tell your executor where it is. A will does not avoid probate.",
        "A lawyer in your state is optional. This is not legal advice.",
    ],
}

US_TRUST = {
    "id": "us_trust",
    "country": "us",
    "title": "Revocable living trust and pour-over will",
    "short_title": "US trust",
    "category": "United States",
    "summary": "A revocable trust you control in your lifetime, plus a pour-over will for anything left outside it. The trust avoids probate only for assets you actually transfer into it.",
    "steps": [
        _about("trust"),
        _people("The successor trustee takes over if you cannot, and after you die. While you are able, you are the trustee."),
        {
            "id": "gifts", "title": "After your death",
            "guidance": [
                "While you are alive you can change this trust or take assets back. That is what revocable means.",
                "A bank account or a house stays outside the trust until the title or the owner name is changed. This website does not change a deed or an account.",
                "Do not name the trust as beneficiary of a retirement account unless a tax adviser has said so. The tax result can be worse.",
            ],
            "fields": [
                {"name": "residue", "label": "Who receives the trust after your death, and in what shares", "type": "textarea", "required": True},
                {"name": "home", "label": "Home address to transfer into the trust later, if you want that", "type": "text"},
                {"name": "funded", "label": "I understand the trust does nothing for an asset until that asset is transferred into it", "type": "checkbox", "required": True},
            ],
        },
    ],
    "next_steps": [
        "Sign the trust and the pour-over will using your state's witness rules. The will still needs the witnesses. The trust usually needs a notary.",
        "Then change title: deed the home, and rename the accounts you want in the trust. Until you do, those assets are not in it.",
        "Leave retirement accounts and life insurance on their own beneficiary forms unless an adviser has told you otherwise.",
        "A lawyer in your state is optional. This is not legal advice, and it does not file a deed.",
    ],
}

US_POA = {
    "id": "us_poa",
    "country": "us",
    "title": "Durable financial power of attorney",
    "short_title": "US financial power",
    "category": "United States",
    "summary": "Name an agent for money and property. Durable means it continues if you cannot decide. It is not a healthcare directive, and it is not registered like a UK lasting power.",
    "steps": [
        _about("poa"),
        {
            "id": "people", "title": "Your agent",
            "guidance": ["The agent can spend your money. Name someone you trust, and a backup. Most states require a notary. Some also require witnesses. The draft says which caution applies. It does not replace your state's statutory form if a bank insists on that form."],
            "fields": [
                {"name": "primary", "label": "Agent", "type": "group", "fields": PERSON},
                {"name": "backup", "label": "Backup agent", "type": "group", "fields": [{"name": "full_name", "label": "Full legal name", "type": "text"}, {"name": "address", "label": "City and state", "type": "text"}]},
                {"name": "when", "label": "When can the agent act?", "type": "select", "required": True, "options": ["As soon as I sign", "Only if a doctor says I cannot manage my affairs"]},
                {"name": "powers", "label": "What they may do", "type": "textarea", "required": True, "hint": "For example: pay bills, deal with banks, sell a named car. Leave out a power you do not want."},
            ],
        },
    ],
    "next_steps": [
        "Sign in front of a notary. Add witnesses if your state or your bank requires them.",
        "This does not let the agent make medical decisions. Use the healthcare directive for that.",
        "It is not filed in a national register. Give a copy to the agent and to your bank.",
    ],
}

US_HEALTH = {
    "id": "us_health",
    "country": "us",
    "title": "Advance healthcare directive",
    "short_title": "US healthcare directive",
    "category": "United States",
    "summary": "Name a healthcare agent and say what treatment you want if you cannot speak. This is not a doctor's order (POLST or MOLST). A clinician signs those.",
    "steps": [
        _about("health"),
        {
            "id": "people", "title": "Healthcare agent and wishes",
            "guidance": ["Your agent should not be a witness. Two adult witnesses is the usual rule. Some states want a notary as well, or bar a relative from witnessing. Follow the instruction on the draft, then check your state's form if a hospital asks for it."],
            "fields": [
                {"name": "primary", "label": "Healthcare agent", "type": "group", "fields": PERSON},
                {"name": "backup", "label": "Backup agent", "type": "group", "fields": [{"name": "full_name", "label": "Full legal name", "type": "text"}, {"name": "address", "label": "City and state", "type": "text"}]},
                {"name": "wishes", "label": "Treatment you want, or do not want, if you cannot decide", "type": "textarea", "required": True},
                {"name": "organs", "label": "Organ and tissue donation", "type": "select", "required": True, "options": ["I do not want to donate", "I want to donate", "My agent decides"]},
            ],
        },
    ],
    "next_steps": [
        "Sign with the witnesses your state requires. Do not ask your agent to witness.",
        "Give copies to the agent and to your doctor. A POLST or MOLST, if you want one, is a medical order your clinician signs. This document is not that order.",
    ],
}

US_PROBATE = {
    "id": "us_probate",
    "country": "us",
    "title": "Probate, for the person handling an estate",
    "short_title": "US probate",
    "category": "United States",
    "summary": "A checklist for the personal representative. You still open the estate in the probate court of the county where the person lived. This site does not file it.",
    "steps": [
        {
            "id": "about", "title": "The person who died",
            "guidance": [
                "Probate is the court process. A trust does not put assets through it if they were transferred into the trust. A will does not avoid it.",
                "The creditor deadline is set by the state. It is often a few months after notice is given. Do not use a number from another state.",
            ],
            "sources": [{"title": "Cornell Legal Information Institute: wills", "url": "https://www.law.cornell.edu/wex/wills"}],
            "fields": [
                {"name": "decedent", "label": "Full name of the person who died", "type": "text", "required": True},
                {"name": "date_of_death", "label": "Date of death", "type": "date", "required": True},
                {"name": "state", "label": "State where they lived", "type": "select", "required": True, "options": list(STATES)},
                {"name": "county", "label": "County or parish", "type": "text", "required": True},
                {"name": "has_will", "label": "Is there a will?", "type": "select", "required": True, "options": ["Yes, I have the original", "There may be one, I have not found it", "No"]},
                {"name": "your_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "your_role", "label": "Why you are the person to start", "type": "select", "required": True, "options": ["I am named as executor", "I am the spouse", "I am a child", "I am another relative", "I am not sure"]},
            ],
        },
    ],
    "next_steps": [
        "Find the original will. Do not write on it.",
        "File in the probate court for the county where they lived. This website cannot open the estate.",
        "Ask that court how long creditors have. Do not pay everyone out before that period, and do not ignore a bill you already know about.",
        "Federal estate tax is a separate question from probate. It applies only above the exemption for the year of death. This page does not calculate it.",
    ],
}

US_SERVICES = (US_WILL, US_TRUST, US_POA, US_HEALTH, US_PROBATE)
