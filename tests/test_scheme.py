"""The scheme checklist, the daily page check, and the retainer. None of them accredits a firm."""
import json
from pathlib import Path

from app.scheme import for_matter
from app.source_watch import fingerprint, run_check


def test_scheme_is_a_file_checklist_not_an_accreditation():
    will = for_matter("will", {})
    probate = for_matter("probate", {"done": ["report28"], "last_report": "2026-11-01"})
    assert any("14 days" in item["point"] for item in will["items"])
    assert any(item["id"] == "oldwill" for item in will["items"])
    assert not any(item["area"] == "estate" for item in will["items"])
    assert any(item["id"] == "report28" and item["done"] for item in probate["items"])
    text = " ".join(will["cannot"])
    assert "cannot" in text
    assert "does not make the firm a member" in will["notice"]
    assert all("7 days" not in item["point"] or "14 days" in item["point"] for item in will["items"])


def test_source_check_records_a_change_and_does_not_rewrite(tmp_path, monkeypatch):
    monkeypatch.setattr("app.source_watch.STORE", tmp_path / "source_watch.json")
    pages = {"https://example.test/a": (200, b"<html><body>First version of the fee.</body></html>", "")}

    def fake(url, timeout=20):
        status, body, _ = pages[url]
        return status, fingerprint(body, "text/html"), ""

    monkeypatch.setattr("app.source_watch.PAGES", [{"id": "fee", "title": "Fees", "url": "https://example.test/a"}])
    first = run_check(fake)
    assert first["found"] == []
    pages["https://example.test/a"] = (200, b"<html><body>The fee is now different.</body></html>", "")
    second = run_check(fake)
    assert second["found"][0]["title"] == "Fees"
    assert "does not rewrite" in second["found"][0]["note"]
    saved = json.loads(Path(tmp_path / "source_watch.json").read_text())
    assert saved["changes"][0]["id"] == "fee"


def test_a_signed_retainer_does_not_waive_the_right_before_the_work_is_finished():
    from app.retainer import clean_retainer, effect
    signed = clean_retainer({
        "signed_name": "Ada King",
        "signed_on": "2026-11-24",
        "place": "At my home, or someone else’s home",
        "finished": ["will"],
    })
    assert signed["signed"] is True
    assert "probate" in signed["sections"] and "lpa_health" in signed["sections"]
    home = effect(signed, "probate")
    assert "has not ended" in home
    assert "fully performed" in effect(signed, "will")
    office = effect({**signed, "place": "At the firm’s office", "finished": []}, "will")
    assert "office" in office and "not because the retainer waived" in office
