# Operations and Deployment Guide

## Local Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for PostgreSQL + Redis)

### Setup

```bash
# Clone and configure
git clone <repo-url>
cd DL-Origination-Assistant
cp .env.example .env

# Default .env runs in full-mock mode (no API keys needed)
```

### Option A: Docker Compose (recommended)

```bash
# Build and start frontend first (if not already built)
cd frontend && npm install && npm run build && cd ..

docker compose up --build
```

Open **http://localhost:8000** in your browser to access the full UI.

This starts 4 services:

| Service | Port | Description |
|---|---|---|
| `api` | 8000 | FastAPI with hot-reload + serves React frontend |
| `worker` | — | ARQ background job worker |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |

Volumes mount `./app`, `./profiles`, `./data`, and `./frontend/dist` for live editing.

**Important:** The `api` service serves the pre-built React frontend from `frontend/dist/`. The `SERVE_FRONTEND=true` environment variable enables this. If you see a blank page, ensure the frontend has been built (`npm run build` in `frontend/`).

#### Resetting the database

If you encounter schema errors (e.g., "column does not exist") after code changes:

```bash
docker compose down -v    # -v removes the PostgreSQL data volume
docker compose up
```

`Base.metadata.create_all()` runs on startup and recreates all tables. Note: this destroys all existing data.

### Option B: Local Python + Docker services

```bash
# Start only infrastructure
docker compose up db redis

# Install package
pip install -e ".[dev]"

# Point at local infrastructure
export DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination
export REDIS_URL=redis://localhost:6379/0

# Run API
uvicorn app.main:app --reload

# Run worker (separate terminal)
python -m app.platform.jobs.worker
```

### Option C: Fully local (no Docker)

The API will work without PostgreSQL or Redis by using SQLite and inline execution. Set:

```bash
export DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
# Redis is optional — pipeline runs inline when unavailable
```

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific module
pytest tests/test_pipeline/ -v
```

All 316 tests run with mock providers — no external services required.

> **Note:** The skipped `test_full_workflow_through_execute` test is an environment issue
> (broken system `cryptography` lib blocking Redis/ARQ import chain), not a code defect.

### Test Categories

| Category | Directory | What It Tests |
|---|---|---|
| Smoke | `tests/test_smoke/` | Imports, config, schemas, exports, scoring |
| Integration | `tests/test_integration/` | Real SQL (SQLite), ClaudeLLMService, API workflow |
| Pipeline | `tests/test_pipeline/` | Full miner pipeline with mocks |
| Recommendation | `tests/test_recommendation/` | Recommender engine |
| Enrichment | `tests/test_enrichment/` | Size estimator, exposure classifier, BizAPI, Capital IQ |
| PitchBook | `tests/test_pitchbook/` | PitchBook REST client |
| Sources | `tests/test_sources/` | NAICS, mock, web scraper adapters |
| Scoring | `tests/test_scoring/` | Company scorer formula |
| Validation | `tests/test_validation/` | QA gate checks |
| Workflow | `tests/test_workflow/` | Dedup, dispositioning, review queue |
| API | `tests/test_api/` | FastAPI endpoint tests |
| Utils | `tests/test_utils/` | Name normalization |

### CLI Usage

```bash
# Install provides `dl-origination` command
pip install -e .

# Create a run
dl-origination run create --theme "data center capex secular growth"

# Generate recommendations
dl-origination recommend subverticals --run-id <id>
dl-origination confirm subverticals --run-id <id> --accept-all

dl-origination recommend sources --run-id <id>
dl-origination confirm sources --run-id <id> --accept-all

# Execute pipeline
dl-origination mine execute --run-id <id>

# Check review queue
dl-origination review list --run-id <id>
dl-origination review resolve --item-id <id> --decision merge

# Export results
dl-origination export --run-id <id> --format excel
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev         # Vite dev server on http://localhost:5173
npm run build       # Production build to frontend/dist/
npm run lint        # ESLint check
```

**Dev mode:** The Vite dev server proxies `/api` requests to `http://localhost:8000`, so you need the FastAPI backend running separately. Use this for frontend development with hot-reload.

**Production mode:** Run `npm run build`, then start Docker Compose. The FastAPI server serves the built assets from `frontend/dist/` when `SERVE_FRONTEND=true` is set (the default in Docker Compose). The SPA catch-all route in `app/main.py` ensures React Router paths return `index.html` instead of 404.

For detailed frontend architecture, see [Frontend Guide](frontend.md).

