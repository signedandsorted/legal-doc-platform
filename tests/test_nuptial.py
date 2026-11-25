import pytest
from app.documents import build_document, missing_fields

def test_nuptial_missing_fields_none():
    answers = {"intro": {"type": "prenup", "assets": "House", "legal_advice": "yes"}}
    missing = missing_fields("nuptial", answers)
    assert missing == []

def test_nuptial_document_contains_fields():
    answers = {"intro": {"type": "prenup", "assets": "House", "legal_advice": "yes"}}
    doc = build_document("nuptial", answers)
    # Gather all paragraph text
    text = "\n".join(p for sec in doc["sections"] for p in sec["paragraphs"])
    assert "Asset disclosure" in text or "assets" in text.lower()
    assert "legal advice" in text.lower()
