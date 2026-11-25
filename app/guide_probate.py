"""Probate helper for England and Wales, following GOV.UK 'Applying for probate' and
'Value the estate for Inheritance Tax'. DRAFT: needs lawyer review before it goes live."""
from .fields import GOV, YES_NO

PROBATE_FEE = 526          # GOV.UK probate fees page, checked 17 Nov 2026 (estates over £5,000)
PROBATE_FEE_FREE_UNDER = 5000
EXTRA_COPY_FEE = 2
NRB = 325_000               # GOV.UK Inheritance Tax overview, checked 17 Nov 2026
RNRB = 175_000              # brings the threshold to £500,000 when a home goes to direct descendants
RNRB_TAPER_FROM = 2_000_000
EXCEPTED_TNRB_LIMIT = 650_000
EXCEPTED_EXEMPT_LIMIT = 3_000_000
EXCEPTED_FOREIGN_DOM_LIMIT = 150_000

ASSET_TYPES = ["Home, land or other property", "Bank, building society or ISA", "Stocks, shares or investments", "Pension or life insurance paid to the estate",
               "Personal possessions or vehicles", "Business or farm", "Money owed to them", "Other"]
OWNERSHIP = ["Owned on their own", "Joint tenants (passes automatically to the other owner)", "Tenants in common (enter their share only)"]
APPLICANT_ROLES = ["Executor named in the will or a codicil", "Husband, wife or civil partner", "Child aged 18 or over", "Other relative",
                   "Unmarried partner", "Someone else (for example an attorney or a beneficiary)"]

FULL_DETAIL_TRIGGERS = [
    ("gifts_with_reservation", "They gave something away but kept benefiting from it (for example gave the house but kept living there rent-free)"),
    ("trust_interests", "They put gifts into a trust, benefited from a trust worth over £250,000, or had more than one trust"),
    ("foreign_assets_over_100k", "They had assets abroad worth more than £100,000"),
    ("pension_changes", "They increased a personal pension lump sum while terminally ill or in poor health"),
    ("annuity_and_life_policy", "They had a life policy paying someone other than their spouse or civil partner, and also an annuity"),
    ("pre_owned_election", "They elected for property they gave away to count as part of their estate (pre-owned asset charge)"),
    ("deemed_domiciled", "They lived outside the UK but were 'deemed domiciled' in the UK"),
]

