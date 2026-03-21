> **Historical Record** — This is a point-in-time development audit (2026-03-18,
> Phase 7 closeout). It is not a live status document. For current implementation status,
> see [architecture.md](../architecture.md). For current project context, see [CLAUDE.md](../../CLAUDE.md).

# Post-Build Validation Report

**Date:** 2026-03-18
**Scope:** Full codebase audit, hardening, and gap analysis — updated after Phase 7 closeout
**Phases completed:** 1 (Scaffold), 2 (Engines), 3 (Wire Up), 4 (Docs), 5 (DB + Claude API), 6 (Connectors), 6.5 (BizAPI + Capital IQ), 7 (Frontend UI)

---

## 1. Implementation Status Report

### Summary

The DL Origination Assistant is a **fully functional platform** with a React frontend, complete mock-first pipeline, real database persistence (PostgreSQL via Docker, tested against SQLite in CI), and a hardened Claude API integration. All core business logic runs end-to-end through both the UI and API. The platform is **running in Docker with mock providers** and ready for real connector integration.

| Metric | Value |
|---|---|
| Total tests | 302 passing, 1 skipped |
| Test categories | 16 (integration/db, integration/llm, integration/api-flow, smoke, pipeline, recommendation, enrichment, enrichment/bizapi, enrichment/capitaliq, pitchbook, sources, scoring, validation, workflow, API, utils) |
| Ruff lint violations | 0 (clean) |
| Python version | 3.11+ |
| Backend modules | 60+ files across 4 packages |
| Frontend pages | 10 React pages + 11 reusable components |
| Pipeline stages | 12 (including BizAPI and Capital IQ enrichment) |
| Enrichment providers | 4 (Web/LLM, BizAPI, PitchBook, Capital IQ) |
| Real Claude API | Validated (complete + complete_json) |
| Alembic migrations | 2 (initial schema + enrichment status columns) |
| DB persistence | All 6 repositories tested against real SQL |
| Docker services | 4 (api + frontend, worker, db, redis) |

### What Works Today

1. **React frontend** — Full guided workflow UI with 10 pages (Dashboard, RunSetup, SubVerticals, Sources, Pipeline, Companies, CompanyDetail, ReviewQueue, Exports, Settings)
2. **Full pipeline execution** with mock providers — theme → sub-verticals → sources → mine → enrich (BizAPI + PitchBook + Capital IQ) → score → export
3. **All 12 miner stages** execute in sequence with checkpoint/resume support
4. **Recommender engine** produces structured sub-vertical and source recommendations via LLM prompts
5. **MockLLMService** with prompt-detection fixtures for subverticals, sources, and web enrichment — full pipeline runs without any API keys
6. **Real Claude API integration** — `ClaudeLLMService` with retry/backoff, auth validation, rate limit handling, structured response parsing
7. **Database persistence** — All 6 repositories (Run, Company, Checkpoint, Recommendation, Review, Export) tested against real SQL
8. **Alembic migrations** — 0001: initial schema (8 tables), 0002: enrichment status columns
9. **Deterministic scoring** with 6 weighted factors and ownership tier bonuses
10. **Fuzzy deduplication** with configurable merge/review thresholds
11. **Dispositioning rules** correctly classify companies as primary/cascade/exclude/watch
12. **QA validation** with 6 gate checks routing failures to review queue
13. **BizAPI enrichment** — Company verification, DUNS, NAICS/SIC codes, firmographics, corporate linkage, with match method cascade and conflict detection
14. **Capital IQ enrichment** — Private-market financials, credit metrics, M&A history, ownership data, with PB-complete skip logic
15. **Cross-source conflict detection** — Revenue/ownership conflicts across BizAPI, PitchBook, Capital IQ route to review queue
16. **Multi-format export** (CSV, JSONL, multi-sheet Excel with outreach, capital structure, and enrichment sources tabs)
17. **REST API** with 20+ endpoints including health, readiness, runs, recommendations, mining, review resolution, exports, checkpoints, connectors
18. **API happy-path integration test** — create run → recommend → confirm (SQLite-backed, real endpoints)
19. **CLI** with full command set (requires DB for most operations)
20. **Docker Compose** stack with 4 services — API serves both backend and frontend
21. **Portable ORM** — GUID TypeDecorator works on both PostgreSQL (native UUID) and SQLite (String)
22. **Frontend served from FastAPI** — SPA catch-all route, static file serving, Vite proxy for dev

