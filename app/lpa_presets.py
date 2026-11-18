"""Official LPA preference and instruction presets for section 7.

Word-for-word examples and warnings are taken from public sources. Do not invent
new operative wording here. Current official guidance is LP12, updated 3 November 2026:
https://www.gov.uk/government/publications/lasting-power-of-attorney-forms/lp12-make-and-register-your-lasting-power-of-attorney-a-guide-web-version

DRAFT: a solicitor (England and Wales) must review any wording before a client signs.
"""
from .fields import GOV

LP12 = GOV["lp12"]
LAW_SOC_DFM = GOV["law_soc_dfm"]

# Each preset is a tick-box the client can choose. `wording` is copied into LP1F/LP1H
# section 7 as a preference or an instruction, as `section` says.
PRESETS = [
    {
        "id": "professional_fees",
        "applies_to": ("lpa_property", "lpa_health"),
        "section": "instructions",
        "label": "I am happy for my attorneys to be paid if they are professional",
        "wording": "I wish my professional attorneys to be paid the standard solicitor rate as set by [state the name of a relevant professional organisation here].",
        "organisation_field": "professional_fee_organisation",
        "source": LP12,
        "source_note": "LP12, 'Professional attorneys' (updated 3 November 2026).",
        "warning": "LP12 says that if you agree to pay a fee you must write this in your instructions; if you do not, the attorney cannot be paid. They can still claim reasonable expenses. A solicitor should check the rate and the organisation you name. Fees are paid out of your funds.",
    },
    {
        "id": "discretionary_investments",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "I am happy for my attorneys to deal with stocks and shares, including a discretionary investment management service or a nominee name",
        "wording": (
            "My attorneys may transfer my investments into a discretionary management scheme. "
            "Or, if I already had investments in a discretionary management scheme before I lost capacity "
            "to make financial decisions, I want the scheme to continue. I understand in both cases that "
            "managers of the scheme will make investment decisions and my investments will be held in their "
            "names or the names of their nominees."
        ),
        "source": LAW_SOC_DFM,
        "source_note": (
            "This is the former OPG 'standard clause X' published in LP12 until March 2022, as quoted by "
            "The Law Society, 'A good investment' (12 May 2022). The current LP12 (updated 3 November 2026) "
            "no longer prints this clause. It instead says you should consider taking legal advice on whether "
            "specific provision is necessary, because at least one major financial institution has required an "
            "express instruction. A property and financial affairs LPA already covers making or selling "
            "investments; this extra instruction is about discretionary management and nominee holdings."
        ),
        "warning": (
            "This is not in the current official LP12 form of words. Some financial institutions still ask for "
            "an express instruction like this. A solicitor should review it before you rely on it. Complicated "
            "or badly worded instructions can make an LPA unworkable (LP12)."
        ),
        "solicitor_review": True,
    },
    {
        "id": "ethical_funds",
        "applies_to": ("lpa_property",),
        "section": "preferences",
        "label": "I prefer my money to be invested in ethical funds",
        "wording": "I prefer to invest in ethical funds.",
        "source": LP12,
        "source_note": "LP12, example preference for a property and financial affairs LPA.",
    },
    {
        "id": "isa_reinvest",
        "applies_to": ("lpa_property",),
        "section": "preferences",
        "label": "I like interest from my investments to go into next year's ISA allowance",
        "wording": "I like to reinvest all interest from each year's investments into next year's ISA allowance.",
        "source": LP12,
        "source_note": "LP12, example preference for a property and financial affairs LPA.",
    },
    {
        "id": "min_current_account",
        "applies_to": ("lpa_property",),
        "section": "preferences",
        "label": "I would like a minimum balance of £1,000 kept in my current account",
        "wording": "I would like to maintain a minimum balance of £1,000 in my current account.",
        "source": LP12,
        "source_note": "LP12, example preference. If you want a different amount, leave this unticked and write your own preference in the box, using words such as 'would like' or 'prefer'.",
    },
    {
        "id": "consult_doctor_house",
        "applies_to": ("lpa_property",),
        "section": "preferences",
        "label": "I would like my attorneys to consult my doctor about whether I can still decide about my house",
        "wording": "I'd like my attorneys to consult my doctor if they think I don't have the mental capacity to make decisions about my house.",
        "source": LP12,
        "source_note": "LP12, example preference for a property and financial affairs LPA.",
    },
    {
        "id": "consult_adviser_10k",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "My attorneys must consult a financial adviser before making investments over £10,000",
        "wording": "My attorneys must consult a financial adviser before making investments over £10,000.",
        "source": LP12,
        "source_note": "LP12, example instruction for a property and financial affairs LPA.",
        "warning": "This is a binding instruction. If you want a different amount, leave this unticked and write your own instruction in the box, using words such as 'must'. Instructions can cause more problems than preferences (LP12).",
    },
    {
        "id": "tax_accountant",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "My attorneys must instruct a tax accountant to prepare my annual tax return",
        "wording": "My attorneys must instruct a tax accountant to prepare my annual tax return.",
        "source": LP12,
        "source_note": "LP12, example instruction for a property and financial affairs LPA.",
    },
    {
        "id": "annual_accounts",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "My attorneys must send annual accounts to my brothers and sisters",
        "wording": "My attorneys must send annual accounts to my brothers and sisters.",
        "source": LP12,
        "source_note": "LP12, example instruction. If you want different people to receive the accounts, leave this unticked and write your own instruction in the box, naming them and using 'must'.",
        "warning": "The official example names brothers and sisters. Write your own instruction if that is not who should see the accounts.",
    },
    {
        "id": "must_not_sell_home",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "My attorneys must not sell my home unless my doctor says I can no longer live independently",
        "wording": "My attorneys must not sell my home unless, in my doctor's opinion, I can no longer live independently.",
        "source": LP12,
        "source_note": "LP12, example instruction for a property and financial affairs LPA.",
        "warning": "This is a binding instruction. If your home later needs to be sold, for example to pay for care, this wording can stop your attorneys acting until the condition is met, or make the LPA hard to use. LP12 says complicated or badly worded instructions can make an LPA unworkable. A solicitor should review this.",
        "solicitor_review": True,
    },
    {
        "id": "must_not_make_gifts",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "My attorneys must not make any gifts",
        "wording": "My attorneys must not make any gifts.",
        "source": LP12,
        "source_note": "LP12, example instruction for a property and financial affairs LPA.",
        "warning": "LP12 says there are strict legal limits on gifts attorneys may make, even if you do not include this instruction. Do not add a binding instruction that attorneys 'must' make gifts or maintain other people (other than a spouse, civil partner or a child under 18) — those instructions are likely to be invalid. A preference ('I would like') may be valid, but attorneys still have to act in your best interests.",
    },
    {
        "id": "capacity_assessment",
        "applies_to": ("lpa_property",),
        "section": "instructions",
        "label": "This LPA should only apply if a doctor confirms in writing that I cannot decide about my finances",
        "wording": "This lasting power of attorney only applies if a doctor confirms in writing that I don't have the capacity to make decisions about my finances.",
        "source": LP12,
        "source_note": "LP12 example for donors who chose, in section 5, that attorneys may act only when the donor has lost mental capacity. LP12 says you do not need this if you trust your attorneys to judge your capacity.",
        "warning": "Use this only if you have also chosen that attorneys may act only when you do not have mental capacity (section 5). Extra conditions can delay decisions.",
    },
    {
        "id": "live_near_family",
        "applies_to": ("lpa_health",),
        "section": "preferences",
        "label": "I prefer to live within five miles of my sister",
        "wording": "I prefer to live within five miles of my sister.",
        "source": LP12,
        "source_note": "LP12, example preference for a health and welfare LPA. If this is not your wish, leave it unticked and write your own preference, for example naming another person or a place.",
    },
    {
        "id": "generic_medicines",
        "applies_to": ("lpa_health",),
        "section": "preferences",
        "label": "I would like to be prescribed generic medicines where they are available",
        "wording": "I'd like to be prescribed generic medicines where they are available.",
        "source": LP12,
        "source_note": "LP12, example preference for a health and welfare LPA.",
    },
    {
        "id": "exercise_outdoors",
        "applies_to": ("lpa_health",),
        "section": "preferences",
        "label": "I would like regular exercise and time outdoors when I am able",
        "wording": "I would like to take exercise at least three times a week whenever I am physically able to do so. Whether or not I am mobile, I would like to spend time outdoors at least once a day.",
        "source": LP12,
        "source_note": "LP12, example preference for a health and welfare LPA.",
    },
    {
        "id": "pets_with_me",
        "applies_to": ("lpa_health",),
        "section": "preferences",
        "label": "I would like my pets to live with me for as long as possible, including in a care home",
        "wording": "I'd like my pets to live with me for as long as possible – if I go into a care home, I'd like to take them with me.",
        "source": LP12,
        "source_note": "LP12, example preference for a health and welfare LPA.",
    },
    {
        "id": "must_not_residential_care",
        "applies_to": ("lpa_health",),
        "section": "instructions",
        "label": "My attorneys must not decide I should move into residential care unless my doctor says I can no longer live independently",
        "wording": "My attorneys must not decide I am to move into residential care unless, in my doctor's opinion, I can no longer live independently.",
        "source": LP12,
        "source_note": "LP12, example instruction for a health and welfare LPA.",
        "warning": "This is a binding instruction about staying in your home. It can make care decisions slower or harder if a move is needed. LP12 says complicated or badly worded instructions can make an LPA unworkable. A solicitor should review this. Life-sustaining treatment is decided separately in section 5, not in this box.",
        "solicitor_review": True,
    },
    {
        "id": "no_blood_products",
        "applies_to": ("lpa_health",),
        "section": "instructions",
        "label": "My attorneys must not consent to medical treatment involving blood products, as this is against my religion",
        "wording": "My attorneys must not consent to any medical treatment involving blood products, as this is against my religion.",
        "source": LP12,
        "source_note": "LP12, example instruction for a health and welfare LPA.",
        "warning": "Only tick this if it is truly your religious or other belief. A solicitor should review medical instructions. LP12 also says you cannot tell attorneys to do anything against the law, including anything to do with euthanasia or assisted suicide.",
        "solicitor_review": True,
    },
    {
        "id": "vegetarian_food",
        "applies_to": ("lpa_health",),
        "section": "instructions",
        "label": "My attorneys must ensure I am given only vegetarian food",
        "wording": "My attorneys must ensure I am given only vegetarian food.",
        "source": LP12,
        "source_note": "LP12, example instruction for a health and welfare LPA.",
    },
]

