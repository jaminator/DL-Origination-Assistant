import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { PageSpinner } from '@/components/ui/Spinner';
import { Card, CardTitle, CardContent } from '@/components/ui/Card';
import { RunStatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export function RunSetup() {
  const { runId } = useParams();
  const navigate = useNavigate();

  const { data: run, isLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
  });

  if (isLoading) return <PageSpinner />;
  if (!run) return <div className="p-8 text-slate-500">Run not found</div>;

  const config = run.config;

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Run Configuration</h1>
          <p className="text-sm text-slate-500 mt-1">Review the settings for this origination run</p>
        </div>
        <RunStatusBadge status={run.status} />
      </div>

      <div className="space-y-4">
        <Card>
          <CardTitle>Investment Theme</CardTitle>
          <CardContent>
            <p className="text-base font-medium text-slate-900">{config.theme}</p>
            {config.theme_notes && <p className="mt-1 text-sm text-slate-500">{config.theme_notes}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardTitle>Parameters</CardTitle>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Geography:</span>{' '}
                <span className="font-medium">{config.geography_filter?.join(', ') || 'US'}</span>
              </div>
              <div>
                <span className="text-slate-500">Revenue Ceiling:</span>{' '}
                <span className="font-medium">${config.revenue_ceiling}M</span>
              </div>
              <div>
                <span className="text-slate-500">Cascade Threshold:</span>{' '}
                <span className="font-medium">${config.cascade_anchor_threshold}M</span>
              </div>
              <div>
                <span className="text-slate-500">EBITDA Ceiling:</span>{' '}
                <span className="font-medium">${config.ebitda_soft_ceiling}M</span>
              </div>
              <div>
                <span className="text-slate-500">Recursion Depth:</span>{' '}
                <span className="font-medium">{config.max_recursion_depth}</span>
              </div>
              <div>
                <span className="text-slate-500">Boundary Treatment:</span>{' '}
                <span className="font-medium capitalize">{config.boundary_treatment}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardTitle>Scoring Bonuses</CardTitle>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Tier A:</span>{' '}
                <span className="font-medium">+{config.tier_a_scoring_bonus}</span>
              </div>
              <div>
                <span className="text-slate-500">Tier B:</span>{' '}
                <span className="font-medium">+{config.tier_b_scoring_bonus}</span>
              </div>
              <div>
                <span className="text-slate-500">Tier C:</span>{' '}
                <span className="font-medium">+{config.tier_c_scoring_bonus}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3 pt-4">
          <Button onClick={() => navigate(`/runs/${runId}/subverticals`)}>
            Continue to Sub-Verticals &rarr;
          </Button>
        </div>
      </div>
    </div>
  );
}
