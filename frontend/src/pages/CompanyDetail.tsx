import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { PageSpinner } from '@/components/ui/Spinner';
import { DispositionBadge, OwnershipBadge, Badge, QualityDot } from '@/components/ui/Badge';
import { ScoreBreakdown } from '@/components/ui/ScoreBar';
import { Card, CardTitle, CardContent } from '@/components/ui/Card';
import { formatCurrency } from '@/lib/utils';
import { Check, AlertTriangle, ExternalLink } from 'lucide-react';

interface Props {
  runId: string;
  companyId: string;
}

export function CompanyDetail({ runId, companyId }: Props) {
  const { data: company, isLoading } = useQuery({
    queryKey: ['company', runId, companyId],
    queryFn: () => api.getCompany(runId, companyId),
  });

  if (isLoading) return <PageSpinner />;
  if (!company) return <div className="text-slate-500 p-4">Company not found</div>;

  const d = company.data;
  const score = d.total_score;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h2 className="text-lg font-bold text-slate-900">{d.canonical_name}</h2>
          {d.website && (
            <a href={d.website.startsWith('http') ? d.website : `https://${d.website}`} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-blue-700">
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <DispositionBadge disposition={d.disposition} />
          <OwnershipBadge tier={d.ownership_tier} />
          {d.eligible_for_outreach && <Badge variant="success"><Check className="h-3 w-3" /> Outreach</Badge>}
          {d.review_required && <Badge variant="warning"><AlertTriangle className="h-3 w-3" /> Review</Badge>}
        </div>
      </div>

      {/* Score */}
      <Card>
        <CardTitle>
          Score: {score != null ? <span className="text-2xl font-bold ml-2">{score.toFixed(0)}</span> : '—'}
        </CardTitle>
        <CardContent>
          <ScoreBreakdown
            components={d.score_components}
            ownershipBonus={
              d.ownership_tier === 'tier_a' ? 15 :
              d.ownership_tier === 'tier_b' ? 8 : 0
            }
          />
        </CardContent>
      </Card>

      {/* Financials */}
      <Card>
        <CardTitle>Financials</CardTitle>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-slate-500 mb-0.5 flex items-center gap-1">
                Revenue <QualityDot quality={d.revenue_quality} />
              </div>
              <div className="text-sm font-medium">{formatCurrency(d.revenue_estimate)}</div>
              {d.revenue_source && <div className="text-xs text-slate-400">{d.revenue_source}</div>}
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-0.5 flex items-center gap-1">
                EBITDA <QualityDot quality={d.ebitda_quality} />
              </div>
              <div className="text-sm font-medium">{formatCurrency(d.ebitda_estimate)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-0.5">Recurring Revenue</div>
              <div className="text-sm font-medium">{formatCurrency(d.recurring_revenue_estimate)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Location & Industry */}
      <Card>
        <CardTitle>Location & Industry</CardTitle>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-500">HQ:</span>{' '}
              {[d.hq_city, d.hq_state, d.hq_country].filter(Boolean).join(', ') || '—'}
            </div>
            <div>
              <span className="text-slate-500">Founded:</span> {d.founded_year ?? '—'}
            </div>
            <div>
              <span className="text-slate-500">Employees:</span> {d.employee_count?.toLocaleString() ?? '—'}
            </div>
            <div>
              <span className="text-slate-500">Industry:</span>{' '}
              {d.industry_exposure_descriptor ?? '—'}
              {d.industry_exposure_intensity && (
                <Badge variant="muted" className="ml-1">{d.industry_exposure_intensity}</Badge>
              )}
            </div>
          </div>
          {d.subvertical_tags && d.subvertical_tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {d.subvertical_tags.map((t, i) => (
                <Badge key={i} variant="muted">{t}</Badge>
              ))}
            </div>
          )}
          {(d.naics_code || d.sic_code) && (
            <div className="mt-2 text-xs text-slate-400">
              {d.naics_code && <span>NAICS: {d.naics_code} {d.naics_description && `(${d.naics_description})`}</span>}
              {d.naics_code && d.sic_code && ' | '}
              {d.sic_code && <span>SIC: {d.sic_code} {d.sic_description && `(${d.sic_description})`}</span>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enrichment Status */}
      <Card>
        <CardTitle>Enrichment Status</CardTitle>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {[
              { name: 'BizAPI', status: d.bizapi_status, id: d.bizapi_duns },
              { name: 'PitchBook', status: d.pb_status, id: d.pb_entity_id },
              { name: 'Capital IQ', status: d.ciq_status, id: d.ciq_entity_id },
            ].map((provider) => (
              <div key={provider.name}>
                <div className="text-xs text-slate-500 mb-0.5">{provider.name}</div>
                <Badge variant={
                  provider.status === 'matched' ? 'success' :
                  provider.status === 'error' ? 'danger' :
                  provider.status === 'pending' ? 'warning' : 'muted'
                }>
                  {provider.status ?? '—'}
                </Badge>
                {provider.id && <div className="text-xs text-slate-400 mt-0.5">{provider.id}</div>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Ownership & Capital Structure */}
      {(d.sponsor_names?.length || d.investor_names?.length || d.has_debt) && (
        <Card>
          <CardTitle>Ownership & Capital Structure</CardTitle>
          <CardContent>
            {(d.sponsor_names?.length ?? 0) > 0 && (
              <div className="mb-2">
                <span className="text-xs text-slate-500">Sponsors: </span>
                {d.sponsor_names?.map((s, i) => <Badge key={i} variant="outline" className="mr-1">{s}</Badge>)}
              </div>
            )}
            {(d.investor_names?.length ?? 0) > 0 && (
              <div className="mb-2">
                <span className="text-xs text-slate-500">Investors: </span>
                {d.investor_names?.map((s, i) => <Badge key={i} variant="outline" className="mr-1">{s}</Badge>)}
              </div>
            )}
            {(d.lender_names?.length ?? 0) > 0 && (
              <div className="mb-2">
                <span className="text-xs text-slate-500">Lenders: </span>
                {d.lender_names?.map((s, i) => <Badge key={i} variant="outline" className="mr-1">{s}</Badge>)}
              </div>
            )}
            {d.has_debt && (
              <div className="grid grid-cols-2 gap-3 mt-3 text-sm">
                {d.facility_type && <div><span className="text-slate-500">Facility:</span> {d.facility_type}</div>}
                {d.facility_amount && <div><span className="text-slate-500">Amount:</span> {formatCurrency(d.facility_amount)}</div>}
                {d.pricing && <div><span className="text-slate-500">Pricing:</span> {d.pricing}</div>}
                {d.maturity_date && <div><span className="text-slate-500">Maturity:</span> {d.maturity_date}</div>}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Review flags */}
      {d.review_reasons && d.review_reasons.length > 0 && (
        <Card>
          <CardTitle>Review Flags</CardTitle>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {d.review_reasons.map((r, i) => (
                <Badge key={i} variant="warning">{r.replace(/_/g, ' ')}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
