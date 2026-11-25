"""Will for England and Wales. Clause options benchmarked against the public feature list of
Sure Will Writer (trusts, bespoke clauses, exclusions, digital assets, pets) and GOV.UK 'Making a will'.
DRAFT WORDING: needs lawyer review before it goes live."""
from .fields import GOV, PERSON, YES_NO, optional

GIFT_TYPES = ["An item", "A sum of money", "A property or my share of it", "A gift to charity", "My pet, with money for its care"]

WILL = {
    "id": "will",
    "title": "Make a will",
    "short_title": "Will",
    "summary": "A will for England and Wales with the clauses most online services leave out: trusts, guardians, digital assets, pets, charity gifts and more. You can make it yourself. A solicitor is optional.",
    "review_video": "will_review",
    "steps": [
        {
            "id": "intro", "title": "Before you start", "video": "will_intro",
            "guidance": [
                "A will says who deals with your estate (executors), who inherits it (beneficiaries) and who cares for your children under 18 (guardians).",
                "To be valid you must be 18 or over, make it voluntarily and of sound mind, and sign it in front of 2 adult witnesses who are both present and then sign it in front of you.",
                "Marriage or a civil partnership usually cancels an earlier will. Divorce does not cancel it, but your ex-partner is treated as having died.",
                "If you have an old will, upload it at the 'Your documents' step and we will suggest names from it. Your answers save as you go.",
            ],
            "sources": [GOV["make_will"], GOV["will_legal"], GOV["will_update"]],
            "fields": [],
        },
        {
            "id": "about_you", "title": "About you", "video": "will_about_you",
            "guidance": [
                "Use your full legal name as it appears on your passport or driving licence, and list any other names you hold assets under.",
                "Where you permanently live and anything you own abroad can change the advice you need. This service covers England and Wales.",
            ],
            "sources": [GOV["make_will"]],
            "fields": [
                {"name": "full_name", "label": "Your full name", "type": "text", "required": True},
                {"name": "other_names", "label": "Other names you have used (optional)", "type": "text"},
                {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True},
                {"name": "address", "label": "Your address", "type": "textarea", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "marital_status", "label": "Marital status", "type": "select", "required": True, "options": ["Single", "Married", "Civil partnership", "Separated", "Divorced", "Widowed", "Living with a partner"]},
                {"name": "domicile", "label": "Where is your permanent home?", "type": "select", "required": True, "options": ["England or Wales", "Elsewhere in the UK", "Outside the UK"]},
                {"name": "assets_abroad", "label": "Do you own property or money outside the UK?", "type": "select", "options": ["No", "Yes", "Yes, and I have a separate will there"]},
                {"name": "expecting_marriage", "label": "Are you planning to marry or form a civil partnership soon?", "type": "select", "options": YES_NO},
                {"name": "partner_name", "label": "Your future spouse or civil partner's full name", "type": "text", "required": True, "show_if": {"field": "expecting_marriage", "in": ["Yes"]}},
            ],
        },
        {
            "id": "family", "title": "Children and guardians", "video": "will_family",
            "guidance": [
                "List all your children, even if you are not leaving them anything. It helps your solicitor make the will robust.",
                "If you have children under 18 you can appoint guardians to look after them if no parent with parental responsibility survives you. Ask them first, and add a back-up.",
            ],
            "sources": [GOV["make_will"]],
            "fields": [
                {"name": "children", "label": "Your children (optional)", "type": "list", "min": 0, "max": 12, "fields": [
                    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
                    {"name": "date_of_birth", "label": "Date of birth", "type": "date"},
                    {"name": "stepchild", "label": "Stepchild?", "type": "select", "options": YES_NO},
                ]},
                {"name": "guardians", "label": "Guardians (optional)", "type": "list", "min": 0, "max": 2, "fields": PERSON},
                {"name": "replacement_guardian", "label": "Replacement guardian (optional)", "type": "group", "fields": optional(PERSON)},
                {"name": "guardian_wishes", "label": "Wishes for your guardians, for example schooling or religion (optional, goes in your letter of wishes)", "type": "textarea"},
            ],
        },
        {
            "id": "executors", "title": "Your executors", "video": "will_executors",
            "guidance": [
                "Executors deal with your estate after you die. Choose 1 to 4 adults you trust; they can also be beneficiaries. They also act as trustees of any trust in your will.",
                "Add a replacement in case someone cannot act. If a professional firm acts, the will needs a charging clause so they can be paid.",
                "You can also appoint a digital executor to deal with online accounts, photos and files. Never put passwords in your will.",
            ],
            "sources": [GOV["make_will"]],
            "fields": [
                {"name": "executors", "label": "Executors", "type": "list", "min": 1, "max": 4, "fields": PERSON},
                {"name": "replacement_executor", "label": "Replacement executor (optional)", "type": "group", "fields": optional(PERSON)},
                {"name": "professional_executor", "label": "Is any executor a professional (solicitor, accountant or firm)?", "type": "select", "options": YES_NO},
                {"name": "digital_executor", "label": "Digital executor (optional)", "type": "group", "fields": optional(PERSON[:2])},
            ],
        },
        {
            "id": "gifts", "title": "Gifts", "video": "will_gifts",
            "guidance": [
                "Gifts of particular items, money, property, charity gifts and pets are dealt with before the rest of your estate is shared out.",
                "Describe items clearly: 'my gold wedding ring' is better than 'my jewellery'. Say what happens if the person dies before you.",
                "Gifts to UK charities are free of Inheritance Tax, and leaving 10% or more of your net estate to charity can reduce the rate on the rest from 40% to 36%.",
            ],
            "sources": [GOV["iht"]],
            "fields": [
                {"name": "gifts", "label": "Gifts (optional)", "type": "list", "min": 0, "max": 25, "fields": [
                    {"name": "type", "label": "Type of gift", "type": "select", "required": True, "options": GIFT_TYPES},
                    {"name": "gift", "label": "What you are giving", "type": "text", "required": True},
                    {"name": "beneficiary", "label": "Who receives it (or the charity's name)", "type": "text", "required": True},
                    {"name": "charity_number", "label": "Registered charity number", "type": "text", "show_if": {"field": "type", "in": ["A gift to charity"]}},
                    {"name": "pet_money", "label": "Money for the pet's care (£)", "type": "number", "show_if": {"field": "type", "in": ["My pet, with money for its care"]}},
                    {"name": "if_they_die", "label": "If they die before you", "type": "select", "options": ["The gift goes into the rest of my estate", "Their children receive it"]},
                ]},
            ],
        },
        {
            "id": "residue", "title": "The rest of your estate", "video": "will_residue",
            "guidance": [
                "Your residuary estate is everything left after debts, funeral costs, expenses and gifts. For most people it is the largest part.",
                "Give each person a share; shares work in proportion, so 1 and 1 means half each. Young beneficiaries can inherit at 18, 21 or 25; until then your trustees can use their share for education and upkeep.",
                "Beneficiaries must survive you by 28 days to inherit, which avoids double tax and confusion if you die close together.",
            ],
            "sources": [GOV["make_will"]],
            "fields": [
                {"name": "residuary_beneficiaries", "label": "Residuary beneficiaries", "type": "list", "min": 1, "max": 12, "fields": [
                    {"name": "full_name", "label": "Full name (or charity name)", "type": "text", "required": True},
                    {"name": "relationship", "label": "Relationship to you", "type": "text"},
                    {"name": "share", "label": "Share", "type": "number", "required": True},
                ]},
                {"name": "inherit_age", "label": "Age at which beneficiaries inherit outright", "type": "select", "required": True, "options": ["18", "21", "25"]},
                {"name": "substitution", "label": "If a beneficiary dies before me", "type": "select", "required": True, "options": ["Their children take their share", "Their share goes to the other residuary beneficiaries"]},
                {"name": "ultimate_beneficiary", "label": "If none of them survive me, the estate goes to (optional)", "type": "text"},
            ],
        },
        {
            "id": "trusts", "title": "Trusts", "video": "will_trusts",
            "guidance": [
                "Trusts protect what you leave. A life interest trust lets a partner live in your home (or have the income from your estate) for life, then passes it to your children: useful in second marriages and for care-fee planning.",
                "A discretionary trust lets your trustees decide who benefits and when, guided by your letter of wishes. A vulnerable person's trust protects someone disabled or receiving means-tested benefits.",
                "If none of these apply, leave them at 'No'. A solicitor checks every trust before you sign.",
                "GOV.UK explains the main types of trust and how they are taxed. Some trusts set up by a will must be registered with HMRC's Trust Registration Service by the trustees after you die.",
            ],
            "sources": [GOV["iht"], GOV["trusts"], GOV["trust_types"], GOV["trust_register"]],
            "fields": [
                {"name": "life_interest", "label": "Do you want a life interest trust?", "type": "select", "options": ["No", "Yes, over my share of my home", "Yes, over my whole residuary estate"]},
                {"name": "life_tenant", "label": "Who benefits for life (usually your partner)?", "type": "text", "required": True, "show_if": {"field": "life_interest", "in": ["Yes, over my share of my home", "Yes, over my whole residuary estate"]}},
                {"name": "discretionary", "label": "Hold the residuary estate on a discretionary trust instead of fixed shares?", "type": "select", "options": YES_NO, "hint": "Your residuary beneficiaries and their families become the people the trustees can choose from."},
                {"name": "vulnerable_beneficiary", "label": "Name of a disabled or vulnerable beneficiary whose share should be held on a protective trust (optional)", "type": "text"},
            ],
        },
        {
            "id": "business", "title": "Your business", "video": "will_business",
            "guidance": [
                "If you own a business, a farm, agricultural land, or shares in a company, say so here so a solicitor can look at how those assets should pass and whether they should be kept separate from the rest of your estate.",
                "Some business assets may qualify for Inheritance Tax Business Relief (sometimes still called business property relief). GOV.UK currently says 100% relief can apply to a business or interest in a business, and to shares in an unlisted company, if the conditions are met, including usually a two-year period of ownership. For deaths on or after 6 April 2026, 100% relief is capped at £2.5 million of qualifying business or agricultural property; value above that can receive 50% relief. Other assets, such as some AIM shares or land used in a business, may only qualify for 50%. Relief is not available for businesses that mainly deal in securities, land or investments, among other exclusions.",
                "The rules are detailed and change. Do not rely on this summary. A solicitor should check whether relief applies and how a gift, a separate will or a trust would affect it. If there are co-owners, talk to them and check any partnership or shareholders' agreement before you decide who should inherit the business.",
                "If you also want someone to run or deal with the business during your lifetime if you cannot, consider a property and financial affairs LPA, and whether that should be a separate business LPA. This will is not an LPA.",
                "This is not legal advice. Any business wording in your draft will is a placeholder for a solicitor to write.",
            ],
            "sources": [GOV["business_relief"], GOV["business_relief_qualifies"], GOV["iht"]],
            "fields": [
                {"name": "owns_business", "label": "Do you own a business, a farm, agricultural land, or shares in a company?", "type": "select", "options": YES_NO},
                {"name": "business_type", "label": "What kind of business interest is it?", "type": "select", "required": True, "show_if": {"field": "owns_business", "in": ["Yes"]},
                 "options": ["Sole trader", "Partnership", "Shares in a limited company", "Farm or agricultural land", "More than one of these", "Not sure"]},
                {"name": "business_details", "label": "Describe the business, farm or shares and who should inherit them", "type": "textarea", "required": True, "show_if": {"field": "owns_business", "in": ["Yes"]}},
                {"name": "talked_to_co_owners", "label": "Have you talked to any co-owners, partners or fellow shareholders about what should happen?", "type": "select", "show_if": {"field": "owns_business", "in": ["Yes"]},
                 "options": ["Yes", "Not yet", "There are no co-owners", "Not sure"]},
                {"name": "has_agreement", "label": "Is there a partnership agreement, shareholders' agreement or similar that deals with death or incapacity?", "type": "select", "show_if": {"field": "owns_business", "in": ["Yes"]},
                 "options": ["Yes", "No", "Not sure"]},
                {"name": "separate_planning", "label": "Would you like a solicitor to consider a separate gift, will or trust for the business assets, including Inheritance Tax Business Relief?", "type": "select", "show_if": {"field": "owns_business", "in": ["Yes"]},
                 "options": YES_NO,
                 "hint": "A solicitor will advise whether this is needed. This app will not draft that wording itself."},
            ],
        },
        {
            "id": "safeguards", "title": "Claims, capacity and couples", "video": "will_review",
            "guidance": [
                "The Inheritance (Provision for Family and Dependants) Act 1975 lets some people ask a court for reasonable financial provision if a will, or the intestacy rules, do not provide it. That can include a husband, wife or civil partner, a former spouse who has not formed a new marriage or civil partnership, a child, someone treated as a child of the family, someone who was being maintained, and a partner who lived with the person as husband, wife or civil partner for the whole of the two years before the death. A claim is normally made within six months of the grant. A spouse's claim is not limited to maintenance. Most other claims are. Recording the reasons, or sending a summary, does not stop a claim and does not make the firm immune from one.",
                "The golden rule is practice, not a statute (Kenward v Adams). Where the person is elderly or seriously ill, or there is any other reason to doubt capacity, a doctor should examine them, apply the Banks v Goodfellow test, and make a written note. The will is not invalid only because this was not done (Hughes v Pritchard). The note is what a firm relies on if capacity is challenged. Do not delay the will so long that it is never signed. See the client alone. Take a full note of the assets, the family, and why someone is left out.",
                "The SRA's wills guidance was updated on 25 November 2019. Paragraph 3.3 is competence. Paragraph 3.5 is taking account of the client's circumstances. Paragraph 6.1 is an own-interest conflict: if the will leaves something of significant value to the drafter, their family, or an employee, the client should take independent advice first, and the drafter usually stops if they refuse. A parent leaving the estate equally to their children, including a solicitor child, can be an exception. Do not tell a client that appointing a solicitor as executor is essential. None of these steps is a warranty against a claim.",
                "Mirror wills are two separate wills in similar terms. The Society of Will Writers says each person can change or revoke their own, including after the other has died, unless they made a separate binding promise. Say that on the face of the will so it is not later called mutual. Mutual wills are different: the couple agree that neither will revoke. While both are alive either can still change their mind. After the first death, and once the survivor has taken the benefit, equity can enforce the promise by a constructive trust. A will still cannot be made irrevocable, and a later marriage can revoke it. Mutual wills are rarely what a couple wants. Do not call a pair of wills mutual unless a solicitor has advised both people.",
                "If an earlier will is uploaded, the draft flags gifts and appointments in it that this new will does not repeat, mutual-will wording, crossings-out, and planning that should not be copied or deleted without a decision. The machine reading is not the will. A solicitor reads the original. Do not cross it out: the Institute of Professional Willwriters says that can make it invalid, so make a new will or a codicil. Do not destroy the old original. A new will does not cancel it until the new one is signed and witnessed. File protection is the attendance note and the earlier papers, kept so the file can be explained years later. It does not stop a claim.",
            ],
            "sources": [GOV["will_legal"], GOV["act1975"], GOV["sra_wills"], GOV["sww_mirror"], GOV["ipw_changes"], GOV["file_retention"], GOV["wills_act"]],
            "fields": [
                {"name": "act_read", "label": "I understand a person left out, or left less than they expected, may be able to claim under the 1975 Act, and that this form does not stop that claim", "type": "checkbox", "required": True},
                {"name": "capacity", "label": "Is there any reason to ask a doctor about capacity?", "type": "select", "required": True, "options": ["No reason to doubt it", "Elderly or seriously ill", "Another reason to doubt it"]},
                {"name": "doctor", "label": "Has a doctor been asked to examine and make a written note?", "type": "select", "required": True, "options": ["Not needed", "Yes", "Not yet"]},
                {"name": "seen_alone", "label": "Were the instructions taken with the client alone, free of pressure?", "type": "select", "required": True, "options": ["Yes", "No, someone else was present or pressing", "Not sure"]},
                {"name": "drafter_benefits", "label": "Does the will writer, a solicitor, their family, or an employee receive a gift under this will?", "type": "select", "required": True, "options": ["No", "Yes"]},
                {"name": "independent_advice", "label": "Has the client taken independent advice on that gift?", "type": "select", "required": True, "show_if": {"field": "drafter_benefits", "in": ["Yes"]}, "options": ["Yes", "Not yet", "The client refuses"]},
                {"name": "couple", "label": "Is this one of a pair of wills?", "type": "select", "required": True, "options": ["No, one will only", "Mirror wills: each of us can change our own", "Mutual wills: the survivor should not be able to change", "Not sure"]},
                {"name": "couple_name", "label": "The other person's full name", "type": "text", "required": True, "show_if": {"field": "couple", "in": ["Mirror wills: each of us can change our own", "Mutual wills: the survivor should not be able to change"]}},
            ],
        },
        {
            "id": "extras", "title": "Extra wishes", "video": "will_extras",
            "guidance": [
                "These are optional but make life easier for your family. Say where your list of online accounts is kept; never write passwords in a will.",
                "You can cancel loans you have made to family, and say whether large lifetime gifts should count against someone's share.",
                "If you are leaving out someone who might expect to inherit (for example a child), explain why in a separate statement; it can help if a claim is made under the Inheritance (Provision for Family and Dependants) Act 1975. A solicitor will review it.",
            ],
            "sources": [GOV["make_will"]],
            "fields": [
                {"name": "digital_assets_location", "label": "Where is your list of online accounts and digital assets kept? (optional)", "type": "text"},
                {"name": "loans_forgiven", "label": "Loans to forgive on your death (who and roughly how much, optional)", "type": "textarea"},
                {"name": "lifetime_gifts", "label": "Should large gifts you made in your lifetime count against that person's share?", "type": "select", "options": ["No", "Yes"]},
                {"name": "exclude_person", "label": "Is there anyone you are deliberately leaving out who might expect to inherit?", "type": "select", "options": YES_NO},
                {"name": "exclusion_name", "label": "Their name", "type": "text", "required": True, "show_if": {"field": "exclude_person", "in": ["Yes"]}},
                {"name": "exclusion_reason", "label": "Your reasons (kept in a separate statement, not in the will)", "type": "textarea", "required": True, "show_if": {"field": "exclude_person", "in": ["Yes"]}},
                {"name": "funeral_wishes", "label": "Funeral wishes", "type": "select", "options": ["No preference", "Burial", "Cremation", "Natural or woodland burial"]},
                {"name": "funeral_notes", "label": "Anything else about your funeral (optional)", "type": "textarea"},
                {"name": "organ_donation", "label": "Organ donation", "type": "select", "options": ["No preference", "I wish to donate my organs and tissue", "I do not wish to donate"]},
                {"name": "letter_of_wishes", "label": "Letter of wishes to your executors and trustees (optional, not part of the will)", "type": "textarea"},
            ],
        },
        {
            "id": "documents", "title": "Your documents", "video": "will_documents", "uploads": ["Old will", "Codicil", "Other"],
            "guidance": [
                "If you have an old will, codicils or other papers, upload them. A photo or scan is fine; we read text from PDFs and Word files and suggest names you can add with one tap. That reading is not a review of the will. Do not cross out or write on the old will. Make a new will, or a codicil for a small change.",
                "Your new will revokes earlier wills once it is signed and witnessed. Do not destroy the old original until then. The firm keeps the original, or a copy if it is revoked, with the file.",
            ],
            "sources": [GOV["will_update"], GOV["ipw_changes"], GOV["will_storage"]],
            "fields": [],
        },
    ],
    "next_steps": [
        "You can finish this will yourself. It is valid only once you sign it in front of two adult witnesses who are both present. A witness must not be a beneficiary, or the husband, wife or civil partner of a beneficiary. A solicitor is optional.",
        "Sign the final will in front of 2 independent adult witnesses who are both present at the same time. They then sign in front of you.",
        "A witness must not be a beneficiary, or the husband, wife or civil partner of a beneficiary, or that person's gift can fail.",
        "Keep the signed original somewhere safe and tell your executors where it is. You can also store it with the Probate Service.",
        "Review your will after marriage, divorce, children, a house move or a big change in your finances. Marriage or civil partnership usually cancels it.",
    ],
}
