# Legal Doc Platform

Self-service will, lasting power of attorney (property and financial affairs; health and welfare) and probate helper for England and Wales. Clients answer guided questions step by step (with an intro video), save and resume with a reference number, preview the draft, download a PDF, and send it for solicitor review. Nothing is signed or filed by the app.

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

- `app/guides.py`: the services, steps, guidance text and questions
- `app/documents.py`: turns answers into the draft will, LPA summary or probate summary, and lists missing answers
- `app/pdf.py`: PDF export
- `app/main.py`: API and static site
- `static/`: the client web app and videos
- `prompts/`: LLM prompt drafts (not used yet; drafting is template-based so it works without a model)
