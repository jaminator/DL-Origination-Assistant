import { cn } from '@/lib/utils';

interface ScoreBarProps {
  score: number | null | undefined;
  max?: number;
  className?: string;
  showLabel?: boolean;
}

export function ScoreBar({ score, max = 100, className, showLabel = true }: ScoreBarProps) {
  const value = score ?? 0;
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-amber-400' : 'bg-red-400';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden min-w-[60px]">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <span className="text-xs font-medium text-slate-600 w-7 text-right">{score != null ? score.toFixed(0) : '—'}</span>}
    </div>
  );
}

interface ScoreBreakdownProps {
  components: Record<string, number> | undefined;
  ownershipBonus?: number;
}

const COMPONENT_CONFIG = [
  { key: 'revenue_scale', label: 'Revenue Scale', max: 20 },
  { key: 'ebitda_margin', label: 'EBITDA Margin', max: 15 },
  { key: 'recurring_revenue', label: 'Recurring Rev', max: 15 },
  { key: 'industry_exposure', label: 'Industry', max: 20 },
  { key: 'data_completeness', label: 'Data Complete', max: 15 },
];

export function ScoreBreakdown({ components, ownershipBonus }: ScoreBreakdownProps) {
  if (!components) return <span className="text-sm text-slate-400">No score data</span>;

  return (
    <div className="space-y-2">
      {COMPONENT_CONFIG.map(({ key, label, max }) => {
        const value = components[key] ?? 0;
        const pct = Math.min(100, (value / max) * 100);
        const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-28 shrink-0">{label}</span>
            <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
              <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs font-medium text-slate-700 w-14 text-right">
              {value.toFixed(1)}/{max}
            </span>
          </div>
        );
      })}
      {ownershipBonus != null && ownershipBonus > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 w-28 shrink-0">Ownership Bonus</span>
          <div className="flex-1" />
          <span className="text-xs font-medium text-blue-600 w-14 text-right">+{ownershipBonus}</span>
        </div>
      )}
    </div>
  );
}
