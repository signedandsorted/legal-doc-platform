"""Shared question building blocks and official GOV.UK sources.

Field types: text, textarea, email, date, number, select, checkbox, list, group.
Optional keys: required, hint, options, min, max, fields (list/group), show_if.
show_if = {"field": <sibling field name>, "in": [values]} hides the field (and skips its
required check) unless the sibling's answer is one of the values. Checkbox answers are true/false.
"""


from datetime import datetime, timezone

def src(title: str, url: str) -> dict:
    return {"title": title, "url": url, "checked": datetime.now(timezone.utc).date().isoformat()}


GOV = {
    "make_will": src("GOV.UK: Making a will", "https://www.gov.uk/make-will"),
    "will_legal": src("GOV.UK: Make sure your will is legal", "https://www.gov.uk/make-will/make-sure-your-will-is-legal"),
    "will_update": src("GOV.UK: Updating your will", "https://www.gov.uk/make-will/updating-your-will"),
    "iht": src("GOV.UK: How Inheritance Tax works", "https://www.gov.uk/inheritance-tax"),
    "lpa": src("GOV.UK: Make, register or end a lasting power of attorney", "https://www.gov.uk/power-of-attorney"),
    "lpa_choose": src("GOV.UK: Choose your attorney", "https://www.gov.uk/power-of-attorney/choose"),
    "lpa_make": src("GOV.UK: Make a lasting power of attorney", "https://www.gov.uk/power-of-attorney/make-lasting-power"),
    "lpa_register": src("GOV.UK: Register a lasting power of attorney", "https://www.gov.uk/power-of-attorney/register"),
    "lpa_forms": src("GOV.UK: LPA forms (LP1F, LP1H, LP3, LPC continuation sheets, LPA120)", "https://www.gov.uk/government/publications/lasting-power-of-attorney-forms"),
    "lpa_fee": src("GOV.UK: Apply for a reduced LPA fee (LPA120)", "https://www.gov.uk/government/publications/applying-for-a-reduced-fee-for-your-power-of-attorney"),
    "probate": src("GOV.UK: Applying for probate", "https://www.gov.uk/applying-for-probate"),
    "probate_will": src("GOV.UK: Applying for probate if there's a will", "https://www.gov.uk/applying-for-probate/if-theres-a-will"),
    "probate_no_will": src("GOV.UK: Applying for probate if there's not a will", "https://www.gov.uk/applying-for-probate/if-theres-not-a-will"),
    "probate_before": src("GOV.UK: Before you apply for probate (the 5 estate values)", "https://www.gov.uk/applying-for-probate/before-you-apply"),
    "probate_fees": src("GOV.UK: Probate fees", "https://www.gov.uk/applying-for-probate/fees"),
    "probate_apply": src("GOV.UK: Apply for probate online or by post", "https://www.gov.uk/applying-for-probate/apply-for-probate"),
    "probate_forms": src("GOV.UK: Probate forms and guidance (PA forms)", "https://www.gov.uk/government/collections/probate-forms"),
    "pa1p": src("GOV.UK: Form PA1P (by post, there is a will)", "https://www.gov.uk/government/publications/form-pa1p-apply-for-probate-the-deceased-had-a-will"),
    "pa1a": src("GOV.UK: Form PA1A (by post, there is no will)", "https://www.gov.uk/government/publications/apply-for-probate-by-post-if-there-is-not-a-will"),
    "iht_value": src("GOV.UK: Value the estate for Inheritance Tax", "https://www.gov.uk/valuing-estate-of-someone-who-died"),
    "iht_estate_type": src("GOV.UK: Check if you need to send full details (excepted estates)", "https://www.gov.uk/valuing-estate-of-someone-who-died/check-type-of-estate"),
    "iht400": src("GOV.UK: Inheritance Tax account (IHT400)", "https://www.gov.uk/government/publications/inheritance-tax-inheritance-tax-account-iht400"),
    "iht402": src("GOV.UK: Claim to transfer unused nil rate band (IHT402)", "https://www.gov.uk/government/publications/inheritance-tax-claim-to-transfer-unused-nil-rate-band-iht402"),
    "iht435": src("GOV.UK: Claim the residence nil rate band (IHT435)", "https://www.gov.uk/guidance/claim-the-residence-nil-rate-band"),
    "iht436": src("GOV.UK: Claim transferable residence nil rate band (IHT436)", "https://www.gov.uk/government/publications/claim-to-transfer-any-unused-residence-nil-rate-band-iht436"),
    "ex160": src("GOV.UK: Help with court fees (EX160)", "https://www.gov.uk/government/publications/apply-for-help-with-court-and-tribunal-fees"),
    "pa11": src("GOV.UK: Form PA11 (appoint someone to apply, will)", "https://www.gov.uk/government/publications/form-pa11-apply-for-power-of-attorney-will"),
    "pa14": src("GOV.UK: Form PA14 (medical certificate)", "https://www.gov.uk/government/publications/form-pa14-medical-certificate-probate"),
    "lp12": src("GOV.UK: LP12 Make and register your lasting power of attorney: a guide (web version, updated 3 November 2026)", "https://www.gov.uk/government/publications/lasting-power-of-attorney-forms/lp12-make-and-register-your-lasting-power-of-attorney-a-guide-web-version"),
    "lpa_errors": src("GOV.UK: Avoiding errors when completing a lasting power of attorney form", "https://www.gov.uk/government/publications/avoiding-errors-when-completing-a-lasting-power-of-attorney-form/avoiding-errors-when-completing-a-lasting-power-of-attorney-form"),
    "poa_act": src("Powers of Attorney Act 1971, section 10", "https://www.legislation.gov.uk/ukpga/1971/27/section/10"),
    "poa_sch1": src("Powers of Attorney Act 1971, Schedule 1 (form of general power of attorney)", "https://www.legislation.gov.uk/ukpga/1971/27/schedule/1"),
    "pg9": src("HM Land Registry Practice Guide 9: powers of attorney and registered land", "https://www.gov.uk/government/publications/powers-of-attorney-and-registered-land/practice-guide-9-powers-of-attorney-and-registered-land"),
    "lpmpa": src("Law of Property (Miscellaneous Provisions) Act 1989, section 1 (deeds)", "https://www.legislation.gov.uk/ukpga/1989/34/section/1"),
    "business_relief": src("GOV.UK: Business Relief for Inheritance Tax", "https://www.gov.uk/business-relief-inheritance-tax"),
    "business_relief_qualifies": src("GOV.UK: What qualifies for Business Relief", "https://www.gov.uk/business-relief-inheritance-tax/what-qualifies-for-business-relief"),
    "law_soc_dfm": src("The Law Society: A good investment (May 2022), quoting the former OPG LP12 standard clause on discretionary investment management", "https://communities.lawsociety.org.uk/may-2022/a-good-investment/6002319.article"),
}

YES_NO = ["No", "Yes"]

PERSON = [
    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
    {"name": "address", "label": "Address", "type": "textarea", "required": True},
    {"name": "relationship", "label": "Relationship to you", "type": "text"},
]

ATTORNEY = [
    {"name": "full_name", "label": "Full name", "type": "text", "required": True},
    {"name": "date_of_birth", "label": "Date of birth", "type": "date", "required": True, "hint": "Attorneys must be 18 or over when you sign."},
    {"name": "address", "label": "Address", "type": "textarea", "required": True},
    {"name": "email", "label": "Email (optional)", "type": "email"},
    {"name": "relationship", "label": "Relationship to you", "type": "text"},
]


def optional(fields: list) -> list:
    return [dict(f, required=False) for f in fields]
