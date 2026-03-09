"""Fuzzy deduplication engine using RapidFuzz."""

from rapidfuzz import fuzz

from app.platform.config.defaults import FUZZY_DEDUP_AUTO_MERGE_THRESHOLD, FUZZY_DEDUP_REVIEW_THRESHOLD
from app.platform.utils.logging import get_logger
from app.platform.utils.normalization import normalize_company_name

logger = get_logger("miner.dedup")


class DedupResult:
    def __init__(self):
        self.merged: list[tuple[str, str, float]] = []  # (kept_name, merged_name, score)
        self.review: list[tuple[str, str, float]] = []   # (name_a, name_b, score)


def deduplicate_names(
    names: list[str],
    auto_merge_threshold: int = FUZZY_DEDUP_AUTO_MERGE_THRESHOLD,
    review_threshold: int = FUZZY_DEDUP_REVIEW_THRESHOLD,
) -> DedupResult:
    """Run fuzzy dedup on a list of company names.

    - Score >= auto_merge_threshold → auto-merge (keep first seen)
    - Score >= review_threshold → route to review queue
    - Score < review_threshold → treat as distinct
    """
    result = DedupResult()
    normalized = [(name, normalize_company_name(name)) for name in names]
    seen: list[tuple[str, str]] = []  # (original, normalized)

    for orig, norm in normalized:
        best_match = None
        best_score = 0.0

        for seen_orig, seen_norm in seen:
            score = fuzz.token_sort_ratio(norm, seen_norm)
            if score > best_score:
                best_score = score
                best_match = seen_orig

        if best_match and best_score >= auto_merge_threshold:
            result.merged.append((best_match, orig, best_score))
            logger.debug("dedup_auto_merge", kept=best_match, merged=orig, score=best_score)
        elif best_match and best_score >= review_threshold:
            result.review.append((best_match, orig, best_score))
            logger.debug("dedup_review", name_a=best_match, name_b=orig, score=best_score)
        else:
            seen.append((orig, norm))

    return result