**Tech stack:**
- React 19 + TypeScript 5.9
- Vite 6.4 (build tool)
- Tailwind CSS 4 (styling)
- Radix UI primitives (accessible components)
- TanStack Query 5 (server state / API caching)
- TanStack Table 8 (data tables with sorting/filtering)
- Zustand 5 (client state management)
- React Router 7 (SPA routing)
- Lucide React (icons)

---

## Environment Variables

All settings are loaded from `.env` via Pydantic Settings.

### Core

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/dl_origination` | Async SQLAlchemy connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for ARQ job queue |
| `AUTH_ENABLED` | `false` | Enable authentication boundary |
| `SERVE_FRONTEND` | `true` | Serve React frontend from `frontend/dist/` |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `STORAGE_PATH` | `./data` | Local storage directory |

### AI / LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` for local dev, `claude` for production |
| `LLM_MODEL` | `claude-sonnet-4-6` | Claude model ID |
| `LLM_API_KEY` | (empty) | Anthropic API key |
| `LLM_RATE_LIMIT_RPM` | `50` | Requests per minute limit |
| `AI_CONFIDENCE_AUTO_ACCEPT_THRESHOLD` | `0.85` | Auto-accept AI outputs above this confidence |

### PitchBook

| Variable | Default | Description |
|---|---|---|
| `PITCHBOOK_PROVIDER` | `mock` | `mock` for local dev, `rest` for production (`mcp` stubbed — not functional) |
| `PITCHBOOK_API_BASE_URL` | `https://api.pitchbook.com/v2` | PitchBook REST API base URL |
| `PITCHBOOK_API_KEY` | (empty) | PitchBook API key (when `rest`) |
| `PITCHBOOK_API_TIMEOUT` | `30.0` | Per-request timeout in seconds |
| `PITCHBOOK_API_MAX_RETRIES` | `3` | Max retry attempts |
| `MCP_PITCHBOOK_URL` | (empty) | MCP server URL (when `mcp`) |
| `MCP_PITCHBOOK_TOKEN` | (empty) | MCP authentication token (when `mcp`) |

### NAICS BizAPI

| Variable | Default | Description |
|---|---|---|
| `BIZAPI_PROVIDER` | `mock` | `mock` for local dev, `rest` for production |
| `BIZAPI_USERNAME` | (empty) | BizAPI Basic Auth username |
| `BIZAPI_PASSWORD` | (empty) | BizAPI Basic Auth password |
| `BIZAPI_USE_SANDBOX` | `true` | Use sandbox endpoint for testing |
| `BIZAPI_TIMEOUT` | `15.0` | Per-request timeout in seconds |
| `BIZAPI_MAX_RETRIES` | `3` | Max retry attempts |
| `BIZAPI_RATE_LIMIT_RPS` | `3.0` | Rate limit (requests per second) |

### S&P Capital IQ

| Variable | Default | Description |
|---|---|---|
| `CAPITALIQ_PROVIDER` | `mock` | `mock` for local dev, `rest` for production |
| `CAPITALIQ_API_URL` | (empty) | Capital IQ API base URL |
| `CAPITALIQ_API_KEY` | (empty) | Capital IQ API key |
| `CAPITALIQ_TIMEOUT` | `30.0` | Per-request timeout in seconds |
| `CAPITALIQ_MAX_RETRIES` | `3` | Max retry attempts |
| `CAPITALIQ_SKIP_IF_PB_COMPLETE` | `true` | Skip CIQ when PitchBook has full data |

---

## Production Deployment

### Docker-Based Deployment

The same Docker Compose stack works for production with configuration changes:

```yaml
# docker-compose.prod.yml (overlay)
services:
  api:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      LLM_PROVIDER: claude
      LLM_API_KEY: ${LLM_API_KEY}
      PITCHBOOK_PROVIDER: rest
      PITCHBOOK_API_KEY: ${PITCHBOOK_API_KEY}
      AUTH_ENABLED: "true"
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### Managed Infrastructure

For production, replace Docker services with managed equivalents:

| Component | Docker | Production |
|---|---|---|
| PostgreSQL | `postgres:16-alpine` | AWS RDS, Cloud SQL, Azure Flexible Server |
| Redis | `redis:7-alpine` | AWS ElastiCache, Memorystore, Azure Cache |
| Storage | Local filesystem | AWS S3, GCS, Azure Blob |
| Auth | Disabled | SSO / OAuth2 / SAML |
| Secrets | `.env` file | Vault, AWS Secrets Manager, Parameter Store |

### Health Checks

| Endpoint | Purpose | What It Checks |
|---|---|---|
| `GET /api/v1/health` | Liveness probe | Database connectivity |
| `GET /api/v1/readiness` | Readiness probe | Database + all connectors (PitchBook, BizAPI, Capital IQ) |
| `GET /api/v1/connectors/status` | Operational | Connector-by-connector health |

### Monitoring

The application uses **structlog** for structured JSON logging. Key log events:

```
# Pipeline lifecycle
miner_pipeline_start    run_id=...
miner_stage_start       stage=name_generation run_id=...
miner_stage_complete    stage=name_generation run_id=...
miner_pipeline_complete run_id=...

