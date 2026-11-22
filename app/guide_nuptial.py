"""Guide definition for nuptial agreements."""

from .fields import YES_NO, optional

NUPTIAL = {
    "id": "nuptial",
    "title": "Create a nuptial agreement",
    "short_title": "Nuptial agreement",
    "summary": "Guided creation of a prenuptial or postnuptial agreement with asset disclosure and legal advice notes.",
    "review_video": "nuptial_review",
    "steps": [
        {
            "id": "intro",
            "title": "About nuptial agreements",
            "video": "nuptial_intro",
            "guidance": [
                "A nuptial agreement can be made before (prenuptial) or after (postnuptial) marriage. It outlines asset division and other arrangements.",
                "These agreements are not automatically binding; a solicitor must review them and they must meet fairness principles (Radmacher v Granatino).",
            ],
            "sources": [],
            "fields": [
                {"name": "type", "label": "Agreement type", "type": "select", "required": True, "options": ["prenup", "postnup"]},
                {"name": "assets", "label": "Asset disclosure (brief description)", "type": "textarea", "required": True},
                {"name": "legal_advice", "label": "Independent legal advice obtained?", "type": "select", "options": YES_NO, "required": True},
            ],
        }
    ],
}
