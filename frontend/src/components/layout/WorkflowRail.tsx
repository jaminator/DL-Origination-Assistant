import { cn } from '@/lib/utils';
import { NavLink, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  LayoutDashboard,
  Lightbulb,
  Database,
  Play,
  AlertTriangle,
  Building2,
  Download,
} from 'lucide-react';

interface Step {
  label: string;
  path: string;
  icon: React.ReactNode;
  requiresStage?: string[];
}

const WORKFLOW_STEPS: Step[] = [
  { label: 'Setup', path: 'setup', icon: <LayoutDashboard className="h-4 w-4" /> },
  { label: 'Sub-Verticals', path: 'subverticals', icon: <Lightbulb className="h-4 w-4" /> },
  { label: 'Sources', path: 'sources', icon: <Database className="h-4 w-4" /> },
  { label: 'Pipeline', path: 'pipeline', icon: <Play className="h-4 w-4" /> },
  { label: 'Review', path: 'review', icon: <AlertTriangle className="h-4 w-4" /> },
  { label: 'Companies', path: 'companies', icon: <Building2 className="h-4 w-4" /> },
  { label: 'Export', path: 'exports', icon: <Download className="h-4 w-4" /> },
];

// Map backend stages to step indices for progress indication
const STAGE_TO_STEP: Record<string, number> = {
  theme_intake: 0,
  subvertical_recommendation: 1,
  subvertical_confirmation: 1,
  source_recommendation: 2,
  source_confirmation: 2,
  name_generation: 3,
  name_normalization: 3,
  web_enhancement: 3,
  dispositioning: 3,
  bizapi_enrichment: 3,
  pitchbook_enrichment: 3,
  capitaliq_enrichment: 3,
  cascade_expansion: 3,
  final_dedup: 3,
  qa_validation: 3,
  scoring: 3,
  export: 6,
  completed: 6,
};

export function WorkflowRail() {
  const { runId } = useParams();

  const { data: run } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' ? 2000 : false;
    },
  });

  const currentStepIndex = run ? (STAGE_TO_STEP[run.current_stage] ?? 0) : 0;
  const isComplete = run?.status === 'completed';

  return (
    <nav className="w-52 shrink-0 border-r border-slate-200 bg-slate-50 p-4">
      <div className="mb-6">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Workflow</h3>
        {run && (
          <p className="text-xs text-slate-500 truncate" title={run.config?.theme}>
            {run.config?.theme}
          </p>
        )}
      </div>
      <ul className="space-y-1">
        {WORKFLOW_STEPS.map((step, idx) => {
          const isActiveOrPast = idx <= currentStepIndex || isComplete;
          return (
            <li key={step.path}>
              <NavLink
                to={`/runs/${runId}/${step.path}`}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : isActiveOrPast
                        ? 'text-slate-700 hover:bg-slate-100'
                        : 'text-slate-400 cursor-default',
                  )
                }
              >
                <span className="shrink-0">{step.icon}</span>
                <span>{step.label}</span>
                {idx < currentStepIndex && isComplete === false && (
                  <span className="ml-auto text-green-500 text-xs">&#10003;</span>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
