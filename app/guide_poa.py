"""Ordinary (general) and specific powers of attorney under the Powers of Attorney Act 1971.

This is not a lasting power of attorney. It does not need OPG registration. It stops if the
donor loses mental capacity. DRAFT WORDING: needs lawyer review before it goes live.
This is not legal advice.
"""
from .fields import ATTORNEY, GOV

POA_ORDINARY = {
    "id": "poa_ordinary",
    "title": "Ordinary or general power of attorney",
    "short_title": "Ordinary power of attorney",
    "category": "Powers of attorney",
    "summary": "A general power of attorney under section 10 of the Powers of Attorney Act 1971, or a specific power limited to one task such as a property sale. It can be used as soon as it is signed and witnessed as a deed. It is not an LPA and it stops if you lose mental capacity.",
    "review_video": "poa_review",
    "steps": [
        {
            "id": "intro",
            "title": "Before you start",
            "video": "poa_intro",
            "guidance": [
                "This prepares an ordinary power of attorney for England and Wales. It is sometimes called a general power of attorney. There is also a specific (limited) option for one exact task, such as completing a particular property sale.",
                "A general power in the statutory form in Schedule 1 to the Powers of Attorney Act 1971, or a form to the like effect expressed to be made under that Act, gives your attorney authority to do on your behalf anything you can lawfully do by an attorney. It does not usually cover functions you have as a trustee or personal representative, or as a tenant for life or statutory owner under the Settled Land Act 1925, except as modified by the Trustee Delegation Act 1999.",
                "It becomes usable when you sign it as a deed in front of a witness. You do not register it with the Office of the Public Guardian. By contrast, a lasting power of attorney (LPA) must be registered with OPG before it can be used, which currently takes 8 to 10 weeks if there are no mistakes, and costs a fee.",
                "An ordinary power of attorney stops automatically if you die, become bankrupt, or lose mental capacity. You can also revoke it at any time while you have capacity. It is not a substitute for an LPA. If you want someone to act after you lose capacity, you need a lasting power of attorney.",
                "Use a general power when you want to give broad authority for a period while you still have capacity, for example if you will be abroad or in hospital but able to make your own decisions. Use a specific power when you want to limit the attorney to one exact task.",
                "This is not legal advice. The draft is for solicitor review and must not be signed until a solicitor has checked it. Land transactions have extra requirements; see HM Land Registry Practice Guide 9.",
            ],
            "sources": [GOV["poa_act"], GOV["poa_sch1"], GOV["pg9"], GOV["lpa"], GOV["lp12"]],
            "fields": [],
        },
        {
            "id": "type",
            "title": "General or specific",
            "video": "poa_type",
            "guidance": [
                "A general power uses the short statutory form in Schedule 1 to the Powers of Attorney Act 1971. It is wide: your attorney can do most things you could lawfully appoint an attorney to do.",
                "A specific (limited) power is not a statutory form. HM Land Registry Practice Guide 9 says you may use any form of wording that gives limited powers, for example in connection with a particular transaction, but the donor must execute it as a deed. A solicitor should draft or check a specific power, especially if it will be used to deal with land or registered title.",
            ],
            "sources": [GOV["poa_sch1"], GOV["pg9"]],
            "fields": [
                {
                    "name": "poa_type",
                    "label": "Which type do you need?",
                    "type": "select",
                    "required": True,
                    "options": [
                        "General power of attorney (Powers of Attorney Act 1971, section 10)",
                        "Specific (limited) power of attorney for one exact task",
                    ],
                },
                {
                    "name": "understood_capacity",
                    "label": "I understand this power stops if I lose mental capacity, and that it is not a substitute for a lasting power of attorney",
                    "type": "checkbox",
                    "required": True,
                },
            ],
        },
        {
            "id": "donor",
            "title": "About you",
            "video": "poa_donor",
            "guidance": [
                "You are the donor of the power. Use your full legal name and the address you want to appear on the deed.",
                "You must have mental capacity when you sign. The power must be executed as a deed: you sign it in the presence of a witness who attests your signature. The witness should be an independent adult and should give their name, address and occupation.",
            ],
            "sources": [GOV["poa_act"], GOV["lpmpa"], GOV["pg9"]],
            "fields": [
                {"name": "full_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "address", "label": "Your address", "type": "textarea", "required": True},
                {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
            ],
        },
        {
            "id": "attorneys",
            "title": "Your attorneys",
            "video": "poa_attorneys",
            "guidance": [
                "You can appoint one attorney, or more than one. If you appoint more than one, say whether they must act jointly (all must agree) or may act jointly and severally (they can act together or on their own). The statutory general form provides for either.",
                "Choose people you trust. If the power will be used for a property sale or a business matter, they should be able to deal with that task in practice.",
            ],
            "sources": [GOV["poa_sch1"], GOV["poa_act"]],
            "fields": [
                {"name": "attorneys", "label": "Attorneys", "type": "list", "min": 1, "max": 4, "fields": ATTORNEY},
                {
                    "name": "how_they_act",
                    "label": "If you appoint more than one attorney, how should they act?",
                    "type": "select",
                    "required": True,
                    "options": ["Only one attorney", "Jointly", "Jointly and severally"],
                },
            ],
        },
        {
            "id": "authority",
            "title": "What the power covers",
            "video": "poa_authority",
            "guidance": [
                "If you chose a general power, the statutory form does not list individual tasks. Section 10 of the Powers of Attorney Act 1971 sets the width of the authority, including the trustee and personal-representative limits described earlier.",
                "If you chose a specific power, describe the exact task in plain language, for example 'to complete the sale of my property at [address] under the contract dated [date]'. Do not try to turn a specific power into a general one. A solicitor should check the wording, and should always check it if the task involves land, a company, or a formal registration.",
                "You can say when you would like the power to end, for example on a date or when the task is finished. That extra wording is not in the statutory general form, so it is flagged for a solicitor to review and should not be signed until they have checked it.",
            ],
            "sources": [GOV["poa_act"], GOV["poa_sch1"], GOV["pg9"]],
            "fields": [
                {
                    "name": "task",
                    "label": "The exact task this specific power is limited to",
                    "type": "textarea",
                    "required": True,
                    "show_if": {"field": "poa_type", "in": []},
                    "hint": "This question is asked on the next screen if you chose a specific power. If you can see it here, describe the one task clearly.",
                },
                {
                    "name": "end_wish",
                    "label": "Should this power end on a particular date or when the task is finished? (optional, solicitor to review)",
                    "type": "select",
                    "options": [
                        "No extra end date — I will revoke it if I need to, and it will end if I lose capacity, die or become bankrupt",
                        "I would like it to end on a date",
                        "I would like it to end when the specific task is finished",
                    ],
                },
                {
                    "name": "end_date",
                    "label": "The date you would like it to end",
                    "type": "date",
                    "required": True,
                    "show_if": {"field": "end_wish", "in": ["I would like it to end on a date"]},
                },
            ],
        },
    ],
    "next_steps": [
        "A solicitor reviews this draft. Do not sign it until they have approved it. This is not legal advice.",
        "Sign the approved deed in the presence of an independent adult witness, who then signs and adds their name, address and occupation.",
        "Give the attorney a copy, and keep the original safe. It can be used at once. It is not registered with the Office of the Public Guardian.",
        "It ends if you revoke it, or if you die, become bankrupt or lose mental capacity. If you need someone to act after you lose capacity, make a lasting power of attorney as well.",
        "If the attorney will deal with registered land, ask the solicitor to check HM Land Registry Practice Guide 9 before it is used.",
    ],
}


def _fix_authority_show_if():
    """The specific-task field must follow the type chosen on the previous step.

    show_if only looks at answers in the same step, so the task field is required
    in document checks when the chosen type is specific, not via show_if across steps.
    """
    for step in POA_ORDINARY["steps"]:
        if step["id"] != "authority":
            continue
        for field in step["fields"]:
            if field["name"] == "task":
                # Always visible on this step; required-ness is enforced in doc_poa.poa_issues
                # and missing_fields is adjusted by making it not required here.
                field.pop("show_if", None)
                field["required"] = False
                field["hint"] = (
                    "Fill this in if you chose a specific (limited) power. Leave it blank if you chose a general power. "
                    "Describe one exact task, such as a named property sale."
                )


_fix_authority_show_if()