### What Doesn't Work Yet

1. **Real PitchBook integration** — `MCPPitchBookClient` methods raise `NotImplementedError`
2. **Authentication** — Stub only; no SSO/OAuth2 implementation
3. **S3 storage** — Interface defined but not implemented
4. **Web scraping** — Adapter logic exists but no real source URLs are configured
5. **Full API execute test** — Skipped (environment issue, not code)

### What Was Fixed in Phase 7

1. **MockLLMService source data** — Added prompt-detection fixtures for source discovery (4 sources + 2 NAICS codes) so the Generate Sources button returns data
2. **Config persistence** — `confirm-subverticals` now saves `selected_subverticals` to the run config in the database
3. **Worker startup crash** — Removed `asyncio.run()` wrapping `arq run_worker` (it runs its own event loop)
4. **Missing DB columns** — Added migration 0002 for `bizapi_status`, `ciq_status`, `bizapi_duns`, `ciq_entity_id` on companies table (ORM had them, DB didn't)
5. **SPA routing** — Added catch-all route so React Router paths don't return 404

---

## 2. Gap Analysis vs Approved Plan

### Phase 1 — Scaffold the Platform: **100% Complete**

All items delivered.

### Phase 2 — Implement the Engines: **98% Complete**

| Planned Item | Status | Gap |
|---|---|---|
| LLM service abstraction | **Done** | Mock + real Claude both working |
| ClaudeLLMService | **Done** | Retry/backoff, auth, rate limits, error handling, tested |
| MCP manager | Done | Registry works; no real connectors registered |
| AI confidence framework | Done | Full AIProvenance model with auto-accept logic |
| Prompt templates | Done | Theme analysis, source discovery, web enrichment |
| All other engine items | Done | See previous report |
| PitchBook MCP client | **Stub** | Methods are `pass` — Phase 6 target |

### Phase 3 — Wire Up End-to-End: **98% Complete**

| Planned Item | Status | Gap |
|---|---|---|
| API endpoints (all routes) | Done | 15+ endpoints wired |
| CLI commands | Done | All command groups implemented |
| Integration tests | **Done** | 49 integration tests (DB + LLM + API flow) |
| API happy-path test | **Done** | create → recommend → confirm, SQLite-backed |
| Unit tests | Done | 200 tests total |

**Remaining gap:** Full execute-through-export API test is skipped due to broken system `cryptography` package (blocks Redis/ARQ import chain). This is an environment issue, not code.

### Phase 4 — Documentation: **100% Complete**

All documents delivered and updated with Phase 5 status.

### Phase 5 — Database Integration & Real LLM: **95% Complete**

| Goal | Status | Notes |
|---|---|---|
| Generate Alembic migration | **Done** | `0001_initial_schema.py` — 8 tables |
| Test against real PostgreSQL | **Deferred** | Docker not available; SQLite validates same code paths |
| Repository integration tests | **Done** | 21 tests against SQLite: full CRUD lifecycle |
| ClaudeLLMService hardened | **Done** | Retry, timeout, auth, rate limit, response parsing |
| Real Claude API validated | **Done** | `complete()` and `complete_json()` both verified live |
| API integration test | **Done** | 10 tests (9 pass, 1 env-skip) |
| Failure handling tested | **Done** | 18 tests: missing key, 401, 429, 400, 500, 503, timeout, connection, malformed |

**Phase 5 remaining item:** Apply migration to real PostgreSQL and run integration tests against it (requires Docker).

---

## 3. Bugs and Issues

### Fixed During Hardening (Phases 4.5 + 5)

| # | Category | Issue | Fix |
|---|---|---|---|
| 1 | **Build** | Dockerfile missing `COPY app/ app/` | Added before `pip install` |
| 2 | **Lint** | 84 ruff violations | All fixed |
| 3 | **Architecture** | `app/main.py` E402 violations | Refactored to `create_app()` factory |
| 4 | **Compatibility** | Enums used `(str, Enum)` not `StrEnum` | Migrated all 11 |
| 5 | **Types** | Wrong imports in `research.py` | Fixed to `collections.abc` |
| 6 | **Tests** | Smoke test `init_db` patch wrong module | Fixed |
| 7 | **Config** | Default model ID `claude-sonnet-4-5-20250514` doesn't exist | Updated to `claude-sonnet-4-6` |
| 8 | **DB** | `UUID(as_uuid=False)` PostgreSQL-only | Created `GUID` TypeDecorator |
| 9 | **DB** | Module-level engine creation (not configurable) | Lazy init + `configure_engine()` |
| 10 | **Alembic** | `env.py` didn't support `DATABASE_URL` override | Added env var support |
| 11 | **Alembic** | Missing `script.py.mako` template | Created |
| 12 | **LLM** | `ClaudeLLMService` had no error handling | Full retry/backoff/typed exceptions |

### Known Issues (Remaining)

| # | Severity | Issue | Impact | Phase to Fix |
|---|---|---|---|---|
| 1 | **Medium** | `MCPPitchBookClient` methods raise `NotImplementedError` | Cannot use `PITCHBOOK_PROVIDER=mcp` | Phase 8 |
| 2 | **Low** | CLI commands crash with connection error if no DB available | Expected; documented | Deferred |
| 3 | **Low** | `revenue_ceiling` and `cascade_anchor_threshold` same default (1000.0) | No cascade anchors by default | Deferred |
| 4 | **Low** | `create_all()` doesn't add columns to existing tables | Must reset DB (`docker compose down -v`) after ORM changes | Documented |
| 5 | **Info** | Export format parameter not validated | Silently produces all formats | Deferred |
| 6 | **Info** | Frontend polling continues indefinitely if pipeline crashes without updating run status | Requires page refresh or new run | Deferred |

---

## 4. Fixes Applied in Phase 5

### Database Layer
- Created `GUID` TypeDecorator for PostgreSQL/SQLite portability
- Made database engine configurable with lazy initialization
- Added `configure_engine()` for test-time engine replacement
- Created initial Alembic migration (`0001_initial_schema`) with all 8 tables
- Fixed Alembic `env.py` to support `DATABASE_URL` env var override
- Added missing `script.py.mako` template

### Claude API Integration
- Replaced stub `ClaudeLLMService` with hardened implementation
- Added typed exception hierarchy: `LLMError`, `LLMAuthError`, `LLMRateLimitError`, `LLMTimeoutError`, `LLMResponseError`
- Added retry with exponential backoff (3 attempts) for timeouts, 5xx, rate limits
- Added persistent httpx client with connection pooling
- Added auth validation on construction
- Added JSON response parsing with markdown code-block stripping
- Fixed default model ID from nonexistent `claude-sonnet-4-5-20250514` to `claude-sonnet-4-6`
- Validated real API: `complete()` and `complete_json()` both working

### Tests Added
- 21 database integration tests (all repositories, CRUD, cross-repo workflow)
- 18 Claude LLM service tests (auth, timeout, retry, rate limit, malformed response)
- 10 API happy-path integration tests (create run, recommend, confirm, health)
- Total: 152 → 200 tests

### Documentation
- Updated test counts everywhere (152 → 200)
- Added test category table
- Added migration instructions
- Updated README with local setup, migration, and Claude API sections
- Updated `.env.example` with SQLite and localhost alternatives
- Added `aiosqlite` to dev dependencies

---

## 5. Prioritized Next-Step Build Plan

### Phase 7: Frontend UI — **Complete** (2026-03-18)

| Item | Status | Notes |
|---|---|---|
| React frontend scaffold | **Done** | React 19 + TypeScript + Vite, Radix UI + Tailwind CSS 4 |
| Dashboard page | **Done** | Run list with create-new-run flow |
| RunSetup page | **Done** | Theme + config input form |
| SubVerticals page | **Done** | AI recommendation cards with confirm/reject |
| Sources page | **Done** | Source + NAICS recommendation table with confirm |
| Pipeline page | **Done** | 12-stage execution with live progress polling (2s/5s intervals) |
| Companies page | **Done** | TanStack Table with sorting, filtering, score bars |
| CompanyDetail page | **Done** | Single company deep-dive with all enrichment data |
| ReviewQueue page | **Done** | Review items with resolve actions |
| Exports page | **Done** | Download CSV/JSONL/Excel exports |
| Settings page | **Done** | Connector status display |
| Frontend served from FastAPI | **Done** | StaticFiles mount + SPA catch-all route |
| Docker integration | **Done** | `frontend/dist` volume mount, `SERVE_FRONTEND=true` |
| MockLLMService source fixtures | **Done** | Prompt detection returns 4 sources + 2 NAICS codes |
| Config persistence fix | **Done** | `confirm-subverticals` saves `selected_subverticals` to DB |
| Worker startup fix | **Done** | Removed `asyncio.run()` wrapping ARQ worker |
| Migration 0002 | **Done** | Added 4 enrichment status columns to companies table |

### Phase 6: Real Connectors & Pipeline Hardening — Complete

| Item | Status | Notes |
|---|---|---|
| Implement `MCPPitchBookClient` | **Parked** | PitchBook MCP is Claude Chat only; using REST API route instead |
| Add retry/circuit-breaker to external calls | **Done** | WebScraperAdapter, DirectoryAdapter — 3 retries with exponential backoff |
| Configure `WebScraperAdapter` with real URLs | **Done** | Updated data_center.yaml with specific paths and CSS selectors |
| Source registry adapter routing | **Done** | Proper dispatch: WebScraper for journals/rankings, DirectoryAdapter for directories, NAICSAdapter for NAICS |
| Test cascade expansion with real PitchBook | **Blocked** | Awaiting PitchBook API key |
| Verify checkpoint/resume | **Done** | 3 tests: resume from checkpoint, resume without checkpoint, save/load round-trip |
| Add request/response logging | **Done** | Structured logging for all connectors: web scraper, directory, PitchBook REST |
| Fix API integration test failures | **Done** | Tests now force mock LLM regardless of `.env` settings |

### Phase 6: Remaining (Blocked on PitchBook API Key)

1. **Wire up `PitchBookRESTClient`** with real API key and validate
2. **Test cascade expansion** with real competitor data
3. **Validate PostgreSQL** via Docker Compose (instructions provided for user's Windows machine)

### Phase 8: Production Deployment & Auth

- Implement auth boundary (SSO/OAuth2)
- Implement `S3Storage` backend
- Add Prometheus metrics endpoint
- Production Docker Compose overlay
- CI/CD pipeline
- Security audit
- Load testing
- Wire up real PitchBook REST API (requires API key)
- Wire up real BizAPI (requires sandbox credentials)
- Wire up real Capital IQ (requires API documentation + key)

---

## 6. Phase 6 Progress Assessment

### Validation Results (2026-03-09)

| Check | Result |
|---|---|
| API integration tests fixed | PASS — 9/9 pass, force mock LLM in test fixture |
| WebScraperAdapter retry logic | PASS — Retries on 503, 429, timeout with backoff |
| DirectoryAdapter retry logic | PASS — Same retry pattern as web scraper |
| Source registry proper routing | PASS — WebScraper, Directory, NAICS adapters correctly dispatched |
| Checkpoint save/load round-trip | PASS — Data survives save → load cycle |
| Resume from checkpoint | PASS — Skips completed stages, runs remaining |
| Resume without checkpoint | PASS — Runs full 10-stage pipeline |
| Request/response logging | PASS — All connectors log start, complete, and errors |
| Full test suite | PASS — 303/303 pass |

### Changes Made

**Code changes:**
- `app/miner/sources/web_scraper.py` — Added retry with exponential backoff (3 attempts, retryable status codes: 429/500/502/503/504)
- `app/miner/sources/directory_adapter.py` — Same retry pattern, extracted `_fetch_page` method
- `app/miner/sources/registry.py` — Proper adapter routing: WebScraper for journals/rankings, DirectoryAdapter for directories, NAICSAdapter for NAICS sources
- `app/miner/pitchbook/rest_client.py` — Enhanced request/response logging with item counts
- `tests/test_integration/test_api_flow.py` — Force `LLM_PROVIDER=mock` in test fixture
- `profiles/data_center.yaml` — Updated with specific URLs, CSS selectors, and member selectors

**Tests added (37 new, 200 → 237):**
- 7 web scraper retry tests (503, 429, timeout, exhausted retries, Retry-After header)
- 2 directory adapter retry tests (500 retry, exhausted retries)
- 3 checkpoint/resume tests (resume from checkpoint, resume full, save/load round-trip)

### Phase 6 Remaining Blockers

1. **PitchBook API key** — REST client is fully implemented; just needs a key to test against real API
2. **PostgreSQL validation** — Docker Compose ready; user needs to run `docker compose up db` and `alembic upgrade head` on their Windows machine

---

## 7. Phase 6.5 — BizAPI + Capital IQ Enrichment Integration

### Summary

Added two new enrichment providers to the pipeline — NAICS BizAPI (company verification and firmographics) and S&P Capital IQ (private-market financials). The pipeline expanded from 10 to 12 stages. Both providers follow the same mock-first architecture as PitchBook.

### What Was Added

**New modules:**
- `app/miner/enrichment/bizapi/` — BizAPIAdapter ABC, REST client (Basic Auth, 3 req/s rate limit, retry/backoff), mock client, normalizers
- `app/miner/enrichment/capitaliq/` — CapitalIQAdapter ABC, REST client (API key auth, retry/backoff), mock client, normalizers

**New pipeline stages:**
- Stage 5: `BIZAPI_ENRICHMENT` — After dispositioning, before PitchBook. Verifies company identity, provides DUNS, NAICS/SIC codes, verified address, employee count, sales volume, corporate linkage
- Stage 7: `CAPITALIQ_ENRICHMENT` — After PitchBook, before cascade expansion. Provides revenue, EBITDA, debt, credit metrics, ownership, M&A history. Skips companies where PitchBook already provided complete data

**New data model fields:**
- 14 BizAPI fields on CompanyRecord (duns, match method/confidence, NAICS/SIC, year started, employee count, sales volume, verified name/address, corporate linkage)
- 10 Capital IQ fields on CompanyRecord (entity ID, revenue, EBITDA, total/net debt, ownership type, investors, M&A history, credit metrics)
- 2 new status enums: `BizAPIStatus`, `CapitalIQStatus`
- 2 new review reasons: `WEAK_ENRICHMENT_MATCH`, `CONFLICTING_ENRICHMENT`

**Cross-source conflict detection:**
- Revenue conflict: flags review when new revenue diverges >50% from existing estimate
- Ownership conflict: flags review when Capital IQ and PitchBook disagree on ownership tier
- Source priority hierarchy: CIQ > PB > BizAPI > Web for canonical field updates

**Export updates:**
- CSV includes BizAPI and Capital IQ columns
- Excel adds "Enrichment Sources" sheet (4 sheets total)

**Health checks:**
- `/readiness` endpoint reports BizAPI and Capital IQ availability

**Tests added (66 new, 237 → 303):**
- BizAPI: REST client, mock client, normalizers, match method selection
- Capital IQ: REST client, mock client, normalizers
- Pipeline integration tests for new enrichment stages
- Conflict detection and review queue generation tests

### Settings Added

| Variable | Default | Description |
|---|---|---|
| `BIZAPI_PROVIDER` | `mock` | `mock` or `rest` |
| `BIZAPI_USERNAME` | (empty) | Basic Auth username |
| `BIZAPI_PASSWORD` | (empty) | Basic Auth password |
| `BIZAPI_USE_SANDBOX` | `true` | Use sandbox endpoint |
| `CAPITALIQ_PROVIDER` | `mock` | `mock` or `rest` |
| `CAPITALIQ_API_URL` | (empty) | API base URL |
| `CAPITALIQ_API_KEY` | (empty) | API key |
| `CAPITALIQ_SKIP_IF_PB_COMPLETE` | `true` | Skip when PB data is complete |

### Remaining Blockers

1. **BizAPI credentials** — REST client is fully implemented; needs sandbox credentials to test against real API
2. **Capital IQ API documentation** — REST client structure based on expected API; exact endpoints/schemas need confirmation from CIQ docs
3. **PitchBook API key** — Still needed from Phase 6

---

## 8. Phase 7 — Frontend UI

### Summary

Added a complete React 19 frontend with TypeScript, served from FastAPI in Docker. The UI provides a guided workflow for the full origination process — from theme input through pipeline execution to export download. All mock providers are wired end-to-end, so the full workflow runs without any external API keys.

### What Was Added

**Frontend scaffold:**
- React 19 + TypeScript 5.9 + Vite 6.4
- Tailwind CSS 4 for styling
- Radix UI primitives for accessible components (checkbox, dialog, dropdown, progress, select, tabs, tooltip)
- TanStack Query 5 for server state management with smart polling
- TanStack Table 8 for sortable/filterable data tables
- Zustand 5 for client state
- React Router 7 for SPA routing
- Lucide React for icons

**10 pages:**
- `Dashboard.tsx` — Run list with create-new-run button
- `RunSetup.tsx` — Theme + configuration input form
- `SubVerticals.tsx` — AI-generated sub-vertical recommendation cards with confirm/reject
- `Sources.tsx` — Source + NAICS code recommendation table with confirm
- `Pipeline.tsx` — 12-stage pipeline execution with live progress polling (2s run status, 5s checkpoints)
- `Companies.tsx` — Scored company table with sorting, filtering, score bars
- `CompanyDetail.tsx` — Single company deep-dive with all enrichment data
- `ReviewQueue.tsx` — Review items with resolve actions
- `Exports.tsx` — Download CSV/JSONL/Excel exports
- `Settings.tsx` — Connector status display

**Layout components:**
- `AppShell.tsx` — Sidebar + content layout
- `TopBar.tsx` — Header with run context
- `WorkflowRail.tsx` — Step-by-step workflow navigation

**Reusable UI components:**
- Badge, Button, Card, Drawer, EmptyState, ScoreBar, Spinner, Toast

**Backend integration:**
- `frontend/src/lib/api.ts` — Complete REST API client covering all endpoints
- `frontend/src/types/api.ts` — TypeScript types matching backend response schemas
- Vite dev server proxies `/api` to FastAPI backend

**Docker integration:**
- `frontend/dist/` volume-mounted into API container
- `SERVE_FRONTEND=true` env var enables static file serving
- SPA catch-all route returns `index.html` for React Router paths
- FastAPI `StaticFiles` mount serves built assets

### Bug Fixes During Phase 7

| # | Issue | Fix |
|---|---|---|
| 1 | SubVerticals page blank screen | Fixed data shape mismatch between API response and frontend expectations; added null safety with optional chaining |
| 2 | SPA routing returned 404 | Added catch-all route in FastAPI to serve `index.html` for non-API paths |
| 3 | Worker startup crash | Removed `asyncio.run()` wrapping `arq run_worker` — ARQ runs its own event loop |
| 4 | Generate Sources returned empty | Added source discovery prompt detection in MockLLMService with 4 mock sources + 2 NAICS codes |
| 5 | Config not persisted after confirm | Fixed `confirm-subverticals` endpoint to save `selected_subverticals` to run config in DB |
| 6 | Pipeline crash: missing DB columns | Created migration 0002 adding `bizapi_status`, `ciq_status`, `bizapi_duns`, `ciq_entity_id` to companies table |

### Validation Results (2026-03-18)

| Check | Result |
|---|---|
| Full test suite | PASS — 302/302 pass, 1 skipped |
| Ruff lint | PASS — 0 violations |
| Docker Compose full stack | PASS — All 4 services start and communicate |
| Frontend workflow (mock mode) | PASS — Create run → recommend subverticals → confirm → recommend sources → confirm → execute pipeline → view companies → export |
| Pipeline execution (mock mode) | PASS — All 12 stages complete, 14 companies generated and scored |
| Database schema (PostgreSQL) | PASS — All columns present after `docker compose down -v && up` |
