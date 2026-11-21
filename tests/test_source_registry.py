import re
from urllib.parse import urlparse

def test_gov_source_registry():
    from app.fields import GOV
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for key, entry in GOV.items():
        url = entry.get("url", "")
        host = urlparse(url).netloc.lower()
        official = host == "gov.uk" or host.endswith(".gov.uk")
        assert official, f"{key} url is not an official .gov.uk source: {url}"
        checked = entry.get("checked")
        assert checked is not None, f"{key} missing checked date"
        assert date_pattern.fullmatch(checked), f"{key} checked date format invalid: {checked}"
