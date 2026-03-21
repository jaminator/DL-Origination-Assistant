"""Normalize S&P Capital IQ SPQL responses into canonical field shapes.

Capital IQ's GDS API returns data in SPQL response format — each
``inputRequest`` yields a result containing a ``Mnemonic`` key and
``Rows`` with the actual values.  These helpers extract values from
that structure and canonicalize them into the shapes our pipeline expects.
"""

from __future__ import annotations

from typing import Any


def normalize_spql_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse a raw SPQL GDSSDKResponse into a mnemonic→value mapping.

    The SPQL response structure:
    {
        "GDSSDKResponse": [
            {
                "Identifier": "IQ12345",
                "Mnemonic": "IQ_TOTAL_REV",
                "Rows": [{"Row": ["150.0"]}]
            },
            ...
        ]
    }
    """
    results: dict[str, Any] = {}
    sdk_response = raw.get("GDSSDKResponse", [])

    for item in sdk_response:
        mnemonic = item.get("Mnemonic", "")
        rows = item.get("Rows", [])
        if rows and isinstance(rows, list):
            first_row = rows[0]
            if isinstance(first_row, dict):
                row_data = first_row.get("Row", [])
            elif isinstance(first_row, list):
                row_data = first_row
            else:
                row_data = [first_row]

            if row_data and len(row_data) > 0:
                value = row_data[0]
                # SPQL returns "Data Unavailable" for missing data
                if isinstance(value, str) and value.lower() in ("data unavailable", ""):
                    results[mnemonic] = None
                else:
                    results[mnemonic] = value
            else:
                results[mnemonic] = None
        else:
            results[mnemonic] = None

    return results


def normalize_search_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Capital IQ company search / profile SPQL response."""
    # Support both SPQL format and legacy REST format
    if "GDSSDKResponse" in raw:
        values = normalize_spql_response(raw)
        entity_id = _extract_identifier(raw)
        if not entity_id and not values:
            return {}
        return {
            "entity_id": entity_id,
            "name": values.get("IQ_COMPANY_NAME", ""),
            "match_confidence": 1.0,  # SPQL uses exact ID matching
            "primary_industry": values.get("IQ_PRIMARY_INDUSTRY", ""),
            "hq_location": _format_spql_location(values),
        }

    # Legacy REST format fallback
    results = raw.get("Results") or raw.get("results") or []
    if not results:
        return {}

    best = results[0] if isinstance(results, list) else results

    return {
        "entity_id": (
            best.get("CompanyId")
            or best.get("companyId")
            or best.get("CiqId")
            or ""
        ),
        "name": best.get("CompanyName") or best.get("companyName") or "",
        "match_confidence": _compute_confidence(best),
        "primary_industry": (
            best.get("PrimaryIndustry")
            or best.get("primaryIndustry")
            or best.get("IndustryClassification", "")
        ),
        "hq_location": _format_location(best),
    }


def normalize_financials_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize Capital IQ financial data response."""
    # SPQL format
    if "GDSSDKResponse" in raw:
        values = normalize_spql_response(raw)
        entity_id = _extract_identifier(raw)
        return {
            "entity_id": entity_id,
            "revenue": _safe_float(values.get("IQ_TOTAL_REV")),
            "ebitda": _safe_float(values.get("IQ_EBITDA")),
            "total_debt": _safe_float(values.get("IQ_TOTAL_DEBT")),
            "net_debt": _safe_float(values.get("IQ_NET_DEBT")),
            "credit_metrics": _extract_spql_credit_metrics(values),
        }

    # Legacy REST format
    return {
        "entity_id": raw.get("CompanyId") or raw.get("companyId") or "",
        "revenue": _safe_float(raw.get("TotalRevenue") or raw.get("revenue")),
        "ebitda": _safe_float(raw.get("EBITDA") or raw.get("ebitda")),
        "total_debt": _safe_float(raw.get("TotalDebt") or raw.get("totalDebt")),
        "net_debt": _safe_float(raw.get("NetDebt") or raw.get("netDebt")),
        "credit_metrics": _extract_credit_metrics(raw),
    }


def normalize_ownership_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize Capital IQ ownership and investor data response."""
    # SPQL format
    if "GDSSDKResponse" in raw:
        values = normalize_spql_response(raw)
        entity_id = _extract_identifier(raw)

        # Extract investors from SPQL (may be in IQ_KEY_INVESTORS as semicolon-delimited)
        investors_str = values.get("IQ_KEY_INVESTORS", "")
        key_investors = []
        if investors_str and isinstance(investors_str, str):
            key_investors = [inv.strip() for inv in investors_str.split(";") if inv.strip()]

        return {
            "entity_id": entity_id,
            "ownership_type": values.get("IQ_OWNERSHIP_STATUS", ""),
            "key_investors": key_investors,
            "ma_history": [],  # M&A history requires separate GDSHV query
        }

    # Legacy REST format
    investors_raw = raw.get("KeyInvestors") or raw.get("investors") or []
    ma_raw = raw.get("MAHistory") or raw.get("ma_history") or []

    return {
        "entity_id": raw.get("CompanyId") or raw.get("companyId") or "",
        "ownership_type": (
            raw.get("OwnershipType")
            or raw.get("ownershipType")
            or raw.get("OwnershipStatus", "")
        ),
        "key_investors": [
            inv.get("Name") or inv.get("name") or str(inv)
            for inv in investors_raw
            if isinstance(inv, dict | str)
        ],
        "ma_history": [
            {
                "date": event.get("Date") or event.get("date", ""),
                "type": event.get("Type") or event.get("type", ""),
                "target": event.get("TargetName") or event.get("target", ""),
                "value": _safe_float(event.get("TransactionValue") or event.get("value")),
            }
            for event in ma_raw
            if isinstance(event, dict)
        ],
    }


