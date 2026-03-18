import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { PriorityBadge, Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { useStore } from '@/hooks/useStore';
import { ChevronDown, ChevronRight, Database } from 'lucide-react';

export function Sources() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [confirmed, setConfirmed] = useState(false);

  const { data: sources, isLoading } = useQuery({
    queryKey: ['sources', runId],
    queryFn: () => api.listSources(runId!),
    enabled: !!runId,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.recommendSources(runId!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['sources', runId] });
      const autoSelected = new Set(
        result.sources
          .filter((s) => ['core', 'useful'].includes(s.recommendation_priority ?? ''))
          .map((s) => s.id),
      );
      setSelected(autoSelected);
      addToast({ type: 'success', message: `${result.count} sources generated` });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const confirmMutation = useMutation({
    mutationFn: () => api.confirmSources(runId!, Array.from(selected)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] });
      setConfirmed(true);
      addToast({ type: 'success', message: 'Sources confirmed' });
      navigate(`/runs/${runId}/pipeline`);
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  if (sources?.length && selected.size === 0 && !confirmed) {
    const preSelected = new Set(
      sources
        .filter((s) => s.user_selected || ['core', 'useful'].includes(s.recommendation_priority ?? ''))
        .map((s) => s.id),
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
          <h1 className="text-xl font-bold text-slate-900">Source Recommendations</h1>
          <p className="text-sm text-slate-500 mt-1">Select data sources for company discovery</p>
        </div>
        <div className="flex gap-2">
          {(!sources || sources.length === 0) && (
            <Button onClick={() => generateMutation.mutate()} loading={generateMutation.isPending}>
              Generate Sources
            </Button>
          )}
          {sources && sources.length > 0 && !confirmed && (
            <Button onClick={() => confirmMutation.mutate()} loading={confirmMutation.isPending} disabled={selected.size === 0}>
              Confirm {selected.size} Selected
            </Button>
          )}
        </div>
      </div>

      {generateMutation.isPending && <PageSpinner />}

      {!sources?.length && !generateMutation.isPending && (
        <EmptyState
          icon={<Database className="h-12 w-12" />}
          title="No sources yet"
          description="Generate source recommendations based on your selected sub-verticals."
          action={{ label: 'Generate', onClick: () => generateMutation.mutate() }}
        />
      )}

      {sources && sources.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="w-10 px-3 py-3" />
                <th className="w-8" />
                <th className="text-left px-3 py-3 font-medium text-slate-600">Source</th>
                <th className="text-left px-3 py-3 font-medium text-slate-600 w-28">Type</th>
                <th className="text-left px-3 py-3 font-medium text-slate-600 w-24">Priority</th>
                <th className="text-left px-3 py-3 font-medium text-slate-600 w-28">Access</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((src) => (
                <React.Fragment key={src.id}>
                  <tr className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(src.id)}
                        onChange={() => toggleSelect(src.id)}
                        className="rounded border-slate-300"
                        disabled={confirmed}
                      />
                    </td>
                    <td>
                      <button onClick={() => toggleExpand(src.id)} className="p-1 hover:bg-slate-100 rounded">
                        {expanded.has(src.id) ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                    </td>
                    <td className="px-3 py-3 font-medium text-slate-900">{src.source_name}</td>
                    <td className="px-3 py-3">
                      <Badge variant="outline">{src.source_type?.replace(/_/g, ' ')}</Badge>
                    </td>
                    <td className="px-3 py-3">
                      <PriorityBadge priority={src.recommendation_priority ?? 'optional'} />
                    </td>
                    <td className="px-3 py-3 text-xs text-slate-500">{src.access_type?.replace(/_/g, ' ')}</td>
                  </tr>
                  {expanded.has(src.id) && (
                    <tr className="bg-slate-50 border-b border-slate-100">
                      <td colSpan={6} className="px-8 py-4">
                        <div className="text-sm space-y-2">
                          <p className="text-slate-700">{src.rationale}</p>
                          {src.expected_company_type && (
                            <p className="text-xs text-slate-500">Expected: {src.expected_company_type}</p>
                          )}
                          {src.url && (
                            <p className="text-xs">
                              <a href={src.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                                {src.url}
                              </a>
                            </p>
                          )}
                          {src.mapped_subverticals?.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {src.mapped_subverticals.map((sv, i) => (
                                <Badge key={i} variant="muted">{sv}</Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
