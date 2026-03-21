# Frontend Guide

## Tech Stack

- **React 19** + TypeScript 5.9
- **Vite 6.4** — build tool + dev server
- **Tailwind CSS 4** — utility-first styling
- **Radix UI** — accessible component primitives (checkbox, collapsible, dialog, dropdown, progress, scroll-area, select, separator, slot, tabs, tooltip)
- **TanStack Query 5** — server state management with smart polling
- **TanStack Table 8** — sortable/filterable data tables
- **Zustand 5** — client state management
- **React Router 7** — SPA routing
- **Lucide React** — icons
- **class-variance-authority** + **clsx** + **tailwind-merge** — class utility helpers

---

## Page Inventory

| Page | Route | Purpose | Key Data Dependencies |
|---|---|---|---|
| Dashboard | `/` | Run list with create-new-run button | `listRuns` |
| RunSetup | `/runs/:runId/setup` | Theme + configuration input form | `getRun` |
| SubVerticals | `/runs/:runId/subverticals` | AI sub-vertical recommendations with confirm/reject | `listSubverticals`, `recommendSubverticals`, `confirmSubverticals` |
| Sources | `/runs/:runId/sources` | Source + NAICS recommendations with confirm | `listSources`, `recommendSources`, `confirmSources` |
| Pipeline | `/runs/:runId/pipeline` | 12-stage execution with live progress polling | `getRunStatus` (2s poll), `listCheckpoints` (5s poll), `executeRun`, `resumeRun` |
| Companies | `/runs/:runId/companies` | Scored company table with sorting/filtering | `listCompanies` |
| CompanyDetail | `/runs/:runId/companies/:companyId` | Single company deep-dive with all enrichment data | `getCompany` |
| ReviewQueue | `/runs/:runId/review` | Dedup + QA review items with resolve actions | `listReviewQueue`, `resolveReviewItem` |
| Exports | `/runs/:runId/exports` | Download CSV/JSONL/Excel exports | `listExports`, `triggerExport`, `getExportDownloadUrl` |
| Settings | `/settings` | Connector status display | `getConnectorStatus` |

### Routing

The app uses React Router 7 with two layout zones:

- **Root layout** (`AppShell` with `TopBar`) — Dashboard and Settings
- **Run layout** (`AppShell` with `TopBar` + `WorkflowRail`) — All `/runs/:runId/*` pages

`WorkflowRail` provides step-by-step navigation and polls run status every 2 seconds while the pipeline is running.

---

## Component Library

### Layout (`components/layout/`)

| Component | Purpose |
|---|---|
| `AppShell.tsx` | Main layout wrapper; conditionally shows WorkflowRail based on `runId` |
| `TopBar.tsx` | Top navigation bar with header and run context |
| `WorkflowRail.tsx` | Left sidebar showing workflow step progress |

### UI Primitives (`components/ui/`)

| Component | Purpose |
|---|---|
| `Badge.tsx` | Status and tag badges |
| `Button.tsx` | Primary button component |
| `Card.tsx` | Card container |
| `Drawer.tsx` | Side drawer for CompanyDetail overlay |
| `EmptyState.tsx` | Empty state placeholder |
| `ScoreBar.tsx` | Score visualization bar |
| `Spinner.tsx` | Loading spinner |
| `Toast.tsx` | Toast notifications with auto-dismiss |

All UI primitives are built on Radix UI for accessibility.

---

## State Management

### Server State — TanStack Query

All API data fetching, caching, and polling is handled by TanStack Query. Configuration:

- `staleTime`: 10 seconds
- `retry`: 1 attempt
- Polling intervals:
  - Pipeline run status: **2 seconds** (while `status === 'running'`)
  - Pipeline checkpoints: **5 seconds** (while running)
  - Polling stops automatically on `completed` or `failed`

### Client State — Zustand (`hooks/useStore.ts`)

Zustand manages UI-only state that doesn't come from the server:

| State | Purpose |
|---|---|
| `sidebarCollapsed` | Sidebar toggle |
| `selectedCompanyId` | Company detail drawer open/close |
| `selectedReviewItemId` | Review item selection |
| `toasts` | Toast notification queue |

Toast auto-dismiss: 5 seconds for success/warning/info; error toasts persist until dismissed.

---

## API Client

All API calls go through `src/lib/api.ts`. The client:

- Uses `fetch` with a base URL of `/api/v1`
- Throws errors with the server's error message on non-2xx responses
- Returns parsed JSON

### Endpoint Functions

| Function | Method | Path |
|---|---|---|
| `listRuns` | GET | `/runs` |
| `getRun` | GET | `/runs/{runId}` |
| `createRun` | POST | `/runs` |
| `getRunStatus` | GET | `/runs/{runId}/status` |
| `executeRun` | POST | `/runs/{runId}/execute` |
| `resumeRun` | POST | `/runs/{runId}/resume` |
| `rerunStage` | POST | `/runs/{runId}/stages/{stage}/rerun` |
| `listCheckpoints` | GET | `/runs/{runId}/checkpoints` |
| `recommendSubverticals` | POST | `/runs/{runId}/recommend-subverticals` |
| `listSubverticals` | GET | `/runs/{runId}/subverticals` |
| `confirmSubverticals` | POST | `/runs/{runId}/confirm-subverticals` |
| `recommendSources` | POST | `/runs/{runId}/recommend-sources` |
| `listSources` | GET | `/runs/{runId}/sources` |
| `confirmSources` | POST | `/runs/{runId}/confirm-sources` |
| `listCompanies` | GET | `/runs/{runId}/companies` |
| `getCompany` | GET | `/runs/{runId}/companies/{companyId}` |
| `listReviewQueue` | GET | `/runs/{runId}/review-queue` |
| `resolveReviewItem` | POST | `/runs/{runId}/review-queue/{itemId}/resolve` |
| `listExports` | GET | `/runs/{runId}/exports` |
| `triggerExport` | POST | `/runs/{runId}/exports` |
| `getExportDownloadUrl` | GET | `/runs/{runId}/exports/{exportId}/download` |
| `getConnectorStatus` | GET | `/connectors/status` |

### Adding a New Endpoint

1. Add the function to `src/lib/api.ts` following the existing pattern
2. Add TypeScript types to `src/types/api.ts`
3. Use it in a page via TanStack Query (`useQuery` or `useMutation`)

---

## Utility Functions (`lib/utils.ts`)

| Function | Purpose |
|---|---|
| `cn()` | Tailwind class merging (clsx + tailwind-merge) |
| `formatCurrency(value)` | Formats to $B/M/K notation |
| `formatScore(score)` | Formats numeric score |
| `formatDate(iso)` | Full date+time format |
| `formatDateShort(iso)` | Date only |

---

## Dev Setup

```bash
cd frontend
npm install
npm run dev         # Vite dev server on http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://localhost:8000` (configured in `vite.config.ts`). You need the FastAPI backend running separately for API calls to work.

---

## Production Build

```bash
cd frontend
npm run build       # Outputs to frontend/dist/
```

In Docker Compose, the `dist/` directory is volume-mounted into the API container at `/app/frontend/dist`. FastAPI serves these files when `SERVE_FRONTEND=true` is set (the default in Docker Compose).

The SPA catch-all route in `app/main.py` ensures React Router paths return `index.html` instead of 404.

---

## Known Issues

- **Pipeline polling loop**: If the pipeline crashes without updating the run status to `failed`, the Pipeline page continues polling indefinitely. Workaround: refresh the page or start a new run.
