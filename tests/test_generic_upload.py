import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_generic_upload_success(tmp_path):
    client = TestClient(app)
    # Create a small PDF-like byte payload
    payload = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("test.pdf", payload, "application/pdf")}
    data = {"user_id": "testuser"}
    resp = client.post("/upload", files=files, data=data)
    assert resp.status_code == 200
    json = resp.json()
    assert json["filename"] == "test.pdf"
    # Ensure the file was saved on disk
    assert Path(json["saved_path"]).exists()

def test_generic_upload_rejects_bad_type(tmp_path):
    client = TestClient(app)
    files = {"file": ("bad.exe", b"MZ", "application/octet-stream")}
    data = {"user_id": "testuser"}
    resp = client.post("/upload", files=files, data=data)
    assert resp.status_code == 400
