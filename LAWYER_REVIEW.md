# Before merge to `main`: lawyer review and Josh's OK

Branch `overhaul-2026-11-16`. Nothing here is live: `main` (commit d8ac0087) auto-deploys to Render and has not been touched.
All new or changed legal wording is **DRAFT** and must be checked by a solicitor (England and Wales) before it is shown to clients.

## 1. Will precedents (`app/doc_will.py`)
Every clause and its plain-English note. In particular:
- Revocation limited to England and Wales property where the client keeps a foreign will.
- Expectation-of-marriage clause (s.18 Wills Act 1837 as amended).
- Professional charging clause; digital executor appointment.
- Guardians and replacement guardian.
- Charity gift with receipt and merger wording; property gift subject to mortgage; pet gift with money "without creating a trust".
- Life interest trust (home or whole residue), discretionary trust (125-year trust period), vulnerable person's trust, business/agricultural property placeholder.
- Contingent age (18/21/25) with 28-day survivorship and substitution; hotchpot/lifetime gifts; release of debts.
- Trustee powers clause (Trustee Act 2000; ss.31 and 32 Trustee Act 1925 as amended).
- Separate documents: letter of wishes, statement of reasons for exclusion (Inheritance (Provision for Family and Dependants) Act 1975).
- Attestation clause.

## 2. LPA packs (`app/guide_lpa.py`, `app/doc_lpa.py`)
- Mapping of answers to LP1F/LP1H sections 1 to 15, continuation sheets 1 and 2, LP3, LPA120.
- Certificate provider eligibility checks (wording of the six confirmations).
- Signing-order text and the "attorneys cannot witness the donor" rule.
- Fees: £92 / £184 / £46 re-application (GOV.UK, checked 17 Nov 2026).

## 3. Probate rules engine (`app/guide_probate.py`, `app/doc_probate.py`)
- When the plan says "apply by post" vs "online" (lost will / PA13, domicile outside England and Wales, someone else applying / PA11-PA12, more than 4 applicants).
- Who can apply with and without a will; spouse giving up (PA16); PA14, PA15.
- Excepted-estate test for deaths on or after 1 Jan 2022, the IHT400 triggers, and IHT402/IHT435/IHT436 selection.
- IHT estimate: nil rate band £325,000, residence nil rate band £175,000 with £2m taper, transfer of unused bands, 36% charity rate (simplified baseline). The transferred-RNRB assumption (100% unused) must be confirmed per case.
- The 5 probate values (gross/net for IHT, net qualifying, gross/net for probate).
- Probate fee £526 over £5,000 (GOV.UK fees page, checked 17 Nov 2026), £2 extra copies.

## 4. Guidance text and videos
- All step guidance in `app/guide_*.py`.
- Video narration in `video/scripts.json` (rendered with an open-source British English voice and an AI-generated presenter). The presenter is synthetic, not a real person, and every video now carries the on-page label "AI-generated video: the presenter is not a real person and the voice is an AI-generated voice." Josh asked for the voice to match his own; that needs about 2 minutes of his recorded speech (`video/RECORDING_SCRIPT.md`). Until then the voice is a stock open-source voice. Please check the label wording, and whether a cloned voice of Josh needs any extra disclosure.

## 5. Uploads and data protection
- Uploaded documents (wills, LPAs, death certificates) are stored in the `uploads` table in `legal-doc-db`, up to 10 MB each, 15 per draft. Access control is now in place: clients sign in with email and password (argon2id hashes), every draft and upload belongs to one account, and only that account and admins can open it; the reference number alone no longer gives access. Admins can view, download and delete client data, and every admin view, download and deletion is written to an audit log. Still needed from the solicitor/Josh: a privacy notice, a retention period, and the wording of the account sign-up page (what we keep and why).
- Drafts made before accounts existed have no owner; only admins can see them (Admin → Drafts).
- Suggestions from documents are heuristic; the client must confirm each one.

## 6. Josh's decisions before merge
Decided by Josh on 17 Nov 2026:
- Lawyer review: **yes**, use this file as the checklist for the solicitor.
- Client logins: **yes**, added (email + password, password reset, rate limits, CSRF protection).
- Admin area in the database: **yes**, added (clients, drafts, uploads, roles, audit log) using the existing `legal-doc-db` with additive migrations.
- Videos: **stay in the repo** (`static/videos/`).
- Voice: **match Josh's voice**. Waiting on a recording from Josh (see `video/RECORDING_SCRIPT.md`).

Still open:
- Approve the legal wording after solicitor review.
- Set the environment variables in `README.md` → "Before merge" on the Render service.
- Then say "merge" (main auto-deploys to Render).


## 7. LPA section 7 presets, business LPAs and ordinary powers of attorney (branch `feat/lpa-presets-business-ordinary-poa`)

New or newly offered wording, all flagged as draft. See `docs/LPA_POA_SOURCES.md` for sources. Please review in particular:

- Tick-box preferences and instructions copied from LP12 (updated 3 November 2026), including professional fee wording, home/care restrictions, gifts, accounts and investment-adviser examples.
- The discretionary investment / nominee instruction, which is the former OPG LP12 clause (removed in 2022) as quoted by The Law Society in May 2022, not current official wording.
- Business LPA questions and the official LP12 personal-only and business-only instructions, plus the warning not to split roles between jointly-and-severally appointed attorneys in one LPA.
- The new Business step in the will, including the Inheritance Tax Business Relief summary (and the 6 April 2026 cap) and the solicitor-drafting placeholder.
- The new Ordinary or general power of attorney service: the Schedule 1 general deed (filled as a form to the like effect under section 10) and the specific/limited deed, execution as a deed, and the explanation that the power ends on death, bankruptcy or loss of mental capacity and is not a substitute for an LPA.

Still not legal advice. Nothing in this branch should be shown to clients as final until this review is done and Josh has approved a merge.
