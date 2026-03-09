# Architecture Guide

## System Overview

DL Origination Assistant is a FastAPI application with two engines — **Recommender** and **Miner** — sharing a common **Platform Layer**. An **AI Layer** provides LLM and MCP connector abstractions.

```
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Application                       │
│                                                              │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  Recommender   │  │     Miner      │  │   AI Layer     │  │
│  │    Engine      │  │    Engine      │  │ LLM + MCP +    │  │
│  │                │  │  (10 stages)   │  │ Prompt Library  │  │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  │
│          │                   │                    │           │
│  ┌───────┴───────────────────┴────────────────────┴────────┐ │
│  │                  Shared Platform Layer                    │ │
│  │                                                          │ │
│  │  Config   │ Models │ Persistence │ Workflow │ Scoring    │ │
│  │  Exports  │ Review │ Validation  │ Jobs    │ Utils      │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    PostgreSQL      Redis         Storage
    (asyncpg)       (ARQ)        (local/S3)
```

## Module Layout

```
app/
├── main.py                          # FastAPI app factory + lifespan
├── cli.py                           # Typer CLI entrypoint
│
├── ai/                              # AI Layer
│   ├── llm_service.py               # LLM abstraction (Claude + Mock)
│   ├── mcp_manager.py               # MCP connector registry
│   ├── confidence.py                # AIProvenance model
│   ├── research.py                  # Research orchestration
│   └── prompts/
│       ├── base.py                  # PromptTemplate base class
│       ├── theme_analysis.py        # ThemeAnalysisPrompt + SourceDiscoveryPrompt
│       └── web_enrichment.py        # WebEnrichmentPrompt
│
├── recommender/                     # Recommender Engine
│   └── engine.py                    # Theme → sub-verticals → sources
│
├── miner/                           # Miner Engine
│   ├── engine.py                    # 10-stage pipeline orchestrator
│   ├── dedup.py                     # RapidFuzz fuzzy deduplication
│   ├── dispositioning.py            # Deterministic disposition rules
│   ├── enrichment/
│   │   ├── web_enricher.py          # LLM-assisted company enrichment
│   │   ├── size_estimator.py        # Revenue/employee estimation
│   │   └── exposure_classifier.py   # Industry exposure intensity
│   ├── sources/
│   │   ├── base_adapter.py          # SourceAdapter ABC
│   │   ├── registry.py              # Adapter routing + mock detection
│   │   ├── mock_adapter.py          # Synthetic companies for local dev
│   │   ├── web_scraper.py           # httpx + BeautifulSoup extractor
│   │   ├── directory_adapter.py     # Association directory scraper
│   │   └── naics_adapter.py         # NAICS code → company seed generator
│   └── pitchbook/
│       ├── adapter.py               # PitchBookAdapter ABC
│       ├── mock_client.py           # Synthetic PitchBook data
│       └── mcp_client.py            # Real PitchBook via MCP (future)
│
└── platform/                        # Shared Platform Layer
    ├── api/                         # FastAPI route modules
    │   ├── deps.py                  # Dependency injection (DB, LLM, MCP)
    │   ├── health.py                # /health, /readiness
    │   ├── runs.py                  # Run CRUD + execute/resume
    │   ├── recommender_routes.py    # Recommendation endpoints
    │   ├── miner_routes.py          # Companies, review queue, stage rerun
    │   ├── exports.py               # Export trigger + download
    │   └── connectors.py            # Connector health report
    ├── config/
    │   ├── settings.py              # Pydantic Settings (env vars)
    │   ├── defaults.py              # Scoring weights, thresholds, QA params
    │   └── loader.py                # YAML profile loader
    ├── models/
    │   ├── enums.py                 # All canonical enums
    │   ├── schemas.py               # Pydantic domain models (CompanyRecord, etc.)
    │   ├── run.py                   # RunConfig model
    │   └── orm.py                   # SQLAlchemy ORM models
    ├── persistence/
    │   ├── database.py              # Async engine + session factory
    │   ├── repositories.py          # Repository pattern (Run, Company, etc.)
    │   └── storage.py               # LocalStorage + StorageBackend ABC
    ├── workflow/
    │   ├── orchestrator.py          # Pipeline orchestrator with DB persistence
    │   └── checkpoint.py            # Checkpoint save/load
    ├── jobs/
    │   ├── worker.py                # ARQ worker + job definitions
    │   └── tasks.py                 # Job enqueue helpers
    ├── scoring/
    │   └── company_scorer.py        # Weighted borrower scoring formula
    ├── validation/
    │   ├── qa_gates.py              # QA gate runner
    │   └── checks.py                # 6 individual validation checks
    ├── exports/
    │   ├── service.py               # ExportService orchestrator
    │   ├── csv_exporter.py          # CSV export
    │   ├── json_exporter.py         # JSONL export
    │   └── excel_exporter.py        # Multi-sheet Excel export
    ├── review/
    │   └── queue.py                 # Review item generation
    └── utils/
        ├── logging.py               # structlog setup
        └── normalization.py         # Company name normalization
```

## Data Flow

### End-to-End Workflow

