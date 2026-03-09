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
docker compose up --build
```

This starts 4 services:

| Service | Port | Description |
|---|---|---|
| `api` | 8000 | FastAPI with hot-reload |
| `worker` | — | ARQ background job worker |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |

Volumes mount `./app`, `./profiles`, and `./data` for live editing.

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

All 152 tests run with mock providers — no external services required.

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

---

## Environment Variables

All settings are loaded from `.env` via Pydantic Settings.

### Core

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/dl_origination` | Async SQLAlchemy connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL for ARQ job queue |
| `AUTH_ENABLED` | `false` | Enable authentication boundary |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `STORAGE_PATH` | `./data` | Local storage directory |

### AI / LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` for local dev, `claude` for production |
| `LLM_MODEL` | `claude-sonnet-4-5-20250514` | Claude model ID |
| `LLM_API_KEY` | (empty) | Anthropic API key |
| `LLM_RATE_LIMIT_RPM` | `50` | Requests per minute limit |
| `AI_CONFIDENCE_AUTO_ACCEPT_THRESHOLD` | `0.85` | Auto-accept AI outputs above this confidence |

### PitchBook MCP

| Variable | Default | Description |
|---|---|---|
| `PITCHBOOK_PROVIDER` | `mock` | `mock` for local dev, `mcp` for production |
| `MCP_PITCHBOOK_URL` | (empty) | MCP server URL |
| `MCP_PITCHBOOK_TOKEN` | (empty) | MCP authentication token |

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
      PITCHBOOK_PROVIDER: mcp
      MCP_PITCHBOOK_URL: ${MCP_PITCHBOOK_URL}
      MCP_PITCHBOOK_TOKEN: ${MCP_PITCHBOOK_TOKEN}
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
| `GET /api/v1/readiness` | Readiness probe | Database + MCP connectors |
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

# Errors
source_extraction_failed  source=... error=...
web_enrichment_failed     company=... error=...
pitchbook_enrichment_failed company=... error=...
```

### Database Migrations

The project includes Alembic for schema migrations:

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current version
alembic current
```

### Scaling Considerations

| Component | Scaling Strategy |
|---|---|
| API | Horizontal: add `--workers N` or run multiple containers behind a load balancer |
| Worker | Horizontal: run multiple worker containers (ARQ distributes jobs) |
| Database | Vertical (read replicas for reporting queries) |
| LLM calls | Rate-limited via `LLM_RATE_LIMIT_RPM`; increase for higher throughput |
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

1. Set `PITCHBOOK_PROVIDER=mcp` in `.env`
2. Set `MCP_PITCHBOOK_URL` and `MCP_PITCHBOOK_TOKEN`
3. Implement MCP tool calls in `app/miner/pitchbook/mcp_client.py`:
   - `search_company(name)` → search results
   - `get_company_detail(entity_id)` → ownership, investors
   - `get_debt_details(entity_id)` → facility info
   - `get_competitors(entity_id)` → competitor list
