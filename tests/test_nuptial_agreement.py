import pytest
from app.nuptial import generate_agreement

def test_generate_prenup_contains_sections():
    text = generate_agreement(data={}, type_="prenup")
    assert "Asset Disclosure" in text
    assert "Independent Legal Advice" in text
    assert "Radmacher" in text
    assert "Prenuptial Agreement" in text

def test_generate_postnup_contains_sections():
    text = generate_agreement(data={}, type_="postnup")
    assert "Asset Disclosure" in text
    assert "Independent Legal Advice" in text
    assert "Radmacher" in text
    assert "Postnuptial Agreement" in text

def test_invalid_type_raises():
    with pytest.raises(ValueError):
        generate_agreement(data={}, type_="invalid")
