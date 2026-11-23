"""Employment settlement Independent Legal Advice (ILA) intake and booking.
Draft wording and flow; needs lawyer review before release.
"""

from .fields import GOV, PERSON, YES_NO

EMPLOYMENT_SETTLEMENT_ILA = {
    "id": "employment_settlement_ila",
    "title": "Employment settlement – Independent Legal Advice",
    "short_title": "Employment settlement ILA",
    "summary": "Intake and booking for independent legal advice on an employment settlement agreement (no automated certificate).",
    "category": "Agreements",
    "review_video": "employment_ila_review",
    "steps": [
        {
            "id": "upload",
            "title": "Upload settlement agreement",
            "video": "employment_ila_upload",
            "guidance": [
                "Upload the draft settlement agreement provided by the employer. The file is stored for the solicitor to review."
            ],
            "fields": [],
        },
        {
            "id": "questionnaire",
            "title": "Details questionnaire",
            "video": "employment_ila_questionnaire",
            "guidance": [
                "Provide details of the parties, the terms being settled and any other relevant information."
            ],
            "fields": [
                {"name": "employer_name", "label": "Employer name", "type": "text", "required": True},
                {"name": "employee_name", "label": "Employee full name", "type": "text", "required": True},
                {"name": "job_title", "label": "Job title", "type": "text"},
                {"name": "termination_date", "label": "Proposed termination date", "type": "date"},
                {"name": "claims_settled", "label": "Claims the agreement purports to settle", "type": "textarea"},
                {"name": "payment_details", "label": "Settlement payment details", "type": "textarea"},
                {"name": "legal_fee_paid_by_employer", "label": "Will the employer pay the employee's legal fee?", "type": "select", "options": YES_NO},
                {"name": "deadline", "label": "Any deadline for the advice", "type": "date"},
            ],
        },
        {
            "id": "quote",
            "title": "Fixed‑fee quote",
            "video": "employment_ila_quote",
            "guidance": [
                "A solicitor will provide a fixed‑fee quote for the advice. Payment integration is currently disabled; the quote is for information only."
            ],
            "fields": [],
        },
        {
            "id": "conflict",
            "title": "Conflict check",
            "video": "employment_ila_conflict",
            "guidance": [
                "The system checks for potential conflicts of interest with existing clients or matters."
            ],
            "fields": [],
        },
        {
            "id": "booking",
            "title": "Book advice session",
            "video": "employment_ila_booking",
            "guidance": [
                "Schedule a meeting with a qualified solicitor to give the independent legal advice."
            ],
            "fields": [],
        },
        {
            "id": "certificate",
            "title": "Adviser certificate (pending)",
            "video": "employment_ila_certificate",
            "guidance": [
                "After advice is given, the solicitor will sign the adviser certificate. The app tracks the status but does not generate a signed document automatically."
            ],
            "fields": [
                {"name": "certificate_signed", "label": "Certificate signed by adviser", "type": "select", "options": ["No", "Yes"], "required": True, "default": "No"},
            ],
        },
    ],
}
