import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { RunStatusBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { useStore } from '@/hooks/useStore';
import { formatDate } from '@/lib/utils';
import { Plus, FolderOpen } from 'lucide-react';

export function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);
  const [showCreate, setShowCreate] = useState(false);
  const [theme, setTheme] = useState('');
  const [geography, setGeography] = useState('US');
  const [revenueCeiling, setRevenueCeiling] = useState('1000');

  const { data, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: () => api.listRuns(),
  });

  const createMutation = useMutation({
    mutationFn: api.createRun,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      addToast({ type: 'success', message: 'Run created' });
      navigate(`/runs/${result.id}/subverticals`);
    },
    onError: (err) => {
      addToast({ type: 'error', message: `Failed to create run: ${err.message}` });
    },
  });

  const handleCreate = () => {
    if (!theme.trim()) return;
    createMutation.mutate({
      theme: theme.trim(),
      geography_filter: geography.split(',').map((g) => g.trim()).filter(Boolean),
      revenue_ceiling: parseFloat(revenueCeiling) || 1000,
    });
  };

  if (isLoading) return <PageSpinner />;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Origination Runs</h1>
          <p className="text-sm text-slate-500 mt-1">Create and manage borrower origination pipelines</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          New Run
        </Button>
      </div>

      {/* Create Run Dialog (inline for simplicity) */}
      {showCreate && (
        <div className="mb-8 rounded-lg border border-blue-200 bg-blue-50 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Create New Run</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Investment Theme *</label>
              <input
                type="text"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g., SaaS companies in healthcare IT"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                autoFocus
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Geography</label>
                <input
                  type="text"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  placeholder="US"
                  value={geography}
                  onChange={(e) => setGeography(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Revenue Ceiling ($M)</label>
                <input
                  type="number"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  placeholder="1000"
                  value={revenueCeiling}
                  onChange={(e) => setRevenueCeiling(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} loading={createMutation.isPending} disabled={!theme.trim()}>
                Create Run
              </Button>
              <Button variant="secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Runs Table */}
      {!data?.runs.length ? (
        <EmptyState
          icon={<FolderOpen className="h-12 w-12" />}
          title="No runs yet"
          description="Create your first origination run to get started."
          action={{ label: 'New Run', onClick: () => setShowCreate(true) }}
        />
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-medium text-slate-600">Theme</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 w-28">Status</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 w-40">Stage</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600 w-44">Created</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {data.runs.map((run) => (
                <tr
                  key={run.id}
                  className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                  onClick={() => navigate(`/runs/${run.id}/setup`)}
                >
                  <td className="px-4 py-3 font-medium text-slate-900 max-w-xs truncate">
                    {run.theme || 'Untitled'}
                  </td>
                  <td className="px-4 py-3">
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {run.current_stage?.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{formatDate(run.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-blue-600 text-xs">Open &rarr;</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
