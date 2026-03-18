# DL Origination Assistant

A production-grade platform for automating direct-lending origination target mining. Accepts investment themes, recommends lender-friendly sub-verticals, discovers and enriches borrower candidates, and exports scored outreach lists.

**303 tests passing** | Python 3.11+ | FastAPI + SQLAlchemy 2.0 async | Mock-first local dev

## Documentation

- [Architecture Guide](docs/architecture.md) — Module layout, data flow, pipeline stages, design decisions
- [Scoring and Dispositioning](docs/scoring-and-dispositioning.md) — Scoring formula, disposition rules, QA gates, dedup thresholds
- [Operations Guide](docs/operations.md) — Setup, deployment, configuration, extending the platform
- [PitchBook Integration Contract](docs/pitchbook_mcp_contract.md) — PitchBook REST/MCP API reference, tool schemas, data flow
- [PitchBook MCP Discovery](docs/pitchbook_mcp_discovery.md) — MCP server discovery report and setup instructions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Recommender  │  │    Miner     │  │    AI Layer    │ │
│  │   Engine     │  │    Engine    │  │  (LLM + MCP)   │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                 │                   │          │
│  ┌──────┴─────────────────┴───────────────────┴────────┐ │
│  │              Shared Platform Layer                   │ │
│  │  Config │ Persistence │ Workflow │ Scoring │ Export  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   PostgreSQL       Redis          Storage
```

**Three engines:**
- **Recommender Engine** — Theme → sub-vertical ranking → source recommendations
- **Miner Engine** — Source extraction → multi-source enrichment (BizAPI, PitchBook, Capital IQ) → dedup → scoring → export
- **AI/MCP Layer** — LLM service abstraction, MCP connectors, prompt library, confidence tracking

## Quick Start (Local Development)

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for CLI outside Docker)

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env if you want to use real LLM (set LLM_PROVIDER=claude, LLM_API_KEY=...)
# Default: LLM_PROVIDER=mock (no API key needed)
```

### 2. Start services

```bash
docker compose up --build
```

This starts:
- **api** — FastAPI on http://localhost:8000
- **db** — PostgreSQL on localhost:5432
- **redis** — Redis on localhost:6379
- **worker** — ARQ background job worker

### 3. Verify

```bash
curl http://localhost:8000/api/v1/health
```

### 4. Create a run

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"theme": "data center capex secular growth"}'

# Via CLI (requires local pip install)
pip install -e .
dl-origination run create --theme "data center capex secular growth"
```

### 5. Run the recommendation flow

```bash
# Generate sub-vertical recommendations
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/recommend-subverticals

# List recommendations
curl http://localhost:8000/api/v1/runs/{run_id}/subverticals

# Confirm all
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/confirm-subverticals \
  -H "Content-Type: application/json" \
  -d '{"accept_all": true}'

# Generate source recommendations
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/recommend-sources

# Confirm sources
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/confirm-sources \
  -H "Content-Type: application/json" \
  -d '{"accept_all": true}'
```

### 6. Execute the mining pipeline

```bash
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/execute
```

## Configuration

### Three layers:
1. **Environment variables** (`.env`) — secrets, provider selection, database URLs
2. **YAML profiles** (`profiles/`) — industry-specific defaults, sub-vertical hints, source templates
3. **Per-run config** — theme, geography, revenue ceiling, ownership preferences

### Key environment variables:
| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` or `claude` |
| `LLM_API_KEY` | (empty) | Anthropic API key (when `claude`) |
| `PITCHBOOK_PROVIDER` | `mock` | `mock`, `rest`, or `mcp` |
| `BIZAPI_PROVIDER` | `mock` | `mock` or `rest` (NAICS BizAPI) |
| `CAPITALIQ_PROVIDER` | `mock` | `mock` or `rest` (S&P Capital IQ) |
| `DATABASE_URL` | (Docker default) | PostgreSQL connection string |
| `AUTH_ENABLED` | `false` | Enable auth boundary |

### Industry profiles:
- `profiles/generic.yaml` — No industry-specific knowledge
- `profiles/data_center.yaml` — Data center ecosystem hints and source templates

## Workflow Stages

### Phase 0-2: Recommendation (interactive)
1. **Theme Intake** — User provides theme + optional constraints
2. **Sub-vertical Recommendation** — AI generates ranked sub-verticals with fit scores
3. **User Confirmation** — Accept/edit/add/remove sub-verticals
4. **Source Recommendation** — AI generates sources + NAICS codes per sub-vertical
5. **User Confirmation** — Accept/deselect/add sources

### Phase 3: Mining (background pipeline, 12 stages)
6. **Name Generation** — Extract companies from confirmed sources
7. **Name Normalization** — Standardize names, fuzzy dedup
8. **Web Enhancement** — AI-assisted enrichment (description, size, geography)
9. **Dispositioning** — Primary / Cascade Anchor / Exclude / Watch
10. **BizAPI Enrichment** — Company verification, DUNS, NAICS/SIC codes, firmographics
11. **PitchBook Enrichment** — Ownership, debt, competitors via REST/MCP
12. **Capital IQ Enrichment** — Private-market financials, credit metrics, M&A history
13. **Cascade Expansion** — Recursive competitor discovery from anchors
14. **Final Dedup** — Cross-source deduplication
15. **QA Validation** — Outreach eligibility gates
16. **Scoring** — Weighted borrower scoring with ownership bonuses
17. **Export** — CSV, JSON, multi-sheet Excel outputs

