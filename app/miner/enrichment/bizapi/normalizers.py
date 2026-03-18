"""Normalize BizAPI responses into canonical field shapes."""

from __future__ import annotations

from typing import Any


def normalize_match_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a BizAPI match response into the adapter contract.

    Handles field name variations across BizAPI match methods (Standard, URL,
    DUNS, Name, Loose, Phone) and returns a stable dict shape.
    """
    address = _extract_address(raw)
    linkage = _extract_corporate_linkage(raw)

    return {
        "duns": raw.get("DUNS") or raw.get("duns") or raw.get("duns_number", ""),
        "match_method": raw.get("match_method", "unknown"),
        "match_confidence": _compute_match_confidence(raw),
        "verified_name": (
            raw.get("CompanyName")
            or raw.get("company_name")
            or raw.get("BusinessName")
            or ""
        ),
        "verified_address": address,
        "naics_code": raw.get("NAICSCode") or raw.get("naics_code") or raw.get("PrimaryNAICS", ""),
        "naics_description": (
            raw.get("NAICSDescription")
            or raw.get("naics_description")
            or raw.get("PrimaryNAICSDescription", "")
        ),
        "sic_code": raw.get("SICCode") or raw.get("sic_code") or raw.get("PrimarySIC", ""),
        "sic_description": (
            raw.get("SICDescription")
            or raw.get("sic_description")
            or raw.get("PrimarySICDescription", "")
        ),
        "year_started": _safe_int(raw.get("YearStarted") or raw.get("year_started")),
        "employee_count": _safe_int(raw.get("EmployeesHere") or raw.get("EmployeesTotal") or raw.get("employee_count")),
        "sales_volume": _safe_float_millions(raw.get("SalesVolume") or raw.get("sales_volume")),
        "website": raw.get("URL") or raw.get("url") or raw.get("WebAddress", ""),
        "corporate_linkage": linkage,
    }


def _extract_address(raw: dict[str, Any]) -> dict[str, str]:
    """Extract and normalize address fields."""
    return {
        "street": raw.get("Street") or raw.get("street") or raw.get("Address", ""),
        "city": raw.get("City") or raw.get("city") or "",
        "state": raw.get("State") or raw.get("state") or raw.get("StateProvince", ""),
        "zip": raw.get("Zip") or raw.get("zip") or raw.get("PostalCode", ""),
        "country": raw.get("Country") or raw.get("country") or raw.get("CountryCode", "US"),
    }


def _extract_corporate_linkage(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract corporate linkage (parent/subsidiary relationships)."""
    return {
        "parent_duns": raw.get("ParentDUNS") or raw.get("parent_duns"),
        "parent_name": raw.get("ParentCompanyName") or raw.get("parent_name"),
        "subsidiary_count": _safe_int(raw.get("SubsidiaryCount") or raw.get("subsidiary_count")) or 0,
    }


def _compute_match_confidence(raw: dict[str, Any]) -> float:
    """Derive a confidence score from BizAPI match quality indicators."""
    if raw.get("MatchScore") is not None or raw.get("match_score") is not None:
        score = raw.get("MatchScore") or raw.get("match_score")
        return min(float(score) / 100.0, 1.0) if float(score) > 1 else float(score)

    # Heuristic: assign confidence by match method
    method = raw.get("match_method", "").lower()
    method_confidence = {
        "duns": 0.98,
        "url": 0.90,
        "standard": 0.80,
        "name": 0.65,
        "phone": 0.70,
        "loose": 0.50,
    }
    return method_confidence.get(method, 0.50)


def _safe_int(value: Any) -> int | None:
    """Safely convert to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float_millions(value: Any) -> float | None:
    """Safely convert sales volume to float in millions."""
    if value is None:
        return None
    try:
        v = float(value)
        # BizAPI may return in dollars; normalize to millions if > 10,000
        if v > 10_000:
            return round(v / 1_000_000, 2)
        return round(v, 2)
    except (ValueError, TypeError):
        return None