BUSINESS_INSTRUCTIONS = [
    {
        "id": "personal_only",
        "purpose": "Personal finances only",
        "section": "instructions",
        "label": "Limit this LPA to my personal finances (not my business)",
        "wording": "My attorneys only have the authority to use my personal bank account. They are not permitted to access my business account or make any decisions relating to my business.",
        "source": LP12,
        "source_note": "LP12, 'Special case: making two LPAs for property and financial affairs'.",
        "warning": "Use this if you are also making, or will make, a second LP1F for your business affairs. A solicitor should check that the two LPAs do not overlap or leave a gap.",
        "solicitor_review": True,
    },
    {
        "id": "business_only",
        "purpose": "Business affairs only",
        "section": "instructions",
        "label": "Limit this LPA to my business affairs (not my personal finances)",
        "wording": "My attorneys only have the authority to use my business accounts and make decisions relating to my business. They are not permitted to use my personal account or make decisions about my personal finances.",
        "source": LP12,
        "source_note": "LP12, 'Special case: making two LPAs for property and financial affairs'.",
        "warning": "Use this if you are also making, or will make, a second LP1F for your personal finances. A solicitor should check that the two LPAs do not overlap or leave a gap, and that this wording fits any partnership or shareholders' agreement.",
        "solicitor_review": True,
    },
]