### Phase 4: Review
- Review queue for ambiguous duplicates, unknown ownership, boundary cases, weak enrichment matches, conflicting enrichment data
- Export downloads

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Liveness probe (DB connectivity) |
| `/api/v1/readiness` | GET | Readiness probe (DB + all connectors) |
| `/api/v1/runs` | POST | Create new run |
| `/api/v1/runs/{id}` | GET | Get run details |
| `/api/v1/runs/{id}/status` | GET | Get run status |
| `/api/v1/runs/{id}/recommend-subverticals` | POST | Generate recommendations |
| `/api/v1/runs/{id}/confirm-subverticals` | POST | Lock selections |
| `/api/v1/runs/{id}/recommend-sources` | POST | Generate source recommendations |
| `/api/v1/runs/{id}/confirm-sources` | POST | Lock source selections |
| `/api/v1/runs/{id}/execute` | POST | Start mining pipeline |
| `/api/v1/runs/{id}/resume` | POST | Resume from checkpoint |
| `/api/v1/runs/{id}/stages/{stage}/rerun` | POST | Re-run single stage |
| `/api/v1/runs/{id}/companies` | GET | List companies |
| `/api/v1/runs/{id}/companies/{company_id}` | GET | Get single company detail |
| `/api/v1/runs/{id}/review-queue` | GET | List review items |
| `/api/v1/runs/{id}/review-queue/{item_id}/resolve` | POST | Resolve a review item |
| `/api/v1/runs/{id}/exports` | POST | Trigger export |
| `/api/v1/runs/{id}/exports` | GET | List exports |
| `/api/v1/runs/{id}/exports/{export_id}/download` | GET | Download export file |
| `/api/v1/runs/{id}/checkpoints` | GET | List pipeline checkpoints |
| `/api/v1/runs/{id}/checkpoints/{checkpoint_id}` | GET | Inspect checkpoint detail |
| `/api/v1/connectors/status` | GET | Connector health report |

## Extending

### Add a new industry profile
Create `profiles/your_industry.yaml` following the structure in `data_center.yaml`.

### Add a new source adapter
1. Create a class extending `app.miner.sources.base_adapter.SourceAdapter`
2. Register it in `app.miner.sources.registry.SourceRegistry`

### Swap PitchBook adapter
1. Set `PITCHBOOK_PROVIDER=rest` (or `mcp`) in `.env`
2. For REST: set `PITCHBOOK_API_KEY`
3. For MCP: set `MCP_PITCHBOOK_URL` and `MCP_PITCHBOOK_TOKEN`

### Enable BizAPI enrichment
1. Set `BIZAPI_PROVIDER=rest` in `.env`
2. Set `BIZAPI_USERNAME` and `BIZAPI_PASSWORD`
3. Optionally set `BIZAPI_USE_SANDBOX=true` for testing

### Enable Capital IQ enrichment
1. Set `CAPITALIQ_PROVIDER=rest` in `.env`
2. Set `CAPITALIQ_API_URL` and `CAPITALIQ_API_KEY`
3. Set `CAPITALIQ_SKIP_IF_PB_COMPLETE=true` to skip when PitchBook data is complete

### Deploy to private cloud
Same Docker images. Change:
- `.env` → secrets manager
- `AUTH_ENABLED=true` + SSO
- PostgreSQL → managed instance
- Redis → managed instance
- `STORAGE_BACKEND=s3`

## Development

### Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

### Running Tests

```bash
# All 303 tests (no external services needed)
pytest tests/ -v

# By category
pytest tests/test_smoke/              # Import, config, schema smoke tests
pytest tests/test_integration/        # DB, LLM service, API flow integration
pytest tests/test_pipeline/           # Full miner pipeline
pytest tests/test_workflow/           # Dedup, dispositioning, review queue
pytest tests/test_enrichment/         # Size estimator, exposure, BizAPI, Capital IQ
pytest tests/test_pitchbook/          # PitchBook REST client tests
pytest tests/test_scoring/            # Company scorer tests
pytest tests/test_validation/         # QA gate checks

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Running Locally (Without Docker)

```bash
# Option A: SQLite (no PostgreSQL needed)
export DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
uvicorn app.main:app --reload

# Option B: Local PostgreSQL
docker compose up db redis    # Start just DB + Redis
export DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination
uvicorn app.main:app --reload
```

### Database Migrations

```bash
# Apply migrations (requires PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic upgrade head

# Generate a new migration after ORM changes
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic revision --autogenerate -m "description"
```

### Lint

```bash
ruff check app/ tests/
```

### Using Real Claude API

```bash
# In .env:
LLM_PROVIDER=claude
LLM_API_KEY=sk-ant-your-key-here
# LLM_MODEL defaults to claude-sonnet-4-6
```

The ClaudeLLMService includes:
- Retry with exponential backoff (3 attempts for timeouts, server errors, rate limits)
- Clear error messages for auth failures, rate limits, malformed responses
- Persistent httpx client with connection pooling
- Structured logging (no secrets leaked)
