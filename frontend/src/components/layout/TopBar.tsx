import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { Settings } from 'lucide-react';

export function TopBar() {
  const { data: connectors } = useQuery({
    queryKey: ['connectors'],
    queryFn: api.getConnectorStatus,
    refetchInterval: 30000,
    retry: 1,
  });

  const isMockMode = connectors
    ? Object.values(connectors.connectors).every((c) => !c.available)
    : false;

  return (
    <header className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-6 shrink-0">
      <Link to="/" className="flex items-center gap-3 text-slate-900 hover:text-blue-600 transition-colors">
        <span className="text-lg font-bold tracking-tight">DL Origination</span>
      </Link>

      <div className="flex items-center gap-4">
        {isMockMode && (
          <Badge variant="warning">Mock Mode</Badge>
        )}

        {connectors && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {Object.entries(connectors.connectors).map(([name, status]) => (
              <span key={name} className="flex items-center gap-1">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: status.available ? '#22c55e' : '#eab308' }}
                />
                <span>{name}</span>
              </span>
            ))}
          </div>
        )}

        <Link to="/settings" className="p-2 rounded-md hover:bg-slate-100 text-slate-500">
          <Settings className="h-4 w-4" />
        </Link>

        <span className="text-xs text-slate-400">Local Developer</span>
      </div>
    </header>
  );
}
