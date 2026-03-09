"""Manual review queue generation and management."""

from uuid import UUID, uuid4

from app.platform.models.enums import ReviewReason
from app.platform.models.schemas import ReviewQueueItem
from app.platform.utils.logging import get_logger

logger = get_logger("review.queue")


def generate_review_items_from_dedup(
    run_id: UUID,
    ambiguous_pairs: list[tuple[str, str, float]],
) -> list[ReviewQueueItem]:
    """Create review queue items from ambiguous dedup matches."""
    items = []
    for name_a, name_b, score in ambiguous_pairs:
        item = ReviewQueueItem(
            id=uuid4(),
            run_id=run_id,
            reason=ReviewReason.AMBIGUOUS_DUPLICATE,
            details=f"Fuzzy match score {score:.1f} between '{name_a}' and '{name_b}'",
            candidate_a={"name": name_a},
            candidate_b={"name": name_b},
        )
        items.append(item)
    return items


def generate_review_items_from_validation(
    run_id: UUID,
    company_id: UUID,
    company_name: str,
    reasons: list[ReviewReason],
    details: str = "",
) -> list[ReviewQueueItem]:
    """Create review queue items from QA validation failures."""
    items = []
    for reason in reasons:
        item = ReviewQueueItem(
            id=uuid4(),
            run_id=run_id,
            company_id=company_id,
            reason=reason,
            details=details or f"{reason.value} for {company_name}",
        )
        items.append(item)
    return items
