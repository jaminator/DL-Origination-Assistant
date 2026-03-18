"""Fuzzy deduplication engine using RapidFuzz."""

from rapidfuzz import fuzz
from rapidfuzz.process import cdist

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

    Uses rapidfuzz.process.cdist for vectorized pairwise comparison.

    - Score >= auto_merge_threshold → auto-merge (keep first seen)
    - Score >= review_threshold → route to review queue
    - Score < review_threshold → treat as distinct
    """
    result = DedupResult()
    if len(names) < 2:
        return result

    normalized = [normalize_company_name(name) for name in names]
    matrix = cdist(
        normalized, normalized,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=review_threshold,
    )

    seen: set[int] = set()
    for i in range(len(names)):
        if i in seen:
            continue
        for j in range(i + 1, len(names)):
            if j in seen:
                continue
            score = matrix[i][j]
            if score >= auto_merge_threshold:
                result.merged.append((names[i], names[j], score))
                seen.add(j)
                logger.debug("dedup_auto_merge", kept=names[i], merged=names[j], score=score)
            elif score >= review_threshold:
                result.review.append((names[i], names[j], score))
                logger.debug("dedup_review", name_a=names[i], name_b=names[j], score=score)

    return result
