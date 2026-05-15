# DL Origination Assistant

A production-grade platform for automating direct-lending origination target mining. Accepts investment themes, recommends lender-friendly sub-verticals, discovers and enriches borrower candidates, and exports scored outreach lists.

**316 tests passing** | Python 3.11+ | FastAPI + SQLAlchemy 2.0 async | React 19 + TypeScript frontend | Mock-first local dev

## Documentation

- [Architecture Guide](docs/architecture.md) — Module layout, data flow, pipeline stages, design decisions
- [API Reference](docs/api-reference.md) — Full endpoint documentation with request/response models
- [Frontend Guide](docs/frontend.md) — React UI architecture, dev setup, component map
- [Scoring and Dispositioning](docs/scoring-and-dispositioning.md) — Scoring formula, disposition rules, QA gates, dedup thresholds
- [Operations Guide](docs/operations.md) — Setup, deployment, configuration, extending the platform
- [PitchBook Integration](docs/integrations/pitchbook.md) — PitchBook REST/MCP API reference, tool schemas, data flow

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    React Frontend                          │
│  Dashboard │ RunSetup │ SubVerticals │ Sources │ Pipeline │
│  Companies │ CompanyDetail │ ReviewQueue │ Exports        │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API
┌──────────────────────┴───────────────────────────────────┐
│                    FastAPI Backend                         │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Recommender  │  │    Miner     │  │    AI Layer    │  │
│  │   Engine     │  │    Engine    │  │  (LLM + MCP)   │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                 │                   │           │
│  ┌──────┴─────────────────┴───────────────────┴────────┐ │
│  │              Shared Platform Layer                   │ │
│  │  Config │ Persistence │ Workflow │ Scoring │ Export  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   PostgreSQL       Redis          Storage
```

**Four layers:**
- **React Frontend** — Guided workflow UI with 10 pages. See [Frontend Guide](docs/frontend.md) for the React UI architecture.
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
- **api** — FastAPI on http://localhost:8000 (serves both API and frontend)
- **db** — PostgreSQL on localhost:5432
- **redis** — Redis on localhost:6379
- **worker** — ARQ background job worker

### 3. Open the UI

Navigate to **http://localhost:8000** in your browser. The React frontend provides a guided workflow:

1. **Dashboard** — Create a new run with an investment theme
2. **Sub-Verticals** — Review and confirm AI-generated sub-vertical recommendations
3. **Sources** — Review and confirm recommended data sources + NAICS codes
4. **Pipeline** — Execute the 12-stage mining pipeline with live progress tracking
5. **Companies** — Browse scored companies with sortable/filterable table
6. **Exports** — Download CSV, JSONL, or multi-sheet Excel results

### 4. Alternative: API / CLI usage

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create a run via API
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"theme": "data center capex secular growth"}'

# Or via CLI (requires local pip install)
pip install -e .
dl-origination run create --theme "data center capex secular growth"
```

### 5. Resetting the database

If you encounter schema errors after code updates (e.g., missing columns), reset the database:

```bash
docker compose down -v    # -v removes the PostgreSQL volume
docker compose up
```

`Base.metadata.create_all()` runs on startup and rebuilds all tables from the ORM models.

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
| `SERVE_FRONTEND` | `true` | Serve React frontend from `frontend/dist/` |

### Industry profiles:
- `profiles/generic.yaml` — No industry-specific knowledge
- `profiles/data_center.yaml` — Data center ecosystem hints and source templates

## Workflow Overview

The platform operates in two phases:

**Interactive (Recommender):** User provides a theme → AI generates sub-vertical recommendations → user confirms → AI generates source recommendations → user confirms.

**Automated (Miner, 12 stages):** Name generation → normalization → web enhancement → dispositioning → BizAPI enrichment → PitchBook enrichment → Capital IQ enrichment → cascade expansion → final dedup → QA validation → scoring → export.

See [Architecture Guide](docs/architecture.md) for the detailed stage-by-stage breakdown.

## API Reference

See [API Reference](docs/api-reference.md) for full endpoint documentation.

## Known Limitations

- **PitchBook MCP client** — `MCPPitchBookClient` raises `NotImplementedError` on all methods. Use `PITCHBOOK_PROVIDER=rest` instead. MCP support is a Phase 8 target.
- **Auth boundary** — Stub only. `get_current_user` returns a dummy user. `AUTH_ENABLED=true` raises `NotImplementedError`. No SSO/OAuth2 implementation.
- **S3 storage** — `StorageBackend` interface exists but `S3Storage` is not implemented. Only `LocalStorage` works.
- **Web scraping** — `WebScraperAdapter` and `DirectoryAdapter` have retry logic but no real source URLs are configured. Uses `MockSourceAdapter` by default.
- **ARQ worker** — Requires Redis. When Redis is unavailable, pipeline execution falls back to synchronous inline execution.
- **Frontend polling loop** — If the pipeline crashes without updating run status to `failed`, the Pipeline page continues polling indefinitely. Workaround: refresh the page or start a new run.

## Extending

### Add a new industry profile
Create `profiles/your_industry.yaml` following the structure in `data_center.yaml`.

### Add a new source adapter
1. Create a class extending `app.miner.sources.base_adapter.SourceAdapter`
2. Register it in `app.miner.sources.registry.SourceRegistry`

### Swap PitchBook adapter
1. Set `PITCHBOOK_PROVIDER=rest` in `.env`
2. Set `PITCHBOOK_API_KEY`

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
# All 316 tests (no external services needed)
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

### Frontend Development

See [Frontend Guide](docs/frontend.md) for the React UI architecture.

```bash
cd frontend
npm install
npm run dev         # Vite dev server on http://localhost:5173 (proxies /api to :8000)
npm run build       # Build to frontend/dist/ (served by FastAPI in Docker)
```

### Database Migrations

```bash
# Apply migrations (requires PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic upgrade head

# Generate a new migration after ORM changes
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic revision --autogenerate -m "description"

# Current migrations:
# 0001 — Initial schema (8 tables)
# 0002 — Add enrichment status columns (bizapi_status, ciq_status, bizapi_duns, ciq_entity_id)
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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file
for details.

## Ownership

This repository is developed and maintained by Jamie Anderson in a personal
capacity. It is not produced, sponsored, or maintained on behalf of any
employer, and the views, code, and design decisions represented here are those
of the author alone.

## Company Collaboration

The original author, Jamie Anderson, may from time to time permit Centerbridge
Partners L.P., its affiliates, and other Persons (including without limitation
their partners, employees, advisors, consultants, and any other natural
persons or entities designated by Jamie Anderson) to view, use, edit,
contribute to, or otherwise work with this codebase in separate forks,
branches, cloned repositories, or other derivative or related code bases,
whether internal or external. Any such activity, and any such forks, branches,
clones, or related code bases, do not change, limit, or otherwise affect the
licensing of this repository, which remains licensed under the MIT License.
