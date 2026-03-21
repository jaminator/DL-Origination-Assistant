# Scoring and Dispositioning Reference

## Dispositioning Rules

Dispositioning assigns each company a classification that determines its role in the pipeline. Rules are applied in priority order — the first match wins.

### Disposition Categories

| Disposition | Meaning | Outreach Eligible | Scored |
|---|---|---|---|
| `primary` | Core lending target within parameters | Yes (if QA passes) | Yes |
| `cascade_anchor` | Too large for direct lending, but useful for competitor discovery | No (by default) | Yes |
| `exclude` | Hard fail on geography, size, or public mega-cap | No | No |
| `watch` | Boundary case — configurable treatment | Depends on config | Yes |

### Rule Evaluation Order

```
1. Geography check
   IF hq_country NOT IN geography_filter → EXCLUDE

2. Public mega-cap check
   IF is_public = true AND revenue > $5B → EXCLUDE

3. Revenue above cascade anchor threshold (default $1B)
   IF revenue > cascade_anchor_threshold → CASCADE_ANCHOR

4. Revenue above revenue ceiling (default $1B)
   IF revenue > revenue_ceiling → CASCADE_ANCHOR

5. Revenue below floor
   IF revenue < $5M → EXCLUDE

6. Boundary zone (when boundary_treatment = "watch")
   IF revenue $5M-$10M (near floor) → WATCH
   IF revenue > 90% of cascade_anchor_threshold (near ceiling) → WATCH

7. Default → PRIMARY
```

**Key design choice**: The mega-cap check runs *before* cascade anchor. Public companies with revenue > $5B are never useful as cascade anchors because their competitor sets are too broad and well-known.

### Configurable Parameters

| Parameter | Default | Per-Run Override |
|---|---|---|
| `geography_filter` | `["US"]` | `config.geography_filter` |
| `revenue_ceiling` | $1,000M ($1B) | `config.revenue_ceiling` |
| `cascade_anchor_threshold` | $1,000M | `config.cascade_anchor_threshold` |
| `boundary_treatment` | `"watch"` | `config.boundary_treatment` |
| `include_cascade_anchors_in_outreach` | `false` | `config.include_cascade_anchors_in_outreach` |

---

## Company Scoring Formula

Scoring is **deterministic** — given the same inputs, always returns the same score. Missing data receives partial credit (never zero, never max).

### Score Components

Total score = sum of weighted components, capped at [0, 100].

| Component | Weight | Raw Score Range | Source |
|---|---|---|---|
| Revenue Scale | 20 | 0-100 | `revenue_estimate` |
| EBITDA Margin | 15 | 0-100 | `ebitda_estimate / revenue_estimate` |
| Recurring Revenue | 15 | 0-100 | `recurring_revenue_estimate / revenue_estimate` |
| Industry Exposure | 20 | 0-100 | `industry_exposure_intensity` |
| Ownership Tier | 15 | 0-15 (bonus) | `ownership_tier` |
| Data Completeness | 15 | 0-100 | Key field fill rate |

### Revenue Scale Scoring

Revenue sweet spot is $50M-$500M (core direct lending range).

| Revenue Range | Raw Score |
|---|---|
| Missing / null | 25 (partial credit) |
| Under $10M | 20 |
| $10M - $50M | 50 |
| $50M - $500M | 90 (sweet spot) |
| $500M - $1B | 70 |
| Over $1B | 40 |

### EBITDA Margin Scoring

| Margin | Raw Score |
|---|---|
| Missing data | 30 (partial credit) |
| >= 20% | 95 |
| >= 15% | 85 |
| >= 10% | 70 |
| >= 5% | 50 |
| < 5% | 30 |

### Recurring Revenue Scoring

| Recurring / Revenue Ratio | Raw Score |
|---|---|
| Missing data | 25 (partial credit) |
| >= 70% | 95 |
| >= 50% | 80 |
| >= 30% | 60 |
| < 30% | 35 |

### Industry Exposure Scoring

| Intensity | Raw Score |
|---|---|
| `high` | 95 |
| `medium` | 65 |
| `low` | 35 |
| Missing / unknown | 30 |

### Ownership Tier Bonus

Additive bonus — not scaled by weight. Reflects direct-lending preference for founder-owned businesses.

