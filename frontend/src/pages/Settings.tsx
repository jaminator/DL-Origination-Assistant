import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { PageSpinner } from '@/components/ui/Spinner';
import { Card, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export function Settings() {
  const { data: connectors, isLoading } = useQuery({
    queryKey: ['connectors'],
    queryFn: api.getConnectorStatus,
  });

  if (isLoading) return <PageSpinner />;

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-xl font-bold text-slate-900 mb-6">Settings</h1>

      <div className="space-y-4">
        <Card>
          <CardTitle>Environment</CardTitle>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-slate-500 w-32">Mode:</span>
                <Badge variant="warning">Local Dev</Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-500 w-32">User:</span>
                <span>Local Developer</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardTitle>Connector Status</CardTitle>
          <CardContent>
            {connectors ? (
              <div className="space-y-2">
                {Object.entries(connectors.connectors).map(([name, status]) => (
                  <div key={name} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <span className="text-sm font-medium text-slate-700">{name}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={status.available ? 'success' : 'warning'}>
                        {status.available ? 'Available' : 'Unavailable'}
                      </Badge>
                      <span className="text-xs text-slate-400">{status.message}</span>
                    </div>
                  </div>
                ))}
                {connectors.registered.length > 0 && (
                  <div className="mt-3 text-xs text-slate-400">
                    Registered: {connectors.registered.join(', ')}
                  </div>
                )}
              </div>
            ) : (
              <span className="text-sm text-slate-500">Unable to load connector status</span>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
