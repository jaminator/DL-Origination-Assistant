"""Name normalization utilities for company name standardization."""

import re

LEGAL_SUFFIXES = [
    r"\bInc\.?$",
    r"\bIncorporated$",
    r"\bCorp\.?$",
    r"\bCorporation$",
    r"\bLLC$",
    r"\bL\.L\.C\.?$",
    r"\bLtd\.?$",
    r"\bLimited$",
    r"\bLP$",
    r"\bL\.P\.?$",
    r"\bLLP$",
    r"\bL\.L\.P\.?$",
    r"\bCo\.?$",
    r"\bCompany$",
    r"\bGroup$",
    r"\bHoldings$",
    r"\bEnterprises$",
    r"\bInternational$",
    r"\bIntl\.?$",
    r"\bServices$",
    r"\bSolutions$",
]

_SUFFIX_PATTERN = re.compile("|".join(LEGAL_SUFFIXES), re.IGNORECASE)


def normalize_company_name(name: str) -> str:
    """Normalize a company name for dedup comparison.

    Strips legal suffixes, normalizes case/punctuation/whitespace, preserves meaningful content.
    """
    # Strip leading/trailing whitespace
    name = name.strip()

    # Remove common punctuation (keep hyphens and ampersands)
    name = re.sub(r"[,\.'\"]", "", name)

    # Strip legal suffixes
    name = _SUFFIX_PATTERN.sub("", name).strip()

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)

    # Lowercase for comparison
    return name.lower().strip()


def canonical_form(name: str) -> str:
    """Return a display-friendly canonical form (title case, stripped suffixes)."""
    normalized = name.strip()
    normalized = _SUFFIX_PATTERN.sub("", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
