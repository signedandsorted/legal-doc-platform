# Legal Doc Platform

Self-service will, lasting power of attorney (financial decisions LP1F; health and care decisions LP1H), ordinary or general power of attorney (Powers of Attorney Act 1971) and probate helper for England and Wales. Clients answer guided questions step by step with a short video on each step, upload old documents for suggested answers, save and resume with a reference number, preview the draft with a plain-English note on each clause, download a PDF, and send it for solicitor review. Nothing is signed or filed by the app.

Legal wording is draft until a solicitor has reviewed it: see `LAWYER_REVIEW.md`.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # uses SQLite (local.db) unless DATABASE_URL is set
pytest -q
```

## Deploy

`render.yaml` deploys one Python web service, `legal-doc-platform`, in Oregon. Its `DATABASE_URL` comes from the existing Render Postgres `legal-doc-db` (adopted, settings unchanged). On start the app runs its migrations (`app/migrations.py`, recorded in `schema_migrations`): they only add tables and the `drafts.user_id` column, so the existing data is kept.

### Before merge: environment variables on the Render web service

| Variable | Needed | What it does |
|---|---|---|
| `DATABASE_URL` | already set | from `legal-doc-db` |
| `ADMIN_EMAIL` | yes | the first admin account is created (or promoted) for this email on start |
| `ADMIN_INITIAL_PASSWORD` | yes, first deploy | its starting password, 12+ characters; change it after the first sign-in, then you can remove the variable |
| `APP_BASE_URL` | yes | `https://legal-doc-platform-pzjv.onrender.com` (used in password reset links) |
| `RESEND_API_KEY`, `MAIL_FROM` | for password reset emails | preferred; sends over Resend's HTTPS API (works on Render's free plan, which blocks SMTP ports). Default from-address is `josh@signedandsorted.com` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | fallback for password reset emails | used if `RESEND_API_KEY` is unset or Resend fails; without either method a reset request is logged as "not sent" and no email goes out |
| `COOKIE_SECURE` | no | defaults to on (cookies only over HTTPS); set `0` only for local http |
| `MAIL_BACKEND` | no | `log` prints reset links to the log; for local development only |

## Accounts and admin

- Clients register with email and password (argon2id). Sessions are random tokens in an HttpOnly, Secure, SameSite=Lax cookie; only a SHA-256 of the token is stored (`sessions`). They last 14 days and end on sign-out or password reset.
- Every state-changing API call needs the `X-CSRF-Token` header to match the `sas_csrf` cookie, and a same-site `Origin`.
- Sign-in is limited to 5 failures per email and 20 per IP address in 15 minutes; resets and registrations are limited too (`login_attempts`).
- Password reset links are single-use and expire after 60 minutes.
- Drafts and uploads belong to one account; anyone else gets "not found".
- Admins (`role = admin`) get `#/admin`: drafts, clients, uploads, view/download/delete, role changes, and the audit log (`audit_log`).

## Layout

- `app/guide_will.py`, `app/guide_lpa.py`, `app/guide_poa.py`, `app/guide_probate.py`: steps, guidance, questions and GOV.UK sources (`app/fields.py` holds the field schema and source links; `app/lpa_presets.py` holds official section 7 tick-box wording)
- `app/doc_will.py`: will clauses with notes; `app/doc_lpa.py`: LP1F/LP1H form-filling pack and checks; `app/doc_poa.py`: ordinary/general and specific power of attorney deeds; `app/doc_probate.py`: online/post routing, forms, the 5 estate values, IHT estimate
- `docs/LPA_POA_SOURCES.md`: sources for LPA presets, business guidance and ordinary powers of attorney
- `app/documents.py`: missing answers, issues and document dispatch
- `app/extract.py`: reads uploaded PDFs/Word/text and suggests answers
- `app/pdf.py`: PDF export
- `app/main.py`: API (drafts, uploads) and static site
- `app/auth.py`, `app/security.py`, `app/mailer.py`: accounts, sessions, CSRF, rate limits, password reset
- `app/admin.py`: admin API; `app/migrations.py`: schema migrations
- `static/`: the client web app and step videos (`static/videos/<id>.mp4/.vtt/.jpg`)
- `video/`: free on-server video pipeline (Kokoro TTS, SadTalker, ffmpeg) and narration scripts
- `prompts/`: LLM prompt drafts (not used yet; drafting is template-based so it works without a model)


## Supporting video statement

An optional in-browser recording (or video upload) lets a client make a short supporting statement about a will or lasting power of attorney. The prompts are original wording based on *Banks v Goodfellow* (wills) and the Mental Capacity Act 2005 sections 2 and 3 (LPAs). The recording supports, but does not prove, capacity. Clients are also offered an optional referral conversation about a medical capacity assessment (the “golden rule”).

The file is encrypted with AES-256-GCM before it is stored in the database (the same place as other uploads). A SHA-256 fingerprint, UTC time, user id, document id, document-version hash, IP address and browser are kept in the record and the audit log. Only the client and an admin can play it. There is no third-party video service.

Set `STATEMENT_ENCRYPTION_KEY` on the Render service to a url-safe base64 encoding of 32 random bytes (for example `python -c "from app.statement_crypto import generate_key; print(generate_key())"`). Keep a backup of the key: without it existing recordings cannot be played. In local SQLite development only, a key is written to gitignored `local.statement_key` if the variable is not set.

Defaults (changeable later): maximum 8 minutes or 40 MB; recordings are kept for as long as the document and account are kept. Witnesses and professionals cannot yet add their own recordings.
