import io
import os
import zipfile

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from app.main import app  # noqa: E402
from tests.test_lpa import lpa  # noqa: E402

WILL_TEXT = "This is the last will and testament of me, I, Ada Mary Lovelace, of 1 High St London. I appoint Charles Babbage of 2 Low Rd to be my executor. Dated 3rd March 2015."


def pdf_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for i in range(0, len(text), 90):
        c.drawString(40, y, text[i:i + 90])
        y -= 14
    c.save()
    return buf.getvalue()


def docx_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>' + text + "</w:t></w:r></w:p></w:body></w:document>")
    return buf.getvalue()


def test_probate_upload_pdf_reads_text_and_suggests():
    with TestClient(app) as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": {}}).json()
        r = c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("will.pdf", pdf_bytes(WILL_TEXT + " Date of death: 1 October 2026"), "application/pdf")}).json()
        assert r["read_as"] == "pdf" and r["kind"] == "Old will"
        labels = [s["label"] for s in r["suggestions"]]
        assert any("Ada Mary Lovelace" in x for x in labels) and any("Date of death" in x for x in labels)
        assert c.get(f"/api/drafts/{d['id']}").json()["uploads"][0]["filename"] == "will.pdf"
        assert c.get(f"/api/drafts/{d['id']}/uploads/{r['id']}").content.startswith(b"%PDF")
        assert c.delete(f"/api/drafts/{d['id']}/uploads/{r['id']}").json()["ok"]
        assert c.get(f"/api/drafts/{d['id']}/uploads").json() == []


def test_upload_rejects_bad_types_and_big_files():
    with TestClient(app) as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": {}}).json()
        assert c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 400
        assert c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("big.pdf", b"0" * (10 * 1024 * 1024 + 1), "application/pdf")}).status_code == 400
        photo = c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("scan.jpg", b"\xff\xd8\xff", "image/jpeg")}, data={"kind": "Death certificate"}).json()
        assert photo["read_as"] == "image" and photo["kind"] == "Death certificate" and photo["suggestions"] == []


def test_lpa_upload_flags_certificate_provider_named_in_old_lpa():
    with TestClient(app) as c:
        d = c.post("/api/drafts", json={"service": "lpa_property", "answers": lpa()}).json()
        txt = "Lasting power of attorney LP1F. Attorneys: Dr Eve Five of Surgery Road."
        r = c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("old.docx", docx_bytes(txt), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}).json()
        assert r["kind"] == "Existing LPA" and r["read_as"] == "docx"
        issues = c.get(f"/api/drafts/{d['id']}").json()["issues"]
        assert any("named in a document you uploaded" in i["message"] for i in issues)
        doc = c.get(f"/api/drafts/{d['id']}/document").json()
        assert any(s["heading"] == "Documents you uploaded" for s in doc["sections"])


def test_no_uploads_after_submission():
    with TestClient(app) as c:
        d = c.post("/api/drafts", json={"service": "lpa_property", "answers": lpa()}).json()
        assert c.post(f"/api/drafts/{d['id']}/submit").status_code == 200
        assert c.post(f"/api/drafts/{d['id']}/uploads", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 409
