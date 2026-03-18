# CLAUDE.md — DL Origination Assistant
## Project Overview
Production FastAPI direct-lending origination platform. Two engines
(Recommender + Miner) share a Platform Layer backed by PostgreSQL
(asyncpg), Redis (ARQ), and an AI Layer (Anthropic Claude + MCP).
Phase 6.5 complete. 303 tests passing. 0 Ruff violations.
## Tech Stack
- Python 3.11+
- FastAPI with create_app() factory + asynccontextmanager lifespan
- SQLAlchemy 2.0 async: Mapped[], mapped_column(), GUID TypeDecorator
  (PostgreSQL-native UUID / SQLite String portable), AsyncSession,
  async_sessionmaker(expire_on_commit=False)
- asyncpg driver → PostgreSQL
- Alembic: 0001_initial_schema.py (8 tables), env.py supports
  DATABASE_URL env var override, run_sync for async engine
- ARQ background jobs + inline async fallback (app/platform/jobs/)
- Pydantic v2: ConfigDict, model_validator, SecretStr, Pydantic Settings
  All enums use StrEnum (migrated from (str, Enum) — do not revert)
- Anthropic Claude SDK (model: claude-sonnet-4-6) + MockLLMService
  Typed exception hierarchy: LLMError, LLMAuthError, LLMRateLimitError,
  LLMTimeoutError, LLMResponseError
- MCP connector registry (app/ai/mcp_manager.py)
- httpx with retry/backoff + connection pooling
- RapidFuzz deduplication (app/miner/dedup.py)
  Thresholds: >= 95 auto-merge, 80-94 → review queue, < 80 distinct
  Scorer: fuzz.token_sort_ratio (DO NOT change to fuzz.ratio)
- structlog structured logging (app/platform/utils/logging.py)
- Ruff: 0 violations. ruff check app/ tests/ is the lint command.
- Typer + Rich CLI (app/cli.py)
- pytest + pytest-asyncio asyncio_mode=auto (303 tests, 16 categories)
- Docker Compose: api, db, redis, worker (4 services)
- Multi-format export: CSV, JSONL, 4-sheet Excel
  (outreach, capital structure, enrichment sources tabs)
## Enrichment Providers (4 total)
Priority order when fields overlap (highest wins):
  1. Capital IQ  — audited financials, credit metrics
  2. PitchBook   — curated deal/ownership data
  3. BizAPI      — verified firmographics, DUNS, NAICS/SIC
  4. Web/LLM     — estimates only
BizAPI:   Basic Auth, 3 req/s rate limit, retry/backoff
          BIZAPI_PROVIDER=mock|rest; sandbox flag
PitchBook: REST API v2 (PITCHBOOK_PROVIDER=mock|rest|mcp)
           MCPPitchBookClient is STUB — all methods raise
           NotImplementedError — do NOT call it in prod
Capital IQ: API key auth, skips if PitchBook data complete
            CAPITALIQ_PROVIDER=mock|rest
## 12-Stage Pipeline (DO NOT reorder)
Stage 1:  name_generation       — sources → RawCompany[]
Stage 2:  name_normalization    — normalize + fuzzy dedup pass 1
Stage 3:  web_enhancement       — LLM WebEnrichmentPrompt
Stage 4:  dispositioning        — PRIMARY|CASCADE_ANCHOR|EXCLUDE|WATCH
Stage 5:  bizapi_enrichment     — DUNS, NAICS/SIC, firmographics
Stage 6:  pitchbook_enrichment  — ownership, debt, competitors
Stage 7:  capitaliq_enrichment  — revenue, EBITDA, credit metrics
Stage 8:  cascade_expansion     — PitchBook competitor discovery
Stage 9:  final_dedup           — fuzzy dedup pass 2 (all companies)
Stage 10: qa_validation         — 6 gate checks → review_required flag
Stage 11: scoring               — 6-factor weighted formula
Stage 12: export                — CSV + JSONL + 4-sheet Excel
## Dispositioning Rules (priority order, first match wins)
1. hq_country NOT IN geography_filter          → EXCLUDE
2. is_public=true AND revenue > $5B            → EXCLUDE
3. revenue > cascade_anchor_threshold ($1B)    → CASCADE_ANCHOR
4. revenue > revenue_ceiling ($1B)             → CASCADE_ANCHOR
5. revenue < $5M                               → EXCLUDE
6. default                                     → PRIMARY
## Scoring Formula (deterministic, 0-100, partial credit for missing data)
Revenue Scale:      weight 20  (sweet spot $50M-$500M → 90 raw)
EBITDA Margin:      weight 15  (>= 20% → 95 raw)
Recurring Revenue:  weight 15  (>= 70% ratio → 95 raw)
Industry Exposure:  weight 20  (high → 95, medium → 65, low → 35)
Ownership Tier:     additive bonus (Tier A +15, Tier B +8, Tier C +0)
Data Completeness:  weight 15  (7 key fields, filled/7 * 100)
## QA Gates (6 checks on PRIMARY companies before scoring)
data_completeness, unknown_ownership, cascade_anchor_bleed,
mega_cap, geography, score_sanity (total_score > 95 = data error)
## Architecture Patterns (DO NOT break these)
- Repository Pattern: ALL DB access through typed repositories in
  app/platform/persistence/repositories.py. Never raw Session in routes.
- Ports & Adapters: SourceAdapter ABC, PitchBookAdapter ABC,
  BizAPIAdapter ABC, CapitalIQAdapter ABC, StorageBackend ABC, LLMService.
  All have mock + real implementations. Resolve through registry/DI only.
- Service Layer: WorkflowOrchestrator is the only entry point into the
  12-stage pipeline. Do not call stage functions directly from routes.
- DI: all FastAPI dependencies in app/platform/api/deps.py only.
- AIProvenance: every LLM-generated field MUST carry an AIProvenance
  record. State machine: pending→auto_accepted→human_accepted/rejected.
- Cross-source conflicts (revenue >50% divergence, ownership disagreement)
  MUST route to review queue, not silently resolve.
## Known Stubs (do not break stub interfaces)
- MCPPitchBookClient: all methods raise NotImplementedError (Phase 7)
- WebScraperAdapter/DirectoryAdapter: retry logic complete, no real URLs
- ARQ worker: config exists, requires Redis to activate
- Auth boundary: get_current_user returns dummy, AUTH_ENABLED flag exists
- S3Storage: interface defined, not implemented
- ResearchOrchestrator: batch/retry framework, no real connectors
## Test Commands
pytest tests/ -v                          # full 303-test suite
pytest tests/test_smoke/                  # import/config smoke
pytest tests/test_integration/            # DB + LLM + API flow (49 tests)
pytest tests/test_pipeline/              # full 12-stage pipeline
pytest tests/test_enrichment/            # BizAPI + Capital IQ enrichment
pytest tests/test_workflow/ -k "dedup"   # dedup/dispositioning
ruff check app/ tests/                   # must return 0 violations
mypy app/ --strict --ignore-missing-imports
## Critical Config Notes
- Default LLM model: claude-sonnet-4-6 (not claude-sonnet-4-5-*)
- GUID TypeDecorator used for all UUID PKs (PostgreSQL + SQLite portable)
- All 11 enums are StrEnum — never revert to (str, Enum)
- expire_on_commit=False is REQUIRED on async_sessionmaker
- LLM_PROVIDER=mock forces MockLLMService in all test fixtures
