import io
import zipfile
from datetime import date

from app.integrations import cra_letters
from tests.helpers import user_client
from tests.test_probate import answers


def test_letters_render_with_estate_data():
    a = answers()
    a["deceased"]["date_of_birth"] = "1950-01-01"
    a["discovery"] = {"previous_addresses": "1 Old Road"}
    p = cra_letters.letters(a, today=date(2026, 11, 24))
    assert [l["agency"] for l in p["letters"]] == ["Experian", "Equifax", "TransUnion"]
    text = "\n".join(p["letters"][0]["lines"])
    assert "Sam Smith" in text and "1 October 2026" not in text and "2026-10-01" in text and "1 Old Road" in text and "Pat Smith" in text
    assert any("grant" in e.lower() for e in p["enclosures"]) and sum("proof" in e.lower() for e in p["enclosures"]) == 1
    assert "Two proofs" in " ".join(p["enclosures"])
    assert p["missing"] == []


def test_missing_fields_flagged_and_placeholders():
    p = cra_letters.letters({})
    assert "Full name" in p["missing"] and "Your name (executor or administrator)" in p["missing"]
    assert "[full name]" in "\n".join(p["letters"][0]["lines"])


def test_pdf_and_docx_downloads():
    with user_client() as c:
        d = c.post("/api/drafts", json={"service": "probate", "answers": answers()}).json()
        pdf = c.get(f"/api/probate/drafts/{d['id']}/cra-letters.pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        dx = c.get(f"/api/probate/drafts/{d['id']}/cra-letters.docx")
        assert dx.status_code == 200
        xml = zipfile.ZipFile(io.BytesIO(dx.content)).read("word/document.xml").decode()
        assert "Sam Smith" in xml and "TransUnion" in xml
        assert c.get(f"/api/probate/drafts/{d['id']}/cra-letters").json()["missing"]
