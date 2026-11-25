"""All services. Each service lives in its own module; see app/fields.py for the field schema."""
from .guide_lpa import LPA_HEALTH, LPA_PROPERTY
from .guide_poa import POA_ORDINARY
from .guide_probate import PROBATE
from .guide_will import WILL
from .guide_prenup import PRENUP
from .guide_postnup import POSTNUP
from .guide_employment import EMPLOYMENT_SETTLEMENT
from .guide_employment_ila import EMPLOYMENT_SETTLEMENT_ILA
from .guide_cohabitation import COHABITATION
from .guide_nuptial import NUPTIAL
from .guide_us import US_SERVICES

# Home page grouping. Order here is the order of the cards.
for _svc, _cat in (
    (WILL, "Wills"),
    (LPA_PROPERTY, "Lasting powers of attorney"),
    (LPA_HEALTH, "Lasting powers of attorney"),
    (POA_ORDINARY, "Ordinary and general powers of attorney"),
    (PROBATE, "Probate"),
    (PRENUP, "Agreements"),
    (POSTNUP, "Agreements"),
    (EMPLOYMENT_SETTLEMENT, "Agreements"),
    (EMPLOYMENT_SETTLEMENT_ILA, "Agreements"),
    (COHABITATION, "Agreements"),
):
    _svc.setdefault("category", _cat)

SERVICES = {s["id"]: s for s in (WILL, LPA_PROPERTY, LPA_HEALTH, POA_ORDINARY, PROBATE, PRENUP, POSTNUP, EMPLOYMENT_SETTLEMENT, EMPLOYMENT_SETTLEMENT_ILA, COHABITATION, NUPTIAL, *US_SERVICES)}
# Define a stand‑alone document upload descriptor (not added to SERVICES to keep API stable).
DOCUMENT_UPLOAD = {
    "id": "document_upload",
    "title": "Upload supporting documents",
    "short_title": "Upload",
    "summary": "Upload PDF, DOCX, JPG, PNG files up to 10\u202fMB that support your draft.",
    "steps": [
        {
            "id": "upload",
            "title": "Your documents",
            "guidance": ["Upload a PDF, Word document, or image up to 10\u202fMB."],
            "fields": [
                {
                    "name": "file",
                    "label": "Document file",
                    "type": "file",
                    "required": True,
                    "accept": ".pdf,.docx,.jpg,.jpeg,.png",
                }
            ],
        }
    ],
}