# Source extraction
source_extracted        source=ENR count=15

# LLM calls
mock_llm_complete       prompt_length=1935

# Enrichment providers
bizapi_enrichment_complete   run_id=... matched=N not_found=N errors=N
capitaliq_enrichment_complete run_id=... matched=N not_found=N skipped=N errors=N
pitchbook_enrichment_complete run_id=... matched=N not_found=N

# Errors
source_extraction_failed       source=... error=...
web_enrichment_failed          company=... error=...
bizapi_enrichment_failed       company=... error=...
capitaliq_enrichment_failed    company=... error=...
pitchbook_enrichment_failed    company=... error=...
```

### Database Migrations

The project includes Alembic for schema migrations. The `DATABASE_URL` env var overrides the default URL in `alembic.ini`:

```bash
# Apply all migrations
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic upgrade head

# Generate a new migration after ORM model changes
DATABASE_URL=postgresql+asyncpg://dl_user:dl_pass@localhost:5432/dl_origination \
  alembic revision --autogenerate -m "description"

# Check current version
alembic current
```

**Current migrations:**

| Revision | Description |
|---|---|
| `0001` | Initial schema — 8 tables (runs, companies, theme_recommendations, source_recommendations, checkpoints, review_queue, export_manifests, company_evidence) |
| `0002` | Add enrichment status columns — `bizapi_status`, `ciq_status`, `bizapi_duns`, `ciq_entity_id` on companies table |

> **`create_all()` does not add columns to existing tables.** If ORM models change,
> run `docker compose down -v` to reset the database before `docker compose up`.
> Generate a new Alembic migration for any schema changes.

In Docker dev mode, `Base.metadata.create_all()` runs on startup and creates all tables from the ORM models. This only creates missing tables — it does **not** add columns to existing tables. If you change the ORM model, either run `alembic upgrade head` or reset the database with `docker compose down -v`.

### Scaling Considerations

| Component | Scaling Strategy |
|---|---|
| API | Horizontal: add `--workers N` or run multiple containers behind a load balancer |
| Worker | Horizontal: run multiple worker containers (ARQ distributes jobs) |
| Database | Vertical (read replicas for reporting queries) |
| LLM calls | Rate-limited via `LLM_RATE_LIMIT_RPM`; increase for higher throughput |
| BizAPI | Rate-limited at 3 req/s; per-run enforcement via token bucket |
| Pipeline | Single-run serial; multiple runs can execute concurrently via separate workers |

---

## Extending the Platform

### Adding a New Source Adapter

1. Create `app/miner/sources/your_adapter.py`:

```python
from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany

class YourAdapter(SourceAdapter):
    adapter_type = "your_type"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        # Extract and return company names
        ...

    async def is_available(self, source_config: dict) -> bool:
        # Check if source is accessible
        ...
```

2. Register in `app/miner/sources/registry.py`

### Adding a New Industry Profile

Create `profiles/your_industry.yaml` with:
- Sub-vertical hints and NAICS code mappings
- Source templates (URLs, selectors)
- Scoring weight overrides (if different from defaults)

### Connecting Real PitchBook

1. Set `PITCHBOOK_PROVIDER=rest` in `.env`
2. Set `PITCHBOOK_API_KEY`

See [PitchBook Integration](integrations/pitchbook.md) for full details. MCP mode is stubbed and not functional.

### Connecting Real BizAPI

1. Set `BIZAPI_PROVIDER=rest` in `.env`
2. Set `BIZAPI_USERNAME` and `BIZAPI_PASSWORD`
3. Set `BIZAPI_USE_SANDBOX=true` for initial testing
4. Client is fully implemented in `app/miner/enrichment/bizapi/rest_client.py`

### Connecting Real Capital IQ

1. Set `CAPITALIQ_PROVIDER=rest` in `.env`
2. Set `CAPITALIQ_API_URL` and `CAPITALIQ_API_KEY`
3. Client is fully implemented in `app/miner/enrichment/capitaliq/rest_client.py`