def normalize_profile_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Capital IQ company profile SPQL response.

    Returns GICS code, SIC code, company status, and industry sector.
    """
    if "GDSSDKResponse" in raw:
        values = normalize_spql_response(raw)
        entity_id = _extract_identifier(raw)
        return {
            "entity_id": entity_id,
            "gics_code": values.get("IQ_GICS_CODE"),
            "sic_code": values.get("IQ_PRIMARY_SIC_CODE"),
            "company_status": values.get("IQ_COMPANY_STATUS"),
            "industry_sector": values.get("IQ_INDUSTRY_SECTOR"),
        }

    # Fallback for non-SPQL
    return {
        "entity_id": raw.get("CompanyId") or raw.get("companyId") or "",
        "gics_code": raw.get("GICSCode") or raw.get("gicsCode"),
        "sic_code": raw.get("SICCode") or raw.get("sicCode"),
        "company_status": raw.get("CompanyStatus") or raw.get("companyStatus"),
        "industry_sector": raw.get("IndustrySector") or raw.get("industrySector"),
    }


# -- Helpers -------------------------------------------------------------


def _extract_identifier(raw: dict[str, Any]) -> str:
    """Extract the CIQ entity identifier from an SPQL response."""
    sdk_response = raw.get("GDSSDKResponse", [])
    if sdk_response and isinstance(sdk_response, list):
        first = sdk_response[0]
        identifier = first.get("Identifier", "")
        # Strip "IQ" prefix if present (e.g. "IQ12345" → "12345")
        if isinstance(identifier, str) and identifier.startswith("IQ"):
            return identifier[2:]
        return identifier or ""
    return ""


def _extract_spql_credit_metrics(values: dict[str, Any]) -> dict[str, Any] | None:
    """Extract credit metrics from SPQL mnemonic values."""
    total_leverage = _safe_float(values.get("IQ_TOTAL_LEVERAGE"))
    net_leverage = _safe_float(values.get("IQ_NET_LEVERAGE"))
    interest_coverage = _safe_float(values.get("IQ_INTEREST_COVERAGE"))

    if any(v is not None for v in (total_leverage, net_leverage, interest_coverage)):
        return {
            "total_leverage": total_leverage,
            "net_leverage": net_leverage,
            "interest_coverage": interest_coverage,
        }
    return None


def _extract_credit_metrics(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract leverage and coverage ratios from legacy format."""
    metrics = raw.get("CreditMetrics") or raw.get("creditMetrics")
    if isinstance(metrics, dict):
        return {
            "total_leverage": _safe_float(metrics.get("TotalLeverage") or metrics.get("total_leverage")),
            "net_leverage": _safe_float(metrics.get("NetLeverage") or metrics.get("net_leverage")),
            "interest_coverage": _safe_float(
                metrics.get("InterestCoverage") or metrics.get("interest_coverage")
            ),
        }
    return None


def _compute_confidence(raw: dict[str, Any]) -> float:
    """Derive confidence from CIQ match quality."""
    if raw.get("MatchScore") is not None:
        score = float(raw["MatchScore"])
        return min(score / 100.0, 1.0) if score > 1 else score
    if raw.get("matchConfidence") is not None:
        return float(raw["matchConfidence"])
    return 0.75


def _format_location(raw: dict[str, Any]) -> str:
    city = raw.get("City") or raw.get("city", "")
    state = raw.get("State") or raw.get("state", "")
    country = raw.get("Country") or raw.get("country", "")
    return ", ".join(p for p in (city, state, country) if p)


def _format_spql_location(values: dict[str, Any]) -> str:
    """Format location from SPQL mnemonic values."""
    city = values.get("IQ_COMPANY_CITY", "")
    state = values.get("IQ_COMPANY_STATE", "")
    country = values.get("IQ_COMPANY_COUNTRY", "")
    return ", ".join(p for p in (city, state, country) if p and isinstance(p, str))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None
