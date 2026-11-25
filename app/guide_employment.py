"""Employment settlement agreement. DRAFT WORDING: needs lawyer review."""
from .fields import GOV, PERSON, YES_NO

EMPLOYMENT_SETTLEMENT = {
    "id": "employment_settlement",
    "title": "Employment settlement agreement",
    "short_title": "Settlement agreement", "hidden": True,
    "summary": "A settlement agreement to end employment on agreed terms. A solicitor checks it before you sign.",
    "category": "Agreements",
    "review_video": "employment_review",
    "steps": [
        {
            "id": "intro", "title": "Before you start", "video": "employment_intro",
            "guidance": [
                "A settlement agreement ends employment on agreed terms and usually waives claims. The employee must receive independent legal advice.",
            ],
            "fields": [],
        },
        {
            "id": "parties", "title": "Parties and employment", "video": "employment_parties",
            "guidance": ["Enter the employer and employee details."],
            "fields": [
                {"name": "employer_name", "label": "Employer name", "type": "text", "required": True},
                {"name": "employee_name", "label": "Employee full name", "type": "text", "required": True},
                {"name": "job_title", "label": "Job title", "type": "text"},
                {"name": "termination_date", "label": "Proposed termination date", "type": "date"},
            ],
        },
        {
            "id": "terms", "title": "Settlement terms", "video": "employment_terms",
            "guidance": ["Describe the payments, notice, and any other terms."],
            "fields": [
                {"name": "payment", "label": "Settlement payment amount and when it is paid", "type": "textarea", "required": True},
                {"name": "other_terms", "label": "Other terms (reference, confidentiality, etc.)", "type": "textarea"},
            ],
        },
        {
            "id": "review", "title": "Review", "video": "employment_review",
            "guidance": ["A solicitor will review and the employee must take independent advice."],
            "fields": [],
        },
    ],
}
