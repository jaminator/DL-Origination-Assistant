"""Tests for company name normalization."""

from app.platform.utils.normalization import canonical_form, normalize_company_name


def test_strip_legal_suffixes():
    assert normalize_company_name("Acme Corp.") == "acme"
    assert normalize_company_name("Acme Corporation") == "acme"
    assert normalize_company_name("Acme Inc") == "acme"
    assert normalize_company_name("Acme LLC") == "acme"


def test_normalize_whitespace():
    assert normalize_company_name("  Acme   Electric   ") == "acme electric"


def test_normalize_punctuation():
    assert normalize_company_name("Acme's Electric") == "acmes electric"
    assert normalize_company_name('Acme "Big" Electric') == "acme big electric"


def test_preserves_meaningful_content():
    assert normalize_company_name("M&A Power Solutions") == "m&a power"


def test_canonical_form():
    result = canonical_form("  Acme Electric Corp.  ")
    assert result == "Acme Electric"
