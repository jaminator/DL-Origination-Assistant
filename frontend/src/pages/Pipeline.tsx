import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { PIPELINE_STAGES, STAGE_LABELS } from '@/types/api';
import { Button } from '@/components/ui/Button';
import { Badge, RunStatusBadge } from '@/components/ui/Badge';
import { useStore } from '@/hooks/useStore';
import { cn } from '@/lib/utils';
import { Spinner } from '@/components/ui/Spinner';
import { CheckCircle2, XCircle, Circle, RotateCcw } from 'lucide-react';

type StageStatus = 'pending' | 'running' | 'complete' | 'failed';

function getStageStatuses(currentStage: string, runStatus: string): Record<string, StageStatus> {
  const statuses: Record<string, StageStatus> = {};
  const stageIndex = PIPELINE_STAGES.indexOf(currentStage as typeof PIPELINE_STAGES[number]);

  for (let i = 0; i < PIPELINE_STAGES.length; i++) {
    const stage = PIPELINE_STAGES[i];
    if (runStatus === 'completed') {
      statuses[stage] = 'complete';
    } else if (runStatus === 'failed') {
      if (i < stageIndex) statuses[stage] = 'complete';
      else if (i === stageIndex) statuses[stage] = 'failed';
      else statuses[stage] = 'pending';
    } else if (runStatus === 'running') {
      if (i < stageIndex) statuses[stage] = 'complete';
      else if (i === stageIndex) statuses[stage] = 'running';
      else statuses[stage] = 'pending';
    } else {
      statuses[stage] = 'pending';
    }
  }
  return statuses;
}

export function Pipeline() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);

  const { data: run } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' ? 2000 : false;
    },
  });

  const { data: connectors } = useQuery({
    queryKey: ['connectors'],
    queryFn: api.getConnectorStatus,
    retry: 1,
  });

  const { data: checkpoints } = useQuery({
    queryKey: ['checkpoints', runId],
    queryFn: () => api.listCheckpoints(runId!),
    enabled: !!runId,
    refetchInterval: (_query) => {
      return run?.status === 'running' ? 5000 : false;
    },
  });

  const executeMutation = useMutation({
    mutationFn: () => api.executeRun(runId!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] });
      queryClient.invalidateQueries({ queryKey: ['checkpoints', runId] });
      if (result.status === 'completed') {
        addToast({ type: 'success', message: 'Pipeline completed (inline mode)' });
      } else {
        addToast({ type: 'info', message: 'Pipeline started' });
      }
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const resumeMutation = useMutation({
    mutationFn: () => api.resumeRun(runId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] });
      addToast({ type: 'info', message: 'Pipeline resumed' });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const rerunMutation = useMutation({
    mutationFn: (stage: string) => api.rerunStage(runId!, stage),
    onSuccess: (_, stage) => {
      queryClient.invalidateQueries({ queryKey: ['run', runId] });
      addToast({ type: 'success', message: `Stage "${STAGE_LABELS[stage]}" rerun complete` });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  const status = run?.status ?? 'pending';
  const currentStage = run?.current_stage ?? '';
  const stageStatuses = getStageStatuses(currentStage, status);
  const isRunning = status === 'running';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  const isPending = !isRunning && !isCompleted && !isFailed;

  // Find checkpoint data per stage
  const checkpointByStage: Record<string, { company_count: number }> = {};
  checkpoints?.forEach((cp) => {
    checkpointByStage[cp.stage] = { company_count: cp.company_count };
  });

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Pipeline Execution</h1>
          <p className="text-sm text-slate-500 mt-1">12-stage borrower mining and enrichment pipeline</p>
        </div>
        <RunStatusBadge status={status} />
      </div>

      {/* Connector status */}
      {connectors && (
        <div className="flex gap-3 mb-6">
          {Object.entries(connectors.connectors).map(([name, info]) => (
            <Badge key={name} variant={info.available ? 'success' : 'warning'}>
              {name}: {info.available ? 'Live' : 'Mock'}
            </Badge>
          ))}
        </div>
      )}

      {/* Stage timeline */}
      <div className="space-y-1 mb-8">
        {PIPELINE_STAGES.map((stage) => {
          const ss = stageStatuses[stage];
          const cpData = checkpointByStage[stage];
          return (
            <div
              key={stage}
              className={cn(
                'flex items-center gap-3 rounded-lg px-4 py-3 border',
                ss === 'complete' ? 'border-green-200 bg-green-50' :
                ss === 'running' ? 'border-blue-200 bg-blue-50' :
                ss === 'failed' ? 'border-red-200 bg-red-50' :
                'border-slate-100 bg-white',
              )}
            >
              {/* Status icon */}
              <span className="shrink-0">
                {ss === 'complete' && <CheckCircle2 className="h-5 w-5 text-green-600" />}
                {ss === 'running' && <Spinner className="h-5 w-5" />}
                {ss === 'failed' && <XCircle className="h-5 w-5 text-red-600" />}
                {ss === 'pending' && <Circle className="h-5 w-5 text-slate-300" />}
              </span>

              {/* Stage name */}
              <span className={cn('flex-1 text-sm font-medium', ss === 'pending' ? 'text-slate-400' : 'text-slate-900')}>
                {STAGE_LABELS[stage] ?? stage}
              </span>

              {/* Checkpoint data */}
              {cpData && (
                <span className="text-xs text-slate-500">{cpData.company_count} companies</span>
              )}

              {/* Rerun button */}
              {(ss === 'complete' || ss === 'failed') && !isRunning && (
                <button
                  onClick={() => rerunMutation.mutate(stage)}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  disabled={rerunMutation.isPending}
                >
                  <RotateCcw className="h-3 w-3" />
                  Rerun
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        {isPending && (
          <Button onClick={() => executeMutation.mutate()} loading={executeMutation.isPending}>
            Execute Pipeline
          </Button>
        )}
        {isFailed && (
          <Button onClick={() => resumeMutation.mutate()} loading={resumeMutation.isPending}>
            Resume from Checkpoint
          </Button>
        )}
        {isCompleted && (
          <>
            <Button onClick={() => navigate(`/runs/${runId}/companies`)}>
              View Companies &rarr;
            </Button>
            <Button variant="secondary" onClick={() => navigate(`/runs/${runId}/exports`)}>
              Export Results
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
