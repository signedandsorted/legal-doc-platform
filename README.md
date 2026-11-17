# Legal Doc Platform

Self-service will, lasting power of attorney (financial decisions LP1F; health and care decisions LP1H) and probate helper for England and Wales. Clients answer guided questions step by step with a short video on each step, upload old documents for suggested answers, save and resume with a reference number, preview the draft with a plain-English note on each clause, download a PDF, and send it for solicitor review. Nothing is signed or filed by the app.

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
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | for password reset emails | without them a reset request is logged as "not sent" and no email goes out |
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

- `app/guide_will.py`, `app/guide_lpa.py`, `app/guide_probate.py`: steps, guidance, questions and GOV.UK sources (`app/fields.py` holds the field schema and source links)
- `app/doc_will.py`: will clauses with notes; `app/doc_lpa.py`: LP1F/LP1H form-filling pack and checks; `app/doc_probate.py`: online/post routing, forms, the 5 estate values, IHT estimate
- `app/documents.py`: missing answers, issues and document dispatch
- `app/extract.py`: reads uploaded PDFs/Word/text and suggests answers
- `app/pdf.py`: PDF export
- `app/main.py`: API (drafts, uploads) and static site
- `app/auth.py`, `app/security.py`, `app/mailer.py`: accounts, sessions, CSRF, rate limits, password reset
- `app/admin.py`: admin API; `app/migrations.py`: schema migrations
- `static/`: the client web app and step videos (`static/videos/<id>.mp4/.vtt/.jpg`)
- `video/`: free on-server video pipeline (Kokoro TTS, SadTalker, ffmpeg) and narration scripts
- `prompts/`: LLM prompt drafts (not used yet; drafting is template-based so it works without a model)
