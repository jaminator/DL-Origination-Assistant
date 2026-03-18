"""Normalize S&P Capital IQ responses into canonical field shapes."""

from __future__ import annotations

from typing import Any


def normalize_search_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Capital IQ company search response."""
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


def _extract_credit_metrics(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract leverage and coverage ratios."""
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


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None