| Tier | Typical Ownership | Bonus |
|---|---|---|
| Tier A | Founder/family-owned, privately held | +15 |
| Tier B | Family office-backed, VC-backed, growth equity | +8 |
| Tier C | PE/sponsor-backed | +0 |
| Unknown | Ownership not determined | +0 |

**Rationale**: Direct lenders typically seek founder/family-owned businesses (Tier A) because they:
- Have longer hold periods and aligned interests
- Often need first-lien capital for growth (not leveraged recaps)
- Represent de novo origination opportunities (vs. refinancing PE deals)

### Data Completeness

Measures how many key fields are populated:
- `canonical_name`
- `hq_state`
- `subvertical_tags` (non-empty)
- `industry_exposure_descriptor`
- `revenue_estimate`
- `ownership_tier` (not `unknown`)
- `website`

Score = (filled / 7) * 100

### Example Scoring

A well-enriched middle-market electrical contractor:

```
Revenue: $150M → scale raw: 90 → weighted: 90 * 20/100 = 18.0
EBITDA margin: 18% → raw: 85 → weighted: 85 * 15/100 = 12.75
Recurring: 40% → raw: 60 → weighted: 60 * 15/100 = 9.0
Exposure: high → raw: 95 → weighted: 95 * 20/100 = 19.0
Ownership: Tier A → bonus: 15.0
Completeness: 7/7 → raw: 100 → weighted: 100 * 15/100 = 15.0

Total = 18.0 + 12.75 + 9.0 + 19.0 + 15.0 + 15.0 = 88.75
```

---

## QA Validation Gates

Six checks run on all `PRIMARY` companies before scoring. Failures flag `review_required = true`.

| Check | What It Validates | Failure Condition |
|---|---|---|
| `data_completeness` | Key fields populated | < 60% of QA_REQUIRED_FIELDS filled |
| `unknown_ownership` | Ownership determined | `ownership_tier = unknown` AND `eligible_for_outreach = true` |
| `cascade_anchor_bleed` | Anchors excluded from outreach | `disposition = cascade_anchor` AND `eligible_for_outreach = true` |
| `mega_cap` | No public mega-caps in primary | `is_public = true` AND `revenue > $5B` AND `disposition = primary` |
| `geography` | Geography compliant | `hq_country` not in geography filter |
| `score_sanity` | Score in reasonable range | `total_score > 95` (likely data error) |

---

## Deduplication

Two-pass deduplication using RapidFuzz:

1. **Name normalization** — strip legal suffixes (LLC, Inc, Corp, etc.), collapse whitespace, lowercase
2. **Pairwise fuzzy matching** — `fuzz.token_sort_ratio` on all pairs

| Score Range | Action |
|---|---|
| >= 95 | Auto-merge (keep first occurrence) |
| 80 - 94 | Send to review queue as `ambiguous_duplicate` |
| < 80 | Distinct — keep both |

Dedup runs twice:
- After Stage 2 (name normalization) — across source extractions
- At Stage 9 (final dedup) — including cascade-expansion additions

---

## Review Queue

Review items are generated automatically from:

1. **Dedup** — ambiguous matches (score 80-94)
2. **QA validation** — any check failure on a primary company
3. **BizAPI enrichment** — weak match confidence (< 0.80), corporate linkage revealing subsidiary relationships
4. **Cross-source conflict** — revenue/ownership data differs >50% between enrichment providers (BizAPI, PitchBook, Capital IQ)

Each item has:
- `reason` — enum: `ambiguous_duplicate`, `unknown_ownership`, `boundary_size`, `weak_enrichment_match`, `conflicting_enrichment`, etc.
- `details` — human-readable description
- `resolution` — set by analyst: `merge`, `keep_both`, `exclude`, `accept`

### Enrichment Source Priority

When multiple enrichment providers return overlapping fields, the highest-priority source wins:

| Priority | Source | Authority |
|----------|--------|-----------|
| 1 (highest) | Capital IQ | Audited financial data |
| 2 | PitchBook | Curated deal data |
| 3 | BizAPI | Verified firmographic data |
| 4 (lowest) | Web enrichment / LLM | Estimates |

Canonical fields (`revenue_estimate`, `ownership_tier`, etc.) always reflect the highest-priority source. Source-specific fields (`bizapi_sales_volume`, `ciq_revenue`, etc.) preserve each provider's raw value.
