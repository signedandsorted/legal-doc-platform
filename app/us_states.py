"""United States signing rules used by the drafts. Not a statute book.

Two adult witnesses is the safe pattern in every state except Louisiana, which
does not use a common-law will, and Pennsylvania, where a will signed at the
end can be valid with no witnesses. A notary does not replace witnesses except
in a Louisiana notarial testament.
"""

STATES = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
)

COMMUNITY = {
    "Arizona", "California", "Idaho", "Louisiana", "Nevada", "New Mexico", "Texas", "Washington", "Wisconsin",
}

SOURCES = [
    {"title": "IRS: estate tax", "url": "https://www.irs.gov/businesses/small-businesses-self-employed/estate-tax"},
    {"title": "Cornell Legal Information Institute: wills", "url": "https://www.law.cornell.edu/wex/wills"},
]


def minimum_age(state: str) -> int:
    return 16 if state == "Louisiana" else 18


def execution(state: str) -> list[str]:
    if state == "Louisiana":
        return [
            "Louisiana does not use the common-law will. A testament is either notarial, signed before a notary and two witnesses in the form the Civil Code requires, or olographic, written entirely in your handwriting, dated and signed.",
            "This printout is a record of what you asked for. It is not a Louisiana notarial testament. Do not sign it as though it were one. A Louisiana notary has to prepare that form.",
        ]
    if state == "Pennsylvania":
        return [
            "In Pennsylvania a will can be valid if you sign it at the end, even with no witnesses. Two adult witnesses are still the safer way to prove it.",
            "A notary is not a witness. A notarised self-proving affidavit lets the witnesses swear now, so the court may not need them later.",
        ]
    return [
        f"In {state}, sign in front of two adult witnesses. They watch you sign, or you acknowledge the signature to them, and they then sign. Do it together, not on different days.",
        "A witness should not be a person who receives a gift under this document, or that person's spouse.",
        "A notary does not take the place of the two witnesses. After the witnesses sign, a notarised self-proving affidavit is optional and useful.",
    ]


def property_note(state: str, married: bool) -> str | None:
    if state not in COMMUNITY or not married:
        return None
    return (
        f"{state} is a community-property state. A spouse may already own a half share of property acquired during the marriage. "
        "This document can give what you own: your separate property and your half of the community property. It does not decide which asset is which."
    )
