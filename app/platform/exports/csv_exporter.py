"""CSV export implementation."""

import csv
import io

EXPORT_COLUMNS = [
    "canonical_name", "hq_city", "hq_state", "hq_country",
    "subvertical_tags", "industry_exposure_descriptor", "industry_exposure_intensity",
    "ownership_tier", "disposition",
    "revenue_estimate", "revenue_band", "revenue_quality",
    "ebitda_estimate", "employee_count",
    "pb_status", "pb_entity_id", "sponsor_names", "lender_names",
    "total_score", "eligible_for_outreach",
    "source_tags", "website",
]


def export_csv(companies: list[dict]) -> bytes:
    """Export companies to CSV bytes."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for company in companies:
        row = {}
        for col in EXPORT_COLUMNS:
            val = company.get(col, "")
            if isinstance(val, list):
                val = "; ".join(str(v) for v in val)
            row[col] = val
        writer.writerow(row)

    return output.getvalue().encode("utf-8")
