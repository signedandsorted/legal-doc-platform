"""Lasting power of attorney, structured on the official OPG forms LP1F (financial decisions)
and LP1H (health and care decisions). Each step names the form section it fills.
DRAFT WORDING: needs lawyer review before it goes live."""
from .fields import ATTORNEY, GOV, PERSON, YES_NO, optional
from .lpa_presets import business_instruction_fields, preset_fields

LPA_FEE = 92  # GOV.UK "Register a lasting power of attorney", checked 17 Nov 2026
LPA_FEE_BOTH = 184
LPA_RETRY_FEE = 46

CP_CHECKS = [
    ("cp_over_18", "They are 18 or over"),
    ("cp_not_attorney", "They are not one of my attorneys or replacement attorneys"),
    ("cp_not_family", "They are not a member of my family or of an attorney's family (including partners, in-laws and step-family)"),
    ("cp_not_partner", "They are not my or an attorney's unmarried partner, boyfriend or girlfriend"),
    ("cp_not_business", "They are not my or an attorney's business partner or employee"),
    ("cp_not_care_home", "They do not own, run or work for a care home where I live, and are not a relative of someone who does"),
]


def lpa_service(kind: str) -> dict:
    prop = kind == "lpa_property"
    form = "LP1F" if prop else "LP1H"
    short = "financial decisions" if prop else "health and care decisions"
    steps = [
        {
            "id": "intro", "title": "Before you start", "video": "lpa_property_intro" if prop else "lpa_health_intro",
            "guidance": [
                f"This prepares a lasting power of attorney (LPA) for {short}, following the official OPG form {form} section by section.",
                ("It lets people you trust manage your bank accounts, pay bills, collect benefits and pensions, and buy or sell your home." if prop else
                 "It lets people you trust make decisions about your daily care, medical treatment, where you live and, if you choose, life-sustaining treatment. It can only be used when you cannot make the decision yourself."),
                "You must be 18 or over and able to make your own decisions when you sign. Everyone signs the same original paper form; copies and digital signatures are not accepted.",
                f"The LPA must be registered with the Office of the Public Guardian (OPG) before it can be used. Registration costs £{LPA_FEE} (£{LPA_FEE_BOTH} for both types) and takes 8 to 10 weeks if there are no mistakes.",
                "You can also make an LPA with the GOV.UK online service. Our pack tells you exactly what to put in each section either way, and a solicitor checks it first.",
            ],
            "sources": [GOV["lpa"], GOV["lpa_forms"], GOV["lpa_make"]],
            "fields": [],
        },
        {
            "id": "donor", "title": "About you (section 1)", "form_section": f"{form} section 1", "video": "lpa_donor",
            "guidance": ["On the form you are the 'donor'. Give your name exactly as you want it to appear, and any other names you are known by (for example on bank accounts)."],
            "sources": [GOV["lpa_make"]],
            "fields": [
                {"name": "full_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "other_names", "label": "Other names you are known by (optional)", "type": "text"},
                {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True},
                {"name": "address", "label": "Your address", "type": "textarea", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "existing_lpa", "label": "Do you already have an LPA or an enduring power of attorney (EPA)?", "type": "select", "options": ["No", "Yes, an LPA", "Yes, an EPA", "Not sure"]},
            ],
        },
        {
            "id": "attorneys", "title": "Your attorneys (section 2)", "form_section": f"{form} section 2", "video": "lpa_attorneys",
            "guidance": [
                "Attorneys must be 18 or over and able to make their own decisions. They do not need to live in the UK.",
                ("You cannot choose someone who is bankrupt or subject to a debt relief order for a financial decisions LPA." if prop else
                 "Choose people who know your wishes about care and treatment and will respect them."),
                "The form has space for 4 attorneys. If you add more, we put the rest on continuation sheet 1.",
            ],
            "sources": [GOV["lpa_choose"]],
            "fields": [
                {"name": "attorneys", "label": "Attorneys", "type": "list", "min": 1, "max": 10, "fields": ATTORNEY},
            ] + ([{"name": "not_bankrupt", "label": "I confirm none of my attorneys is bankrupt or subject to a debt relief order", "type": "checkbox", "required": True}] if prop else []),
        },
        {
            "id": "decisions", "title": "How your attorneys decide (section 3)", "form_section": f"{form} section 3", "video": "lpa_decisions",
            "guidance": [
                "Only answer this if you have more than one attorney.",
                "Jointly and severally: they can act together or on their own. Jointly: they must all agree on every decision, and if one stops acting the LPA may stop working. Or a mix: some decisions jointly, others jointly and severally.",
                "If you choose a mix, say exactly which decisions must be made jointly. Unclear wording is a common reason LPAs are rejected.",
            ],
            "sources": [GOV["lpa_choose"]],
            "fields": [
                {"name": "decisions", "label": "How should they make decisions?", "type": "select", "required": True, "options": ["Only one attorney", "Jointly and severally", "Jointly", "Jointly for some decisions, jointly and severally for others"]},
                {"name": "joint_decisions", "label": "Which decisions must be made jointly?", "type": "textarea", "required": True, "show_if": {"field": "decisions", "in": ["Jointly for some decisions, jointly and severally for others"]}},
            ],
        },
        {
            "id": "replacements", "title": "Replacement attorneys (section 4)", "form_section": f"{form} section 4", "video": "lpa_replacements",
            "guidance": [
                "Replacement attorneys step in if an attorney can no longer act, for example if they die, lose capacity or (for financial LPAs) become bankrupt. They are optional but recommended.",
                "A replacement cannot also be one of your main attorneys.",
            ],
            "sources": [GOV["lpa_choose"]],
            "fields": [
                {"name": "replacement_attorneys", "label": "Replacement attorneys (optional)", "type": "list", "min": 0, "max": 10, "fields": ATTORNEY},
                {"name": "replacement_instructions", "label": "Anything about when or how replacements step in (optional, goes on continuation sheet 2)", "type": "textarea"},
            ],
        },
    ]
    if prop:
        steps.append({
            "id": "when", "title": "When your attorneys can act (section 5)", "form_section": "LP1F section 5", "video": "lpa_property_when",
            "guidance": [
                "You can let your attorneys act as soon as the LPA is registered (with your permission while you can still decide for yourself), or only when you do not have mental capacity.",
                "Many people choose 'as soon as registered' because it is practical, for example if you are in hospital or cannot get to the bank.",
            ],
            "sources": [GOV["lpa_forms"]],
            "fields": [{"name": "when_used", "label": "When can your attorneys use the LPA?", "type": "select", "required": True, "options": ["As soon as it is registered", "Only when I do not have mental capacity"]}],
        })
    else:
        steps.append({
            "id": "life_sustaining", "title": "Life-sustaining treatment (section 5)", "form_section": "LP1H section 5", "video": "lpa_health_life_sustaining",
            "guidance": [
                "Life-sustaining treatment is care or medicine needed to keep you alive, for example a ventilator or CPR.",
                "Option A gives your attorneys authority to give or refuse consent on your behalf. Option B means they cannot; your doctors decide, taking your attorneys' views into account.",
                "You sign this section in front of a witness at the same time as you sign section 9.",
                "This choice stays in section 5. Do not put life-sustaining treatment instructions in section 7 (preferences and instructions). You can add other care preferences, such as food or everyday treatment, in section 7.",
            ],
            "sources": [GOV["lpa_forms"], GOV["lp12"]],
            "fields": [{"name": "life_sustaining", "label": "Life-sustaining treatment", "type": "select", "required": True, "options": ["Option A: my attorneys can give or refuse consent", "Option B: my attorneys cannot give or refuse consent"]}],
        })
    if prop:
        steps.append({
            "id": "business", "title": "Business or personal finances", "form_section": "LP1F section 7 (if you limit the LPA)",
            "guidance": [
                "You can appoint different attorneys for your personal finances and your business affairs. To do this, fill in two LP1F forms. Official guidance (LP12) says you should then explain in the instructions for each LPA what you want to happen, so the two do not overlap.",
                "A separate business LPA is worth considering if you want a different attorney for the business, or if you want to keep business accounts and decisions apart from your household finances. Talk to any co-owners, partners or fellow shareholders first, and check the partnership agreement, shareholders' agreement or articles. Choose attorneys who understand the business.",
                "Do not use an instruction in a single LPA to give one attorney the business and another your personal affairs if you have appointed them jointly and severally. LP12 says that sort of instruction means the LPA will not work. Make two LPAs instead.",
                "This is not legal advice. A solicitor should check both LPAs and any business agreement before you sign.",
            ],
            "sources": [GOV["lp12"], GOV["lpa_forms"]],
            "fields": [
                {"name": "has_business", "label": "Do you own a business, a farm, or shares in a company that this LPA should deal with?", "type": "select", "options": YES_NO},
                {"name": "purpose", "label": "What should this LPA cover?", "type": "select", "required": True, "show_if": {"field": "has_business", "in": ["Yes"]},
                 "options": ["Personal finances only", "Business affairs only", "Both personal and business (same attorneys)"],
                 "hint": "If you want different attorneys for the business and for your personal finances, make two LP1F forms instead of choosing 'both'."},
                {"name": "talked_to_co_owners", "label": "Have you talked to any co-owners, partners or fellow shareholders?", "type": "select", "show_if": {"field": "has_business", "in": ["Yes"]},
                 "options": ["Yes", "Not yet", "There are no co-owners", "Not sure"]},
                {"name": "has_agreement", "label": "Is there a partnership agreement, shareholders' agreement or similar that deals with incapacity?", "type": "select", "show_if": {"field": "has_business", "in": ["Yes"]},
                 "options": ["Yes", "No", "Not sure"],
                 "hint": "A solicitor should check that this LPA does not conflict with that agreement."},
            ] + business_instruction_fields(),
        })
    steps += [
        {
            "id": "notify", "title": "People to notify (section 6)", "form_section": f"{form} section 6", "video": "lpa_notify",
            "guidance": [
                "People to notify are an extra safeguard. Before the LPA is registered they are sent form LP3 and have 3 weeks to raise concerns with OPG.",
                "You can name up to 5. They cannot be your attorneys or replacement attorneys. This is optional.",
            ],
            "sources": [GOV["lpa_register"], GOV["lpa_forms"]],
            "fields": [{"name": "people_to_notify", "label": "People to notify (optional)", "type": "list", "min": 0, "max": 5, "fields": PERSON[:2]}],
        },
        {
            "id": "preferences", "title": "Preferences and instructions (section 7)", "form_section": f"{form} section 7", "video": "lpa_preferences",
            "guidance": [
                "Preferences are what you would like your attorneys to think about. They should bear them in mind but do not have to follow them. Official guidance says to use words such as 'prefer' and 'would like', not 'must' or 'shall'.",
                "Instructions tell your attorneys what they must do. Use words such as 'must', 'shall' and 'have to'. Official guidance says instructions can cause more problems than preferences, and that complicated or badly worded instructions or preferences can make an LPA unworkable.",
                "Tick any official example wording that you want copied into section 7. You can also write your own in the boxes. The examples are from the Office of the Public Guardian's LP12 guide (updated 3 November 2026), except the discretionary investment wording, which is the former OPG clause no longer printed in LP12 — see the warning on that option.",
                "Most people leave this page blank and just talk to their attorneys. If you are not sure, get legal advice. Life-sustaining treatment on a health and welfare LPA is decided in section 5, not in this box. LP12 also notes that attorneys must already consult family and friends when working out your best interests, so you do not have to add a separate instruction about that.",
                "Anything that does not fit the boxes goes on continuation sheet 2.",
            ],
            "sources": [GOV["lpa_forms"], GOV["lp12"], GOV["lpa_errors"]],
            "fields": preset_fields(kind) + [
                {"name": "preferences", "label": "Any other preferences (optional)", "type": "textarea", "hint": "Use words such as 'prefer' and 'would like'."},
                {"name": "instructions", "label": "Any other instructions (optional)", "type": "textarea", "hint": "Use words such as 'must', 'shall' and 'have to'. Avoid instructions that the law will not allow — see the warnings on the tick-box options and in LP12."},
            ],
        },
        {
            "id": "certificate_provider", "title": "Your certificate provider (section 10)", "form_section": f"{form} section 10", "video": "lpa_certificate_provider",
            "guidance": [
                "Your certificate provider confirms you understand the LPA and are not being pressured into making it.",
                "They must be 18 or over and either have known you personally for at least 2 years, or have relevant professional skills (for example your GP, a solicitor or a social worker).",
                "Many people cannot do it. Please confirm each check below; we also compare their name with your attorneys, people to notify and any earlier LPA you upload.",
            ],
            "sources": [GOV["lpa_make"], GOV["lpa_forms"]],
            "fields": [
                PERSON[0], PERSON[1],
                {"name": "basis", "label": "How do they qualify?", "type": "select", "required": True, "options": ["Known me personally for at least 2 years", "Relevant professional skills (doctor, solicitor, social worker etc.)"]},
            ] + [{"name": k, "label": label, "type": "checkbox", "required": True} for k, label in CP_CHECKS],
        },
        {
            "id": "registration", "title": "Registering your LPA (sections 12 to 15)", "form_section": f"{form} sections 12-15", "video": "lpa_registration",
            "guidance": [
                "Either you or your attorneys can apply to register. If attorneys apply, you are told and can object.",
                f"The fee is £{LPA_FEE}, or £{LPA_FEE_BOTH} for both types of LPA. If you earn less than £12,000 a year you can apply for a reduction, and some benefits give an exemption: use form LPA120.",
                "Send LP3 to everyone in section 6 first, then send the signed original form and the fee to OPG (the address is on the form).",
            ],
            "sources": [GOV["lpa_register"], GOV["lpa_fee"]],
            "fields": [
                {"name": "applicant", "label": "Who will apply to register? (section 12)", "type": "select", "required": True, "options": ["Me (the donor)", "My attorneys"]},
                {"name": "correspondent", "label": "Who should receive the registered LPA? (section 13)", "type": "select", "required": True, "options": ["Me (the donor)", "An attorney", "Someone else"]},
                {"name": "correspondent_details", "label": "Their name and address", "type": "textarea", "required": True, "show_if": {"field": "correspondent", "in": ["An attorney", "Someone else"]}},
                {"name": "fee_reduction", "label": "Will you apply for a fee reduction or exemption (LPA120)? (section 14)", "type": "select", "required": True, "options": ["No, I will pay the full fee", "Yes, reduction (income under £12,000)", "Yes, exemption (certain benefits)", "Not sure"]},
                {"name": "repeat_application", "label": "Is this a repeat application within 3 months of a rejected one?", "type": "select", "options": YES_NO},
            ],
        },
        {
            "id": "documents", "title": "Your documents", "video": "lpa_documents", "uploads": ["Existing LPA", "Enduring power of attorney (EPA)", "Other"],
            "guidance": [
                "If you already have an LPA or an enduring power of attorney, upload it. We use it to suggest details and to check that nobody named in it is acting as your certificate provider.",
                "LPAs made on older forms (LPA114 or LPA117 before 1 January 2016, LP PA or LP PW before 1 April 2011) can still be registered with form LP2. Otherwise a new LPA is needed.",
            ],
            "sources": [GOV["lpa_register"]],
            "fields": [],
        },
    ]
    return {
        "id": kind,
        "form": form,
        "title": "Lasting power of attorney: " + short,
        "short_title": "LPA: " + short,
        "summary": f"Prepare an LPA for England and Wales that follows the official {form} form section by section. A solicitor checks it before you sign and register.",
        "review_video": "lpa_review",
        "steps": steps,
        "next_steps": [
            "A solicitor reviews your answers and contacts you with any questions.",
            f"Copy each answer into the matching section of the official {form} form (or the GOV.UK online service). Your pack lists them section by section.",
            "Sign in this order: you sign sections 5 and 9 with a witness; then the certificate provider signs section 10; then each attorney and replacement signs section 11 with a witness; the applicant signs section 15 last. Attorneys cannot witness your signature but can witness each other's.",
            "Send form LP3 to each person to notify. They have 3 weeks to raise concerns.",
            f"Send the signed original form and the £{LPA_FEE} fee (or form LPA120) to the Office of the Public Guardian. Registration takes 8 to 10 weeks if there are no mistakes. If OPG finds a correctable mistake you can usually re-apply within 3 months for £{LPA_RETRY_FEE}.",
        ],
    }


LPA_PROPERTY = lpa_service("lpa_property")
LPA_HEALTH = lpa_service("lpa_health")
