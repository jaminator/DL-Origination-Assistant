"""QA gate runner — executes all validation checks and produces a report."""

from app.platform.models.schemas import CompanyRecord
from app.platform.validation.checks import (
    ValidationResult,
    check_cascade_anchor_bleed,
    check_data_completeness,
    check_geography,
    check_mega_cap,
    check_score_sanity,
    check_unknown_ownership,
)


class QAReport:
    def __init__(self):
        self.results: list[tuple[str, list[ValidationResult]]] = []
        self.passed: int = 0
        self.failed: int = 0

    def add(self, company_name: str, checks: list[ValidationResult]) -> None:
        self.results.append((company_name, checks))
        if all(c.passed for c in checks):
            self.passed += 1
        else:
            self.failed += 1

    @property
    def total(self) -> int:
        return self.passed + self.failed

    def failures(self) -> list[tuple[str, list[ValidationResult]]]:
        return [(name, checks) for name, checks in self.results if not all(c.passed for c in checks)]


def run_qa_gates(
    companies: list[CompanyRecord],
    geography_filter: list[str] | None = None,
) -> QAReport:
    """Run all QA checks on a list of companies."""
    report = QAReport()

    for company in companies:
        checks = [
            check_data_completeness(company),
            check_unknown_ownership(company),
            check_cascade_anchor_bleed(company),
            check_mega_cap(company),
            check_geography(company, geography_filter),
            check_score_sanity(company),
        ]
        report.add(company.canonical_name, checks)

    return report
