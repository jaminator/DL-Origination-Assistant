import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { RecommendationBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { useStore } from '@/hooks/useStore';
import { ChevronDown, ChevronRight, Lightbulb } from 'lucide-react';

export function SubVerticals() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [confirmed, setConfirmed] = useState(false);

  const { data: subverticals, isLoading } = useQuery({
    queryKey: ['subverticals', runId],
    queryFn: () => api.listSubverticals(runId!),
    enabled: !!runId,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.recommendSubverticals(runId!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['subverticals', runId] });
      // Pre-select strong_fit and moderate_fit
      const autoSelected = new Set(
        result.recommendations
          .filter((r) => ['strong_fit', 'moderate_fit'].includes(r.recommendation_status ?? ''))
          .map((r) => r.id),
      );
      setSelected(autoSelected);
      addToast({ type: 'success', message: `${result.count} sub-verticals generated` });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const confirmMutation = useMutation({
    mutationFn: () => api.confirmSubverticals(runId!, Array.from(selected)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] });
      setConfirmed(true);
      addToast({ type: 'success', message: 'Sub-verticals confirmed' });
      navigate(`/runs/${runId}/sources`);
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  // Initialize selections from backend data
  if (subverticals?.length && selected.size === 0 && !confirmed) {
    const preSelected = new Set(
      subverticals
        .filter((sv) => sv.user_selected || ['strong_fit', 'moderate_fit'].includes(sv.recommendation_status ?? ''))
        .map((sv) => sv.id),
    );
    if (preSelected.size > 0) setSelected(preSelected);
  }

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (isLoading) return <PageSpinner />;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Sub-Vertical Recommendations</h1>
          <p className="text-sm text-slate-500 mt-1">Review and select sub-verticals for source discovery</p>
        </div>
        <div className="flex gap-2">
          {(!subverticals || subverticals.length === 0) && (
            <Button onClick={() => generateMutation.mutate()} loading={generateMutation.isPending}>
              Generate Recommendations
            </Button>
          )}
          {subverticals && subverticals.length > 0 && !confirmed && (
            <Button onClick={() => confirmMutation.mutate()} loading={confirmMutation.isPending} disabled={selected.size === 0}>
              Confirm {selected.size} Selected
            </Button>
          )}
        </div>
      </div>

      {generateMutation.isPending && <PageSpinner />}

      {!subverticals?.length && !generateMutation.isPending && (
        <EmptyState
          icon={<Lightbulb className="h-12 w-12" />}
          title="No recommendations yet"
          description="Generate AI-powered sub-vertical recommendations for your investment theme."
          action={{ label: 'Generate', onClick: () => generateMutation.mutate() }}
        />
      )}

      {subverticals && subverticals.length > 0 && (
        <>
          <div className="mb-3 flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set(subverticals.map((s) => s.id)))}>
              Select All
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
              Deselect All
            </Button>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="w-10 px-3 py-3" />
                  <th className="w-8" />
                  <th className="text-left px-3 py-3 font-medium text-slate-600">Sub-Vertical</th>
                  <th className="text-left px-3 py-3 font-medium text-slate-600 w-28">Status</th>
                  <th className="text-right px-3 py-3 font-medium text-slate-600 w-24">Thematic</th>
                  <th className="text-right px-3 py-3 font-medium text-slate-600 w-24">Lender</th>
                  <th className="text-right px-3 py-3 font-medium text-slate-600 w-20">Total</th>
                </tr>
              </thead>
              <tbody>
                {subverticals
                  .sort((a, b) => (b.total_recommendation_score ?? 0) - (a.total_recommendation_score ?? 0))
                  .map((sv) => (
                    <React.Fragment key={sv.id}>
                      <tr className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-3">
                          <input
                            type="checkbox"
                            checked={selected.has(sv.id)}
                            onChange={() => toggleSelect(sv.id)}
                            className="rounded border-slate-300"
                            disabled={confirmed}
                          />
                        </td>
                        <td>
                          <button onClick={() => toggleExpand(sv.id)} className="p-1 hover:bg-slate-100 rounded">
                            {expanded.has(sv.id) ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </button>
                        </td>
                        <td className="px-3 py-3 font-medium text-slate-900">{sv.subvertical_name ?? '—'}</td>
                        <td className="px-3 py-3">
                          <RecommendationBadge status={sv.recommendation_status ?? 'watchlist'} />
                        </td>
                        <td className="px-3 py-3 text-right text-slate-600">{sv.thematic_fit_score?.toFixed(0) ?? '—'}</td>
                        <td className="px-3 py-3 text-right text-slate-600">{sv.lender_fit_score?.toFixed(0) ?? '—'}</td>
                        <td className="px-3 py-3 text-right font-medium">{sv.total_recommendation_score?.toFixed(0) ?? '—'}</td>
                      </tr>
                      {expanded.has(sv.id) && (
                        <tr className="bg-slate-50 border-b border-slate-100">
                          <td colSpan={7} className="px-8 py-4">
                            <div className="grid grid-cols-2 gap-6 text-sm">
                              <div>
                                <p className="text-slate-700 mb-3">{sv.description ?? ''}</p>
                                <div className="space-y-1 text-xs text-slate-500">
                                  {sv.demand_profile && <div>Demand: {sv.demand_profile}</div>}
                                  {sv.cyclicality_profile && <div>Cyclicality: {sv.cyclicality_profile}</div>}
                                  {sv.margin_profile && <div>Margins: {sv.margin_profile}</div>}
                                  {sv.recurring_revenue_profile && <div>Recurring Rev: {sv.recurring_revenue_profile}</div>}
                                  {sv.ownership_landscape && <div>Ownership: {sv.ownership_landscape}</div>}
                                </div>
                              </div>
                              <div>
                                {(sv.reasons_to_lend ?? []).length > 0 && (
                                  <div className="mb-3">
                                    <h4 className="text-xs font-semibold text-green-700 mb-1">Reasons to Lend</h4>
                                    <ul className="space-y-0.5">
                                      {(sv.reasons_to_lend ?? []).map((r, i) => (
                                        <li key={i} className="text-xs text-green-600">+ {r}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {(sv.reasons_not_to_lend ?? []).length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-red-700 mb-1">Risks</h4>
                                    <ul className="space-y-0.5">
                                      {(sv.reasons_not_to_lend ?? []).map((r, i) => (
                                        <li key={i} className="text-xs text-red-600">- {r}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {(sv.example_borrower_archetypes ?? []).length > 0 && (
                                  <div className="mt-3 flex flex-wrap gap-1">
                                    {(sv.example_borrower_archetypes ?? []).map((a, i) => (
                                      <span key={i} className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600">{a}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
