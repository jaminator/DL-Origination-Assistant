import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { DispositionBadge, OwnershipBadge, EnrichmentDots, QualityDot } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/ui/ScoreBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { Drawer } from '@/components/ui/Drawer';
import { CompanyDetail } from './CompanyDetail';
import { useStore } from '@/hooks/useStore';
import { formatCurrency } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { Building2, Filter, Check, AlertTriangle } from 'lucide-react';

const PAGE_SIZES = [25, 50, 100];

export function Companies() {
  const { runId } = useParams();
  const selectedCompanyId = useStore((s) => s.selectedCompanyId);
  const openCompanyDrawer = useStore((s) => s.openCompanyDrawer);
  const closeCompanyDrawer = useStore((s) => s.closeCompanyDrawer);

  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(0);
  const [disposition, setDisposition] = useState<string>('');
  const [showFilters, setShowFilters] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: ['companies', runId, disposition, pageSize, page],
    queryFn: () =>
      api.listCompanies(runId!, {
        disposition: disposition || undefined,
        limit: pageSize,
        offset: page * pageSize,
      }),
    enabled: !!runId,
  });

  if (isLoading) return <PageSpinner />;

  const companies = data?.companies ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="flex h-full">
      {/* Filters sidebar */}
      {showFilters && (
        <div className="w-56 shrink-0 border-r border-slate-200 bg-white p-4 overflow-y-auto">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Filters</h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Disposition</label>
              <select
                value={disposition}
                onChange={(e) => { setDisposition(e.target.value); setPage(0); }}
                className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs"
              >
                <option value="">All</option>
                <option value="primary">Primary</option>
                <option value="cascade_anchor">Cascade Anchor</option>
                <option value="watch">Watch</option>
                <option value="exclude">Exclude</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Main table */}
      <div className="flex-1 overflow-auto">
        <div className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setShowFilters(!showFilters)} className="text-slate-500 hover:text-slate-700">
              <Filter className="h-4 w-4" />
            </button>
            <span className="text-sm text-slate-600">{total} companies</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>Page {page + 1} of {totalPages || 1}</span>
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-2 py-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
            >
              Prev
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="px-2 py-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
            >
              Next
            </button>
            <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }} className="border border-slate-200 rounded px-1 py-1 text-xs">
              {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}/page</option>)}
            </select>
          </div>
        </div>

        {companies.length === 0 ? (
          <EmptyState
            icon={<Building2 className="h-12 w-12" />}
            title="No companies"
            description="Execute the pipeline to generate borrower candidates."
          />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left">
                <th className="px-4 py-2 font-medium text-slate-600 sticky left-0 bg-slate-50">Company</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-20">State</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-24">Disposition</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-24">Ownership</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-28">Revenue</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-32">Score</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-14 text-center">Out</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-14 text-center">QA</th>
                <th className="px-3 py-2 font-medium text-slate-600 w-20">Enrich</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => {
                const d = c.data;
                return (
                  <tr
                    key={c.id}
                    onClick={() => openCompanyDrawer(c.id)}
                    className={cn(
                      'border-b border-slate-100 hover:bg-slate-50 cursor-pointer',
                      selectedCompanyId === c.id && 'bg-blue-50',
                    )}
                  >
                    <td className="px-4 py-2.5 font-medium text-slate-900 sticky left-0 bg-inherit max-w-xs truncate">
                      {d.canonical_name}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-slate-500">{d.hq_state ?? '—'}</td>
                    <td className="px-3 py-2.5"><DispositionBadge disposition={d.disposition} /></td>
                    <td className="px-3 py-2.5"><OwnershipBadge tier={d.ownership_tier} /></td>
                    <td className="px-3 py-2.5 text-xs">
                      <span className="flex items-center gap-1">
                        <QualityDot quality={d.revenue_quality} />
                        {formatCurrency(d.revenue_estimate)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <ScoreBar score={d.total_score} />
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {d.eligible_for_outreach ? <Check className="h-4 w-4 text-green-500 mx-auto" /> : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {d.review_required ? <AlertTriangle className="h-4 w-4 text-amber-500 mx-auto" /> : null}
                    </td>
                    <td className="px-3 py-2.5">
                      <EnrichmentDots bizapi={d.bizapi_status} pitchbook={d.pb_status} capitaliq={d.ciq_status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Company detail drawer */}
      <Drawer
        open={!!selectedCompanyId}
        onClose={closeCompanyDrawer}
        title="Company Detail"
      >
        {selectedCompanyId && <CompanyDetail runId={runId!} companyId={selectedCompanyId} />}
      </Drawer>
    </div>
  );
}