def presets_for(kind: str) -> list[dict]:
    return [p for p in PRESETS if kind in p["applies_to"]]


def preset_fields(kind: str) -> list[dict]:
    """Checkbox fields (plus any follow-up text) for the preferences step."""
    fields = []
    for p in presets_for(kind):
        hint_parts = [p["source_note"]]
        if p.get("warning"):
            hint_parts.append("Warning: " + p["warning"])
        fields.append({
            "name": "preset_" + p["id"],
            "label": p["label"],
            "type": "checkbox",
            "wording": p["wording"],
            "section": p["section"],
            "warning": p.get("warning", ""),
            "hint": " ".join(hint_parts),
        })
        if p.get("organisation_field"):
            fields.append({
                "name": p["organisation_field"],
                "label": "Name of the professional organisation that sets the rate (optional)",
                "type": "text",
                "show_if": {"field": "preset_" + p["id"], "in": [True]},
                "hint": "LP12 asks you to state the name of a relevant professional organisation in this instruction. A solicitor should check it.",
            })
    return fields


def business_instruction_fields() -> list[dict]:
    fields = []
    for p in BUSINESS_INSTRUCTIONS:
        fields.append({
            "name": "preset_business_" + p["id"],
            "label": p["label"],
            "type": "checkbox",
            "wording": p["wording"],
            "section": p["section"],
            "warning": p.get("warning", ""),
            "hint": p["source_note"] + " Warning: " + p.get("warning", ""),
            "show_if": {"field": "purpose", "in": [p["purpose"]]},
        })
    return fields


def _fill_professional_fees(wording: str, answers: dict) -> str:
    org = (answers.get("professional_fee_organisation") or "").strip()
    if not org:
        return wording
    return (
        "I wish my professional attorneys to be paid the standard solicitor rate as set by "
        + org + "."
    )


def selected_wordings(kind: str, answers: dict) -> list[dict]:
    """Chosen presets with the wording to write on the form."""
    out = []
    prefs = answers.get("preferences") or {}
    for p in presets_for(kind):
        if prefs.get("preset_" + p["id"]) is True:
            wording = p["wording"]
            if p.get("organisation_field"):
                wording = _fill_professional_fees(wording, prefs)
            out.append({**p, "wording": wording})
    biz = answers.get("business") or {}
    for p in BUSINESS_INSTRUCTIONS:
        if biz.get("preset_business_" + p["id"]) is True:
            out.append(p)
    return out
