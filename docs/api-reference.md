# API Reference

All endpoints are served under the `/api/v1` prefix.

---

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness probe |
| GET | `/api/v1/readiness` | Readiness probe |

### `GET /api/v1/health`

Returns database connectivity status.

**Response:** `{ "status": "ok", "database": "connected" }`

### `GET /api/v1/readiness`

Returns database and all connector availability (PitchBook, BizAPI, Capital IQ).

**Response:** `{ "status": "ok", "database": "connected", "connectors": { ... } }`

---

## Runs

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/runs` | List runs (paginated) |
| POST | `/api/v1/runs` | Create a new run |
| GET | `/api/v1/runs/{run_id}` | Get run details |
| GET | `/api/v1/runs/{run_id}/status` | Get run status |
| POST | `/api/v1/runs/{run_id}/execute` | Start mining pipeline |
| POST | `/api/v1/runs/{run_id}/resume` | Resume from checkpoint |

### `GET /api/v1/runs`

**Query parameters:** `limit` (int, default 20), `offset` (int, default 0)

**Response:** `{ "runs": [...], "total": int, "limit": int, "offset": int }`

### `POST /api/v1/runs`

**Request body:** `CreateRunRequest` (`app/platform/models/schemas.py`)

Key fields: `theme` (required), `theme_notes`, `industry_description`, `geography_filter`, `revenue_ceiling`, `cascade_anchor_threshold`, `ebitda_soft_ceiling`, `max_recursion_depth`, `profile_name`, `tier_a_scoring_bonus`, `tier_b_scoring_bonus`, `tier_c_scoring_bonus`, `include_cascade_anchors_in_outreach`, `boundary_treatment`

**Response:** `{ "id": uuid, "status": "pending", "created_at": datetime }`

### `GET /api/v1/runs/{run_id}`

**Path parameters:** `run_id` (UUID)

**Response:** `{ "id": uuid, "config": {...}, "current_stage": str, "status": str, "created_at": datetime, "updated_at": datetime }`

### `GET /api/v1/runs/{run_id}/status`

Lightweight status-only endpoint used by the frontend for polling.

**Response:** `{ "id": uuid, "current_stage": str, "status": str }`

### `POST /api/v1/runs/{run_id}/execute`

Starts the 12-stage mining pipeline. When Redis/ARQ is available, the job runs asynchronously and returns a `job_id`. When Redis is unavailable, falls back to synchronous inline execution.

**Response:** `{ "status": "accepted"|"completed", "job_id": str|null, "result": dict|null, "run_id": uuid }`

### `POST /api/v1/runs/{run_id}/resume`

Resume pipeline from the last saved checkpoint. The orchestrator determines the next stage automatically.

**Response:** `{ "status": "accepted"|"completed", "job_id": str|null, "result": dict|null, "run_id": uuid }`

---

## Recommendations

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/runs/{run_id}/recommend-subverticals` | Generate sub-vertical recommendations |
| GET | `/api/v1/runs/{run_id}/subverticals` | List sub-verticals for a run |
| POST | `/api/v1/runs/{run_id}/confirm-subverticals` | Lock sub-vertical selections |
| POST | `/api/v1/runs/{run_id}/recommend-sources` | Generate source recommendations |
| GET | `/api/v1/runs/{run_id}/sources` | List sources for a run |
| POST | `/api/v1/runs/{run_id}/confirm-sources` | Lock source selections |

### `POST /api/v1/runs/{run_id}/recommend-subverticals`

Triggers LLM-based sub-vertical recommendation. Uses `ThemeAnalysisPrompt`.

**Response:** `{ "run_id": uuid, "count": int, "recommendations": [...] }`

### `GET /api/v1/runs/{run_id}/subverticals`

**Response:** `[{ "id": uuid, "subvertical_name": str, "recommendation_status": str, "total_recommendation_score": float, "user_selected": bool, ... }]`

### `POST /api/v1/runs/{run_id}/confirm-subverticals`

**Request body:** `ConfirmSubverticalsRequest` — `selected_ids` (list[UUID]), `accept_all` (bool)

Saves `selected_subverticals` to the run config in the database.

**Response:** `{ "run_id": uuid, "confirmed_subverticals": [...] }`

