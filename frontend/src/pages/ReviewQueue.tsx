import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { Card, CardTitle, CardContent } from '@/components/ui/Card';
import { useStore } from '@/hooks/useStore';
import { cn } from '@/lib/utils';
import { CheckCircle } from 'lucide-react';
import type { ReviewQueueItem } from '@/types/api';

const REASON_COLORS: Record<string, string> = {
  ambiguous_duplicate: 'warning',
  conflicting_enrichment: 'danger',
  weak_enrichment_match: 'default',
  unknown_ownership: 'purple',
  data_completeness: 'default',
  cascade_anchor_bleed: 'purple',
  mega_cap: 'danger',
  geography: 'warning',
  score_sanity: 'danger',
  acquisition_merger: 'primary',
};

const RESOLUTION_OPTIONS: Record<string, string[]> = {
  ambiguous_duplicate: ['merge', 'keep_both', 'exclude'],
  conflicting_enrichment: ['accept', 'reject', 'flag_for_research'],
  weak_enrichment_match: ['accept', 'reject'],
  unknown_ownership: ['accept_risk', 'exclude', 'escalate'],
  data_completeness: ['accept_risk', 'exclude'],
  cascade_anchor_bleed: ['accept', 'exclude'],
  mega_cap: ['accept_risk', 'exclude'],
  geography: ['accept_risk', 'exclude'],
  score_sanity: ['accept_risk', 'exclude', 'flag_for_research'],
};

export function ReviewQueue() {
  const { runId } = useParams();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);
  const [filter, setFilter] = useState<'all' | 'unresolved' | 'resolved'>('unresolved');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const resolvedParam = filter === 'all' ? undefined : filter === 'resolved';
  const { data: items, isLoading } = useQuery({
    queryKey: ['review-queue', runId, filter],
    queryFn: () => api.listReviewQueue(runId!, resolvedParam),
    enabled: !!runId,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ itemId, resolution }: { itemId: string; resolution: string }) =>
      api.resolveReviewItem(runId!, itemId, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue', runId] });
      addToast({ type: 'success', message: 'Item resolved' });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const selectedItem = items?.find((i) => i.id === selectedId);
  const unresolvedCount = items?.filter((i) => !i.resolved).length ?? 0;

  if (isLoading) return <PageSpinner />;

  return (
    <div className="flex h-full">
      {/* Left: Queue table */}
      <div className="w-2/5 border-r border-slate-200 overflow-y-auto">
        <div className="p-4 border-b border-slate-200 bg-white sticky top-0 z-10">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-lg font-bold text-slate-900">Review Queue</h1>
            {unresolvedCount > 0 && (
              <Badge variant="warning">{unresolvedCount} unresolved</Badge>
            )}
          </div>
          <div className="flex gap-1">
            {(['unresolved', 'all', 'resolved'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  'px-3 py-1 rounded-md text-xs font-medium transition-colors',
                  filter === f ? 'bg-blue-100 text-blue-700' : 'text-slate-500 hover:bg-slate-100',
                )}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {!items?.length ? (
          <EmptyState
            icon={<CheckCircle className="h-10 w-10" />}
            title="All clear"
            description="No review items to triage."
          />
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => setSelectedId(item.id)}
                className={cn(
                  'w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors',
                  selectedId === item.id && 'bg-blue-50',
                  item.resolved && 'opacity-50',
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={(REASON_COLORS[item.reason] ?? 'default') as 'default'}>
                    {item.reason.replace(/_/g, ' ')}
                  </Badge>
                  {item.resolved && <Badge variant="success">Resolved</Badge>}
                </div>
                <p className="text-xs text-slate-600 line-clamp-2">{item.details}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: Detail / triage */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selectedItem ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-400">
            Select an item to review
          </div>
        ) : (
          <ReviewDetail item={selectedItem} onResolve={(resolution) => resolveMutation.mutate({ itemId: selectedItem.id, resolution })} isResolving={resolveMutation.isPending} />
        )}
      </div>
    </div>
  );
}

function ReviewDetail({
  item,
  onResolve,
  isResolving,
}: {
  item: ReviewQueueItem;
  onResolve: (resolution: string) => void;
  isResolving: boolean;
}) {
  const options = RESOLUTION_OPTIONS[item.reason] ?? ['accept', 'reject'];

  return (
    <div className="space-y-6">
      <div>
        <Badge variant={(REASON_COLORS[item.reason] ?? 'default') as 'default'} className="mb-2">
          {item.reason.replace(/_/g, ' ')}
        </Badge>
        <p className="text-sm text-slate-700">{item.details}</p>
      </div>

      {/* Side-by-side comparison for duplicates/conflicts */}
      {item.candidate_a && item.candidate_b && (
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardTitle>Candidate A</CardTitle>
            <CardContent>
              <pre className="text-xs whitespace-pre-wrap text-slate-600">
                {JSON.stringify(item.candidate_a, null, 2)}
              </pre>
            </CardContent>
          </Card>
          <Card>
            <CardTitle>Candidate B</CardTitle>
            <CardContent>
              <pre className="text-xs whitespace-pre-wrap text-slate-600">
                {JSON.stringify(item.candidate_b, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Resolution buttons */}
      {!item.resolved ? (
        <div className="flex gap-2 pt-4 border-t border-slate-200">
          {options.map((opt) => (
            <Button
              key={opt}
              variant={opt === 'exclude' || opt === 'reject' ? 'danger' : opt === 'accept' || opt === 'merge' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => onResolve(opt)}
              loading={isResolving}
            >
              {opt.replace(/_/g, ' ')}
            </Button>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 pt-4 border-t border-slate-200">
          <Badge variant="success">Resolved</Badge>
          <span className="text-sm text-slate-600">{item.resolution}</span>
        </div>
      )}
    </div>
  );
}