```
User Input                    Recommender                           Miner
─────────                    ───────────                           ─────
  │                               │                                  │
  │  POST /runs {theme}           │                                  │
  ├──────────────────────────────►│                                  │
  │                               │                                  │
  │  POST /recommend-subverticals │                                  │
  ├──────────────────────────────►│                                  │
  │                        LLM: ThemeAnalysisPrompt                  │
  │                        → SubVerticalRecommendation[]             │
  │◄──────────────────────────────┤                                  │
  │                               │                                  │
  │  POST /confirm-subverticals   │                                  │
  ├──────────────────────────────►│                                  │
  │                               │                                  │
  │  POST /recommend-sources      │                                  │
  ├──────────────────────────────►│                                  │
  │                        LLM: SourceDiscoveryPrompt                │
  │                        → SourceRecommendation[]                  │
  │◄──────────────────────────────┤                                  │
  │                               │                                  │
  │  POST /confirm-sources        │                                  │
  ├──────────────────────────────►│                                  │
  │                               │                                  │
  │  POST /execute                │                                  │
  ├──────────────────────────────────────────────────────────────────►│
  │                                                    10-stage pipeline
  │                                                    (see below)
  │◄─────────────────────────────────────────────────────────────────┤
  │  {companies, review_items, exports}                              │
```

### Miner Pipeline Stages

```
Stage 1: name_generation
  Sources → SourceRegistry → [SourceAdapter] → RawCompany[]
     │
Stage 2: name_normalization
  RawCompany[] → normalize → deduplicate_names() → CompanyRecord[]
  Side effect: review items for ambiguous duplicates
     │
Stage 3: web_enhancement
  CompanyRecord[] → LLM(WebEnrichmentPrompt) → enriched fields
  (city, state, revenue, ownership, exposure, employees)
     │
Stage 4: dispositioning
  CompanyRecord[] → assign_disposition() → PRIMARY | CASCADE_ANCHOR | EXCLUDE
     │
Stage 5: pitchbook_enrichment
  Primary + Anchor → PitchBookAdapter → ownership, debt, competitors
     │
Stage 6: cascade_expansion
  Cascade Anchors → PitchBook competitors → new CompanyRecord[]
     │
Stage 7: final_dedup
  All companies → deduplicate_names() → remove merged, add review items
     │
Stage 8: qa_validation
  Primary companies → run_qa_gates() → 6 checks → flag review_required
     │
Stage 9: scoring
  Eligible companies → score_company() → total_score + components
     │
Stage 10: export
  All companies → ExportService → CSV + JSON + Excel files
```

## Key Design Decisions

### Mock-First Development

All external dependencies have mock implementations:
- `LLM_PROVIDER=mock` → `MockLLMService` with fixture responses
- `PITCHBOOK_PROVIDER=mock` → `MockPitchBookClient` with synthetic data
- `SourceRegistry` auto-detects mock mode → `MockSourceAdapter`

The full pipeline runs end-to-end without any API keys or external services.

### Inline Execution Fallback

When Redis/ARQ is unavailable (common in local dev), API endpoints fall back to synchronous inline execution:

```python
job_id = await enqueue_pipeline(run_id)
if job_id:
    return {"status": "accepted", "job_id": job_id}
# Fallback: run inline
result = await orchestrator.run_pipeline(run_id, miner_engine=miner)
return {"status": "completed", "result": result}
```

### AI Provenance Tracking

Every AI-generated field carries an `AIProvenance` record:
- `ai_generated: bool` — is this value from AI?
- `model_source: str` — which model class produced it
- `prompt_template_id: str` — which prompt was used
- `prompt_template_version: str` — version of the prompt
- `confidence_score: float` — model's self-reported confidence
- `acceptance_status: str` — pending / auto_accepted / human_accepted / human_rejected

### Repository Pattern

All database access goes through typed repositories:
- `RunRepository` — run lifecycle
- `CompanyRepository` — company CRUD with run-scoped queries
- `CheckpointRepository` — pipeline checkpoint management
- `RecommendationRepository` — sub-vertical and source recommendations
- `ReviewRepository` — review queue items
- `ExportRepository` — export manifest tracking

### Checkpoint + Resume

The `WorkflowOrchestrator` saves a checkpoint after each successful stage. On failure, it persists partial results. Resume picks up from the last completed stage:

```python
# Resume from last checkpoint
checkpoint = await checkpoint_repo.get_latest(run_id)
start_from = WorkflowStage(checkpoint.stage)
await miner.execute_pipeline(run_id, config, start_from=start_from)
```

## Configuration Hierarchy

```
Priority (highest → lowest):
1. Per-run config (POST /runs body)
2. Environment variables (.env / settings.py)
3. YAML profile defaults (profiles/*.yaml)
4. Hardcoded defaults (defaults.py)
```

## Test Architecture

```
tests/
├── test_pipeline/           # Full pipeline + orchestrator integration
├── test_recommendation/     # Recommender engine unit tests
├── test_enrichment/         # Size estimator, exposure classifier, web enricher
├── test_sources/            # NAICS, mock, web scraper adapter tests
├── test_scoring/            # Company scorer unit tests
├── test_validation/         # QA check unit tests
├── test_workflow/           # Dedup, dispositioning, review queue tests
├── test_api/                # FastAPI endpoint tests (TestClient)
├── test_utils/              # Normalization tests
└── conftest.py              # Shared fixtures
```

All tests run with `pytest tests/ -v` — no external services required.
