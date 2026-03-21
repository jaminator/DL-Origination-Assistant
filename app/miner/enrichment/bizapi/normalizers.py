"""Normalize BizAPI V2 responses into canonical field shapes.

The real BizAPI returns a 3-section JSON response:
  - "Search Terms": echo of input fields
  - "Matching Data": match quality indicators
  - "Appended Data": firmographic data (or {"Message": "No match found"})
"""

from __future__ import annotations

from typing import Any


def normalize_match_response(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a BizAPI V2 cosearch response into the adapter contract.

    Returns None if no match was found.
    """
    matching = raw.get("Matching Data", {})
    appended = raw.get("Appended Data", {})

    # No match: the API returns {"Message": "No match found"} in Appended Data
    if "Message" in appended or not matching.get("DUNS #"):
        return None

    address = _extract_address(appended)
    linkage = _extract_corporate_linkage(appended)

    return {
        "duns": matching.get("DUNS #", ""),
        "match_method": _normalize_match_method(matching.get("Match Method", "")),
        "match_confidence": _confidence_code_to_float(matching.get("Confidence Code")),
        "match_grade": matching.get("Match Grade", ""),
        "bemfab": matching.get("BEMFAB", ""),
        "matches_remaining": matching.get("Matches Remaining"),
        "verified_name": appended.get("Company Name", ""),
        "secondary_name": appended.get("Secondary Business Name", ""),
        "verified_address": address,
        "phone": appended.get("Phone", ""),
        "website": appended.get("URL", ""),
        "ceo_name": appended.get("CEO Name", ""),
        "ceo_title": appended.get("CEO Title", ""),
        "line_of_business": appended.get("Line of Business", ""),
        "location_type": appended.get("Location Type", ""),
        "year_started": _safe_int(appended.get("Year Started")),
        "employees_on_site": _parse_int_with_commas(appended.get("Employees on Site")),
        "employee_count": _parse_int_with_commas(appended.get("Employees Total")),
        "sales_volume": _parse_sales_volume(appended.get("Sales Volume in US$")),
        "naics_code": appended.get("NAICS 1 Code", ""),
        "naics_description": appended.get("NAICS 1 Description", ""),
        "naics_code_2": appended.get("NAICS 2 Code", ""),
        "naics_description_2": appended.get("NAICS 2 Description", ""),
        "sic_code": appended.get("4 Digit SIC 1", ""),
        "sic_description": appended.get("4 Digit SIC 1 Description", ""),
        "sic_code_2": appended.get("4 Digit SIC 2", ""),
        "sic_description_2": appended.get("4 Digit SIC 2 Description", ""),
        "sic_code_8_1": appended.get("8 Digit SIC 1", ""),
        "sic_description_8_1": appended.get("8 Digit SIC 1 Description", ""),
        "sic_code_8_2": appended.get("8 Digit SIC 2", ""),
        "sic_description_8_2": appended.get("8 Digit SIC 2 Description", ""),
        "corporate_linkage": linkage,
    }


def _extract_address(appended: dict[str, Any]) -> dict[str, str]:
    """Extract and normalize address fields from Appended Data."""
    return {
        "street": appended.get("Street Address", ""),
        "city": appended.get("City", ""),
        "state": appended.get("State/Province", ""),
        "zip": appended.get("ZIP Code", ""),
        "country": appended.get("Country", "US"),
    }


def _extract_corporate_linkage(appended: dict[str, Any]) -> dict[str, Any]:
    """Extract full corporate linkage from Appended Data."""
    return {
        "subsidiary_indicator": appended.get("Subsidiary Indicator", ""),
        "global_ult": {
            "indicator": appended.get("Global Ult Indicator", ""),
            "duns": appended.get("Global Ult DUNS #", ""),
            "name": appended.get("Global Ult Bus. Name", ""),
            "state": appended.get("Global Ult State/Province", ""),
            "country": appended.get("Global Ult Country", ""),
        },
        "domestic_ult": {
            "duns": appended.get("Domestic Ult DUNS #", ""),
            "name": appended.get("Domestic Ult Name", ""),
            "state": appended.get("Domestic Ult State/Province", ""),
            "country": appended.get("Domestic Ult Country", ""),
        },
        "hq_parent": {
            "parent_duns": appended.get("Parent Ult DUNS #", ""),
            "hq_duns": appended.get("HQ Ult DUNS #", ""),
            "name": appended.get("HQ/Parent Ult Bus. Name", ""),
            "state": appended.get("HQ/Parent State/Province", ""),
            "country": appended.get("HQ/Parent Country", ""),
        },
        "hierarchy_code": appended.get("Hierarchy Code", ""),
        "family_member_count": _safe_int(appended.get("# of Family Members")),
    }


def _normalize_match_method(raw_method: str) -> str:
    """Convert API match method name to internal lowercase key."""
    mapping = {
        "DUNS Match": "duns",
        "Standard Match": "standard",
        "Loose Match": "loose",
        "URL Match": "url",
        "Name Match": "name",
        "Phone Match": "phone",
    }
    return mapping.get(raw_method, raw_method.lower().replace(" match", "").strip() or "unknown")


def _confidence_code_to_float(code: Any) -> float:
    """Convert BizAPI Confidence Code (integer 0-10) to float 0.0-1.0."""
    if code is None:
        return 0.0
    try:
        return min(int(code) / 10.0, 1.0)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value: Any) -> int | None:
    """Safely convert to int, returning None on failure."""
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_int_with_commas(value: Any) -> int | None:
    """Parse an integer that may contain commas (e.g. '15,000')."""
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_sales_volume(value: Any) -> float | None:
    """Parse Sales Volume in US$ (raw dollars) to float in millions."""
    if value is None or value == "":
        return None
    try:
        v = float(str(value).replace(",", ""))
        return round(v / 1_000_000, 2)
    except (ValueError, TypeError):
        return None