### `POST /api/v1/runs/{run_id}/recommend-sources`

Triggers LLM-based source recommendation. Uses `SourceDiscoveryPrompt`.

**Response:** `{ "run_id": uuid, "count": int, "sources": [...] }`

### `GET /api/v1/runs/{run_id}/sources`

**Response:** `[{ "id": uuid, "source_name": str, "source_type": str, "user_selected": bool, ... }]`

### `POST /api/v1/runs/{run_id}/confirm-sources`

**Request body:** `ConfirmSourcesRequest` — `selected_ids` (list[UUID]), `accept_all` (bool), `deselected_ids` (list[UUID])

**Response:** `{ "run_id": uuid, "confirmed_sources_count": int }`

---

## Pipeline

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/runs/{run_id}/stages/{stage}/rerun` | Re-run a single pipeline stage |

### `POST /api/v1/runs/{run_id}/stages/{stage}/rerun`

Re-runs a single stage without advancing the pipeline. The pipeline must have previously reached the specified stage.

**Path parameters:** `run_id` (UUID), `stage` (WorkflowStage enum value)

**Response:** `{ "status": "completed", "run_id": uuid, "stage": str, "result": dict }`

---

## Companies

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/runs/{run_id}/companies` | List companies for a run |
| GET | `/api/v1/runs/{run_id}/companies/{company_id}` | Get single company detail |

### `GET /api/v1/runs/{run_id}/companies`

**Query parameters:** `disposition` (str, optional filter), `limit` (int), `offset` (int)

**Response:** `{ "run_id": uuid, "total": int, "limit": int, "offset": int, "companies": [...] }`

### `GET /api/v1/runs/{run_id}/companies/{company_id}`

**Response:** `{ "id": uuid, "canonical_name": str, "data": { ... } }`

---

## Review Queue

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/runs/{run_id}/review-queue` | List review items |
| POST | `/api/v1/runs/{run_id}/review-queue/{item_id}/resolve` | Resolve a review item |

### `GET /api/v1/runs/{run_id}/review-queue`

**Query parameters:** `resolved` (bool, optional filter)

**Response:** `[{ "id": uuid, "reason": str, "details": str, "resolved": bool, "resolution": str|null, "data": {...} }]`

### `POST /api/v1/runs/{run_id}/review-queue/{item_id}/resolve`

**Request body:** `ResolveRequest` — `resolution` (str: `merge`, `keep_both`, `exclude`, `accept`)

**Response:** `{ "status": "resolved", "item_id": uuid, "resolution": str }`

---

## Exports

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/runs/{run_id}/exports` | List exports for a run |
| POST | `/api/v1/runs/{run_id}/exports` | Trigger an export |
| GET | `/api/v1/runs/{run_id}/exports/{export_id}/download` | Download export file |

### `GET /api/v1/runs/{run_id}/exports`

**Response:** `[{ "id": uuid, "created_at": datetime, "data": {...} }]`

### `POST /api/v1/runs/{run_id}/exports`

**Query parameters:** `format` (str, default `"excel"` — one of `csv`, `jsonl`, `excel`)

**Response:** Export manifest dict with file paths and metadata.

### `GET /api/v1/runs/{run_id}/exports/{export_id}/download`

Returns the export file as a download (FileResponse). Content type depends on format: `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, or `application/jsonl`.

---

## Checkpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/runs/{run_id}/checkpoints` | List pipeline checkpoints |
| GET | `/api/v1/runs/{run_id}/checkpoints/{checkpoint_id}` | Inspect a checkpoint |

### `GET /api/v1/runs/{run_id}/checkpoints`

**Response:** `[{ "id": uuid, "stage": str, "company_count": int, "created_at": datetime, "notes": str|null }]`

### `GET /api/v1/runs/{run_id}/checkpoints/{checkpoint_id}`

**Response:** Full checkpoint data including artifact path.

---

## Connectors

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/connectors/status` | Connector health report |

### `GET /api/v1/connectors/status`

Reports availability of all registered connectors (PitchBook, BizAPI, Capital IQ).

**Response:** `{ "connectors": { "pitchbook": { "available": bool, "message": str }, ... }, "registered": [str] }`
