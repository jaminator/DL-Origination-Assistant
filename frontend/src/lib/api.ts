/**
 * Typed API client for DL Origination Assistant backend.
 * All endpoints prefixed /api/v1/.
 */
import type {
  RunListResponse,
  RunDetail,
  CreateRunRequest,
  RunStatus,
  SubVertical,
  SourceRecommendation,
  CompanyListResponse,
  Company,
  ReviewQueueItem,
  Checkpoint,
  ExportManifest,
  ConnectorStatus,
  ExecuteResponse,
} from '@/types/api';

const BASE = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ─── Runs ────────────────────────────────────────────────────────────────

export const api = {
  // List runs
  listRuns: (limit = 50, offset = 0) =>
    request<RunListResponse>(`/runs?limit=${limit}&offset=${offset}`),

  // Get single run
  getRun: (runId: string) => request<RunDetail>(`/runs/${runId}`),

  // Create run
  createRun: (data: CreateRunRequest) =>
    request<{ id: string; status: string; created_at: string }>('/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Get run status (for polling)
  getRunStatus: (runId: string) => request<RunStatus>(`/runs/${runId}/status`),

  // Execute pipeline
  executeRun: (runId: string) =>
    request<ExecuteResponse>(`/runs/${runId}/execute`, { method: 'POST' }),

  // Resume pipeline
  resumeRun: (runId: string) =>
    request<ExecuteResponse>(`/runs/${runId}/resume`, { method: 'POST' }),

  // Rerun stage
  rerunStage: (runId: string, stage: string) =>
    request<{ status: string; run_id: string; stage: string }>(`/runs/${runId}/stages/${stage}/rerun`, {
      method: 'POST',
    }),

  // Checkpoints
  listCheckpoints: (runId: string) =>
    request<Checkpoint[]>(`/runs/${runId}/checkpoints`),

  // ─── Recommender ────────────────────────────────────────────────────────

  recommendSubverticals: (runId: string) =>
    request<{ run_id: string; count: number; recommendations: SubVertical[] }>(
      `/runs/${runId}/recommend-subverticals`,
      { method: 'POST' },
    ),

  listSubverticals: (runId: string) =>
    request<SubVertical[]>(`/runs/${runId}/subverticals`),

  confirmSubverticals: (runId: string, selectedIds: string[]) =>
    request<{ run_id: string; confirmed_subverticals: string[] }>(
      `/runs/${runId}/confirm-subverticals`,
      { method: 'POST', body: JSON.stringify({ selected_ids: selectedIds }) },
    ),

  recommendSources: (runId: string) =>
    request<{ run_id: string; count: number; sources: SourceRecommendation[] }>(
      `/runs/${runId}/recommend-sources`,
      { method: 'POST' },
    ),

  listSources: (runId: string) =>
    request<SourceRecommendation[]>(`/runs/${runId}/sources`),

  confirmSources: (runId: string, selectedIds: string[]) =>
    request<{ run_id: string; confirmed_sources_count: number }>(
      `/runs/${runId}/confirm-sources`,
      { method: 'POST', body: JSON.stringify({ selected_ids: selectedIds }) },
    ),

  // ─── Miner ──────────────────────────────────────────────────────────────

  listCompanies: (runId: string, params?: { disposition?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.disposition) sp.set('disposition', params.disposition);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    const qs = sp.toString();
    return request<CompanyListResponse>(`/runs/${runId}/companies${qs ? `?${qs}` : ''}`);
  },

  getCompany: (runId: string, companyId: string) =>
    request<Company>(`/runs/${runId}/companies/${companyId}`),

  listReviewQueue: (runId: string, resolved?: boolean) => {
    const qs = resolved !== undefined ? `?resolved=${resolved}` : '';
    return request<ReviewQueueItem[]>(`/runs/${runId}/review-queue${qs}`);
  },

  resolveReviewItem: (runId: string, itemId: string, resolution: string) =>
    request<{ status: string; item_id: string; resolution: string }>(
      `/runs/${runId}/review-queue/${itemId}/resolve`,
      { method: 'POST', body: JSON.stringify({ resolution }) },
    ),

  // ─── Exports ────────────────────────────────────────────────────────────

  listExports: (runId: string) =>
    request<ExportManifest[]>(`/runs/${runId}/exports`),

  triggerExport: (runId: string, format: string) =>
    request<ExportManifest>(`/runs/${runId}/exports?format=${format}`, { method: 'POST' }),

  getExportDownloadUrl: (runId: string, exportId: string) =>
    `${BASE}/runs/${runId}/exports/${exportId}/download`,

  // ─── Connectors ─────────────────────────────────────────────────────────

  getConnectorStatus: () => request<ConnectorStatus>('/connectors/status'),
};
