# Audit of legal-doc-platform vs Sure Will Writer and gov.uk

## Will module
- Current steps cover basic will creation but miss:
  - Trust provisions (e.g., discretionary trusts, life interest trusts) mentioned on Sure Will Writer site.
  - Customisable precedents and ability to add bespoke clauses (Sure Will Writer feature).
  - Guidance on updating will after marriage/civil partnership (present but could be expanded).
  - No reference/link to official gov.uk will guidance.
- Video: only intro video exists; needs human‑like English video for each step.

## LPA module
- Two LPA types implemented (property/financial and health/welfare) aligning with gov.uk.
- Missing links to official GOV.UK LPA forms (LP1F, LP1H) and registration fee info.
- Guidance does not include certificate provider eligibility details from gov.uk.
- No support for “when can be used” options beyond basic.
- No reference to OPG registration process steps.

## Probate helper
- Covers intro, deceased info, will presence, estate valuation.
- Lacks explicit link to GOV.UK probate application page and fee (£215 as of 2026, check).
- No guidance on Inheritance Tax thresholds and IHT400 form link.
- No mention of Gazette notice requirement.
- No video steps.

## UX/UI
- Forms are functional but UI is dated; no modern responsive design, no progress bar, no stepper UI.
- No mobile‑friendly layout.

## Document upload
- No upload fields defined in guides; need file upload support for old wills, LPA forms, probate papers.

## Videos
- Existing `static/videos/will_intro.mp4` is non‑English, non‑human looking.
- Need new videos for each step, English, human‑like appearance.

## Legal wording
- Drafted text needs lawyer review before go‑live (as required).

## Actions needed
1. Add missing trust clause fields to WILL steps.
2. Insert gov.uk links in guidance sections.
3. Add file upload fields to each service.
4. Update UX templates (frontend) for modern responsive design.
5. Replace videos (placeholder now, propose options).
6. Create PR with these changes on branch `overhaul-2026-11-16`.

## Items needing Josh
- Approve budget/options for new human‑like video creation (paid service options).
- Review any new third‑party assets (e.g., stock images) for licensing.
- Confirm any additional legal wording to be added before lawyer review.
