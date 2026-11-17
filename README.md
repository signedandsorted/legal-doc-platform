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

`render.yaml` deploys one Python web service, `legal-doc-platform`, in Oregon. Its `DATABASE_URL` comes from the existing Render Postgres `legal-doc-db` (adopted, settings unchanged). The app creates its own `drafts` table on start.

## Layout

- `app/guide_will.py`, `app/guide_lpa.py`, `app/guide_probate.py`: steps, guidance, questions and GOV.UK sources (`app/fields.py` holds the field schema and source links)
- `app/doc_will.py`: will clauses with notes; `app/doc_lpa.py`: LP1F/LP1H form-filling pack and checks; `app/doc_probate.py`: online/post routing, forms, the 5 estate values, IHT estimate
- `app/documents.py`: missing answers, issues and document dispatch
- `app/extract.py`: reads uploaded PDFs/Word/text and suggests answers
- `app/pdf.py`: PDF export
- `app/main.py`: API (drafts, uploads) and static site
- `static/`: the client web app and step videos (`static/videos/<id>.mp4/.vtt/.jpg`)
- `video/`: free on-server video pipeline (Kokoro TTS, SadTalker, ffmpeg) and narration scripts
- `prompts/`: LLM prompt drafts (not used yet; drafting is template-based so it works without a model)
