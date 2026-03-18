# DL Origination Assistant — Frontend

React 19 + TypeScript frontend for the DL Origination Assistant platform.

## Tech Stack

- **React 19** + TypeScript 5.9
- **Vite 6.4** — build tool + dev server
- **Tailwind CSS 4** — utility-first styling
- **Radix UI** — accessible component primitives (checkbox, dialog, dropdown, progress, select, tabs, tooltip)
- **TanStack Query 5** — server state management with smart polling
- **TanStack Table 8** — sortable/filterable data tables
- **Zustand 5** — client state management
- **React Router 7** — SPA routing
- **Lucide React** — icons

## Development

```bash
npm install
npm run dev         # Vite dev server on http://localhost:5173
npm run build       # Production build to dist/
npm run lint        # ESLint check
npm run preview     # Preview production build
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so you need the FastAPI backend running.

## Production

Run `npm run build` to create `dist/`. The FastAPI backend serves these static files when `SERVE_FRONTEND=true` is set (default in Docker Compose).

## Pages

| Page | Route | Description |
|---|---|---|
| Dashboard | `/` | Run list with create-new-run |
| RunSetup | `/runs/new` | Theme + config input form |
| SubVerticals | `/runs/:id/subverticals` | AI sub-vertical recommendations |
| Sources | `/runs/:id/sources` | Source + NAICS recommendations |
| Pipeline | `/runs/:id/pipeline` | 12-stage execution with live progress |
| Companies | `/runs/:id/companies` | Scored company table |
| CompanyDetail | `/runs/:id/companies/:companyId` | Single company deep-dive |
| ReviewQueue | `/runs/:id/review` | Dedup + QA review items |
| Exports | `/runs/:id/exports` | Download CSV/JSONL/Excel |
| Settings | `/settings` | Connector status + config |

## Project Structure

```
src/
├── main.tsx                    # App entry + React Router
├── App.tsx                     # Route definitions
├── pages/                      # Page components (one per route)
├── components/
│   ├── layout/                 # AppShell, TopBar, WorkflowRail
│   └── ui/                     # Reusable primitives (Badge, Button, Card, etc.)
├── hooks/useStore.ts           # Zustand client state
├── lib/
│   ├── api.ts                  # REST API client (all endpoints)
│   └── utils.ts                # Formatting helpers
└── types/api.ts                # TypeScript API response types
```

## API Client

All API calls go through `src/lib/api.ts`. The client uses `fetch` with a base URL of `/api/v1`. TanStack Query handles caching, refetching, and polling.

Key polling intervals:
- **Pipeline run status**: 2 seconds while `status === 'running'`
- **Pipeline checkpoints**: 5 seconds while running
- Polling stops automatically when status changes to `completed` or `failed`
