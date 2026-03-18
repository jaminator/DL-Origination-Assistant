import { cn } from '@/lib/utils';

type Variant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'purple' | 'outline' | 'muted';

const variantClasses: Record<Variant, string> = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-red-100 text-red-700',
  purple: 'bg-purple-100 text-purple-700',
  outline: 'border border-slate-300 text-slate-600',
  muted: 'bg-slate-50 text-slate-500',
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
  dot?: string; // color for leading dot
}

export function Badge({ children, variant = 'default', className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        variantClasses[variant],
        className,
      )}
    >
      {dot && <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: dot }} />}
      {children}
    </span>
  );
}

// Disposition badges
export function DispositionBadge({ disposition }: { disposition?: string }) {
  const d = (disposition ?? '').toLowerCase();
  const map: Record<string, { variant: Variant; label: string }> = {
    primary: { variant: 'primary', label: 'Primary' },
    cascade_anchor: { variant: 'purple', label: 'Cascade' },
    exclude: { variant: 'muted', label: 'Exclude' },
    watch: { variant: 'warning', label: 'Watch' },
  };
  const cfg = map[d] ?? { variant: 'default' as Variant, label: d || '—' };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

// Ownership tier badges
export function OwnershipBadge({ tier }: { tier?: string }) {
  const t = (tier ?? '').toLowerCase();
  const map: Record<string, { variant: Variant; label: string }> = {
    tier_a: { variant: 'success', label: 'Tier A' },
    tier_b: { variant: 'primary', label: 'Tier B' },
    tier_c: { variant: 'default', label: 'Tier C' },
    unknown: { variant: 'outline', label: 'Unknown' },
  };
  const cfg = map[t] ?? { variant: 'default' as Variant, label: t || '—' };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

// Run status badges
export function RunStatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const map: Record<string, { variant: Variant; label: string }> = {
    pending: { variant: 'warning', label: 'Pending' },
    running: { variant: 'primary', label: 'Running' },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'danger', label: 'Failed' },
  };
  const cfg = map[s] ?? { variant: 'default' as Variant, label: s };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

// Recommendation status
export function RecommendationBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const map: Record<string, { variant: Variant; label: string }> = {
    strong_fit: { variant: 'success', label: 'Strong Fit' },
    moderate_fit: { variant: 'warning', label: 'Moderate Fit' },
    watchlist: { variant: 'muted', label: 'Watchlist' },
    avoid: { variant: 'danger', label: 'Avoid' },
  };
  const cfg = map[s] ?? { variant: 'default' as Variant, label: s };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

// Source priority
export function PriorityBadge({ priority }: { priority: string }) {
  const p = (priority ?? '').toLowerCase();
  const map: Record<string, { variant: Variant; label: string }> = {
    core: { variant: 'primary', label: 'Core' },
    useful: { variant: 'success', label: 'Useful' },
    optional: { variant: 'muted', label: 'Optional' },
    manual_only: { variant: 'warning', label: 'Manual' },
  };
  const cfg = map[p] ?? { variant: 'default' as Variant, label: p };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

// Data quality dot
export function QualityDot({ quality }: { quality?: string }) {
  const q = (quality ?? '').toLowerCase();
  const colors: Record<string, string> = {
    clean: '#22c55e',
    web_est: '#eab308',
    stale: '#f97316',
    all_inferred: '#ef4444',
  };
  const color = colors[q] ?? '#94a3b8';
  return (
    <span
      className="inline-block h-2 w-2 rounded-full"
      style={{ backgroundColor: color }}
      title={q || 'unknown'}
    />
  );
}

// Enrichment status dots (B/P/C)
export function EnrichmentDots({ bizapi, pitchbook, capitaliq }: { bizapi?: string; pitchbook?: string; capitaliq?: string }) {
  const color = (status?: string) => {
    const s = (status ?? '').toLowerCase();
    if (s === 'matched') return '#22c55e';
    if (s === 'not_found') return '#94a3b8';
    if (s === 'pending') return '#eab308';
    if (s === 'error') return '#ef4444';
    if (s === 'skipped') return '#3b82f6';
    return '#d1d5db';
  };
  return (
    <span className="inline-flex gap-1 items-center">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color(bizapi) }} title={`BizAPI: ${bizapi ?? '—'}`} />
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color(pitchbook) }} title={`PitchBook: ${pitchbook ?? '—'}`} />
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color(capitaliq) }} title={`Capital IQ: ${capitaliq ?? '—'}`} />
    </span>
  );
}