PROBATE = {
    "id": "probate",
    "title": "Probate helper",
    "short_title": "Probate",
    "summary": "A plain-English walk-through the family can start, then the firm continues on the same figures: what they owned, where else to look, the tax papers, a simple estate account, and what happens after the grant. England and Wales.",
    "review_video": "probate_review",
    "steps": [
        {
            "id": "intro", "title": "Before you start", "video": "probate_intro",
            "guidance": [
                "We are sorry for your loss. This helper follows the GOV.UK steps: check probate is needed, check who can apply, value the estate for Inheritance Tax, then apply online or by post.",
                "Probate is the legal right to deal with someone's property, money and possessions. You may not need it if they only had savings, or owned everything jointly as joint tenants. Each bank has its own limit, so ask them.",
                "Do not make financial plans or put property on the market until you have probate.",
            ],
            "sources": [GOV["probate"], GOV["probate_before"]],
            "fields": [],
        },
        {
            "id": "deceased", "title": "The person who died", "video": "probate_deceased",
            "guidance": [
                "You need the death certificate. If the death happened outside England or Wales, or you have an interim certificate from the coroner, you send a copy with the application.",
                "Where they lived permanently and their marital status affect who can apply, the tax rules, and whether you can apply online.",
            ],
            "sources": [GOV["probate_apply"], GOV["probate_before"]],
            "fields": [
                {"name": "full_name", "label": "Their full name", "type": "text", "required": True},
                {"name": "other_names", "label": "Other names they used, for example on bank accounts (optional)", "type": "text"},
                {"name": "date_of_birth", "label": "Date of birth", "type": "date"},
                {"name": "date_of_death", "label": "Date of death", "type": "date", "required": True},
                {"name": "address", "label": "Their last permanent address", "type": "textarea", "required": True},
                {"name": "domicile", "label": "Did they live permanently in England or Wales?", "type": "select", "required": True, "options": ["Yes", "No, elsewhere in the UK", "No, outside the UK"]},
                {"name": "marital_status", "label": "Marital status when they died", "type": "select", "required": True, "options": ["Married or in a civil partnership", "Widowed or a surviving civil partner", "Divorced or civil partnership dissolved", "Separated", "Never married"]},
                {"name": "death_certificate", "label": "Which death certificate do you have?", "type": "select", "required": True, "options": ["UK death certificate", "Interim certificate from the coroner", "Certificate from outside England or Wales", "Not yet"]},
            ],
        },
        {
            "id": "will", "title": "The will and who is applying", "video": "probate_will",
            "guidance": [
                "If there is a will, the executors named in it (or in a codicil) apply. You must send the original will; a photocopy is not accepted. If it is lost you may be able to use form PA13.",
                "Up to 4 people can apply. Executors who do not want to apply can hold 'power reserved', give up the right with form PA15, or appoint someone with form PA11.",
                "If there is no will, the closest living relative applies: the husband, wife or civil partner (even if separated), then children aged 18 or over. An unmarried partner cannot apply.",
            ],
            "sources": [GOV["probate_will"], GOV["probate_no_will"], GOV["probate_forms"]],
            "fields": [
                {"name": "has_will", "label": "Is there a will?", "type": "select", "required": True, "options": ["Yes, I have the original", "Yes, but the original is lost", "No", "Not sure"]},
                {"name": "codicils", "label": "Are there any codicils (updates to the will)?", "type": "select", "options": YES_NO + ["Not sure"], "show_if": {"field": "has_will", "in": ["Yes, I have the original", "Yes, but the original is lost"]}},
                {"name": "applicant_role", "label": "You are applying as", "type": "select", "required": True, "options": APPLICANT_ROLES},
                {"name": "applicant", "label": "You (the lead applicant)", "type": "group", "fields": [
                    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
                    {"name": "address", "label": "Address", "type": "textarea", "required": True},
                    {"name": "email", "label": "Email", "type": "email", "required": True},
                    {"name": "phone", "label": "Mobile phone (optional)", "type": "text"},
                ]},
                {"name": "applicants", "label": "How many people are applying, including you?", "type": "select", "required": True, "options": ["1", "2", "3", "4", "More than 4"]},
                {"name": "other_executors", "label": "Executors named in the will who are not applying", "type": "select", "options": ["None", "Holding power reserved", "Giving up the right to apply (renouncing)", "Want to appoint someone to apply for them", "Have died", "Cannot apply because of a mental health condition or impairment"], "show_if": {"field": "has_will", "in": ["Yes, I have the original", "Yes, but the original is lost"]}},
                {"name": "surviving_spouse_applying", "label": "Is a surviving husband, wife or civil partner applying or giving up their right?", "type": "select", "options": ["They are applying", "They are giving up their right (form PA16)", "There is no surviving spouse or civil partner"], "show_if": {"field": "has_will", "in": ["No"]}},
                {"name": "help_with_fees", "label": "Are you on a low income or certain benefits (help with fees)?", "type": "select", "options": YES_NO + ["Not sure"]},
            ],
        },
        {
            "id": "estate", "title": "What they owned and owed", "video": "probate_estate",
            "guidance": [
                "List what they owned and owed on the date they died. Ask each bank or organisation for the date-of-death value; for possessions, use what they would sell for.",
                "For jointly owned things, enter only their share and say how it was owned. Joint tenants' assets pass automatically to the other owner and are left out of the probate value.",
                "We use these to work out the 5 values the probate application asks for.",
            ],
            "sources": [GOV["iht_value"], GOV["probate_before"]],
            "fields": [
                {"name": "assets", "label": "Assets", "type": "list", "min": 0, "max": 40, "fields": [
                    {"name": "description", "label": "Description", "type": "text", "required": True},
                    {"name": "category", "label": "Type", "type": "select", "options": ASSET_TYPES},
                    {"name": "value", "label": "Their share of the value (£)", "type": "number", "required": True},
                    {"name": "ownership", "label": "How it was owned", "type": "select", "options": OWNERSHIP},
                    {"name": "abroad", "label": "Is it outside the UK?", "type": "select", "options": YES_NO},
                ]},
                {"name": "debts", "label": "Debts (mortgages, loans, cards, bills)", "type": "list", "min": 0, "max": 40, "fields": [
                    {"name": "description", "label": "Description", "type": "text", "required": True},
                    {"name": "value", "label": "Amount (£)", "type": "number", "required": True},
                    {"name": "joint", "label": "Owed jointly with someone else?", "type": "select", "options": YES_NO},
                ]},
                {"name": "funeral_costs", "label": "Funeral costs (£)", "type": "number"},
            ],
        },
        # Companies House check step added for probate estate wiring
        {
            "id": "companies_house", "title": "Check Companies House", "video": "probate_estate",
            "guidance": [
                "Search the Companies House officer register for the deceased to confirm any directorships or appointments. This helps identify assets or liabilities linked to companies.",
                "If the API key is not configured, a message will appear indicating the feature is not available.",
                "Tick the boxes for any officers that match the deceased; these will be added to the estate asset checklist.",
                "This helper prepares a pack for the family. It does not file or submit anything to Companies House or any government service.",
            ],
            "sources": [],
            "fields": [
                {"name": "officers", "label": "Companies House officers", "type": "list", "min": 0, "max": 20, "fields": [
                    {"name": "name", "label": "Officer name", "type": "text", "required": True},
                    {"name": "dob_month_year", "label": "Date of birth (month/year)", "type": "text"},
                    {"name": "appointments", "label": "Appointments (company, role)", "type": "textarea"},
                    {"name": "match", "label": "This is the deceased", "type": "checkbox"},
                ]},
            ],
        },
        {
            "id": "tax", "title": "Inheritance Tax", "video": "probate_tax",
            "guidance": [
                f"There is normally no Inheritance Tax if the estate is below the £{NRB:,} threshold, or everything above it goes to a spouse, civil partner, charity or community amateur sports club.",
                "Leaving a home to children or grandchildren can raise the threshold to £500,000, and unused threshold from a spouse or civil partner who died first can be added.",
                "Most estates are 'excepted estates': no full details go to HMRC. Some things mean you must send form IHT400 even if no tax is due. Tax is due by the end of the sixth month after the death.",
            ],
            "sources": [GOV["iht"], GOV["iht_estate_type"], GOV["iht400"]],
            "fields": [
                {"name": "to_spouse", "label": "Value left to a husband, wife or civil partner living in the UK (£)", "type": "number"},
                {"name": "to_charity", "label": "Value left to UK charities or community amateur sports clubs (£)", "type": "number"},
                {"name": "home_to_descendants", "label": "Does their home (or share of it) go to children, grandchildren, step or foster children?", "type": "select", "options": YES_NO},
                {"name": "home_value_to_descendants", "label": "Value of the home passing to them (£)", "type": "number", "required": True, "show_if": {"field": "home_to_descendants", "in": ["Yes"]}},
                {"name": "earlier_spouse_died", "label": "Did they outlive a husband, wife or civil partner?", "type": "select", "options": YES_NO},
                {"name": "unused_nrb_percent", "label": "Percentage of that person's threshold that was unused (%)", "type": "number", "hint": "Usually 100 if everything went to the person who has now died.", "show_if": {"field": "earlier_spouse_died", "in": ["Yes"]}},
                {"name": "gifts_7_years", "label": "Total gifts they made in the 7 years before they died (£)", "type": "number", "hint": "Leave out small gifts covered by exemptions, such as the £3,000 annual exemption."},
            ] + [{"name": k, "label": label, "type": "checkbox"} for k, label in FULL_DETAIL_TRIGGERS],
        },
        {
            "id": "documents", "title": "Your documents", "video": "probate_documents", "uploads": ["Will", "Codicil", "Death certificate", "Bank or valuation letter", "Other"],
            "guidance": [
                "Upload copies of the will, codicils, the death certificate, bank letters and valuations. Photos and scans are fine.",
                "We read text from PDFs and Word files, and we read photos and scans. When the papers are uploaded, use Fill in what these papers show. It writes the names, dates and amounts it can read, and leaves anything you have already typed. A blurry photo may still need to be typed. Check every step. Nothing is filed from here.",
            ],
            "sources": [GOV["probate_before"]],
            "fields": [],
        },
        {
            "id": "discovery", "title": "Where else to look", "video": "probate_estate",
            "guidance": [
                "People often miss an account. Work through this list before you decide the estate is complete.",
                "My Lost Account is free and searches banks, building societies and NS&I: https://www.mylostaccount.org.uk/",
                "The Pension Tracing Service finds workplace and personal pensions: https://www.gov.uk/find-pension-contact-details",
                "Search the Land Registry if there may be a house or land: https://www.gov.uk/search-property-information-land-registry",
                "Tell Us Once can notify government departments: https://www.gov.uk/tell-us-once",
                "Also ask NS&I about Premium Bonds, the last employer, any insurer, and look at email for PayPal or other online balances. This is not a credit-file search. A firm that buys those still has to pay a data company. What you find here is added on the estate step and flows into the account.",
            ],
            "sources": [GOV["iht_value"]],
            "fields": [
                {"name": "looked_banks", "label": "We have asked the banks, or started a My Lost Account search", "type": "checkbox"},
                {"name": "looked_pensions", "label": "We have looked for pensions", "type": "checkbox"},
                {"name": "looked_property", "label": "We have checked for property", "type": "checkbox"},
                {"name": "looked_rest", "label": "We have asked about Premium Bonds, the employer, insurance and online balances", "type": "checkbox"},
            ],
        },
        {
            "id": "bona_vacantia", "title": "Unclaimed estates list", "video": "probate_estate", "tool": "bona_vacantia",
            "guidance": [
                "If nobody claimed the estate, it may have been referred to the Crown (the Bona Vacantia Division). GOV.UK publishes a list of those estates that are not yet claimed.",
                "Search by surname, and add a first name to narrow it down. Each match shows the BV reference, the date and place of death. We download the list from GOV.UK at most once a day.",
                "If you find the person, follow the GOV.UK claim guidance and quote the BV reference. You make the claim yourself. This helper does not file or submit anything to the Bona Vacantia Division.",
            ],
            "sources": [GOV["bona_vacantia_list"], GOV["bona_vacantia_claim"]],
            "fields": [
                {"name": "result", "label": "What did the search show?", "type": "select", "options": ["Not checked yet", "No match on the list", "Possible match found"]},
                {"name": "bv_reference", "label": "BV reference of the match", "type": "text", "show_if": {"field": "result", "in": ["Possible match found"]}},
                {"name": "checked_on", "label": "Date you checked", "type": "date"},
                {"name": "note", "label": "Notes (optional)", "type": "textarea"},
            ],
        },
        {
            "id": "account", "title": "What is left, and what you do next", "video": "probate_estate",
            "guidance": [
                "You do not type the money again. This step turns the values you already entered into a simple estate account.",
                "The account is what the grant covers: things in their name, minus debts and the funeral. A joint bank account or a house owned as joint tenants goes straight to the other owner. It is not in this account, and you do not collect it.",
                "The order is always the same. Get the papers. Ask each bank for the value on the day they died. If the plan says so, post the tax form and wait for a code. Apply for the grant. When it arrives, collect the money and pay the bills. Share what is left only after that, and not in full until at least 6 months after the grant.",
                "You can file the grant yourself, or ask the firm to file it for you. This website cannot sign in to HMCTS. If you ask the firm, a solicitor files it in the firm's MyHMCTS account, or by post where the online service will not take it. That happens only after the firm accepts the matter.",
            ],
            "sources": [GOV["iht_value"], GOV["probate"]],
            "fields": [
                {"name": "who_files", "label": "Who should file the grant?", "type": "select", "required": True, "options": ["I will file it myself", "I want the firm to file it for me"]},
                {"name": "people", "label": "People to tell about their share (optional)", "type": "list", "min": 0, "max": 8, "fields": [
                    {"name": "full_name", "label": "Name", "type": "text", "required": True},
                    {"name": "relationship", "label": "Who they were to the person who died", "type": "text"},
                ]},
            ],
        },
    ],
    "next_steps": [
        "Read the estate account in your plan. It uses the values you entered. A solicitor checks it before anyone is paid.",
        "If the plan says full details are needed, print form IHT400, sign it, and post it to HMRC. Wait for their code. We cannot send the form.",
        "Apply for the grant on GOV.UK if the plan says you can, or by post on the form it names. Send the original will. We cannot send the application.",
        "When the grant arrives, collect each account and pay the debts and the funeral. Keep a note of money in and money out.",
        "Place a notice in The London Gazette under section 27 of the Trustee Act 1925, and in a local newspaper if there is land. Give people at least two months to make a claim. Wait at least 6 months from the grant as well before paying everyone in full.",
        "Share what is left as the will says, or as the law says if there is no will. The names you listed are people to keep informed. They are not a decision about who inherits.",
    ],
}
