// Backend API types matching Python Pydantic schemas

export interface RunSummary {
  id: string;
  theme: string;
  status: string;
  current_stage: string;
  created_at: string;
  updated_at: string;
}

export interface RunListResponse {
  total: number;
  limit: number;
  offset: number;
  runs: RunSummary[];
}

export interface RunDetail {
  id: string;
  config: RunConfig;
  current_stage: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RunConfig {
  theme: string;
  theme_notes?: string;
  industry_description?: string;
  geography_filter: string[];
  revenue_ceiling: number;
  cascade_anchor_threshold: number;
  ebitda_soft_ceiling: number;
  max_recursion_depth: number;
  profile_name?: string;
  tier_a_scoring_bonus: number;
  tier_b_scoring_bonus: number;
  tier_c_scoring_bonus: number;
  include_cascade_anchors_in_outreach: boolean;
  boundary_treatment: string;
}

export interface CreateRunRequest {
  theme: string;
  theme_notes?: string;
  industry_description?: string;
  geography_filter?: string[];
  revenue_ceiling?: number;
  cascade_anchor_threshold?: number;
  ebitda_soft_ceiling?: number;
  max_recursion_depth?: number;
  profile_name?: string;
  tier_a_scoring_bonus?: number;
  tier_b_scoring_bonus?: number;
  tier_c_scoring_bonus?: number;
  include_cascade_anchors_in_outreach?: boolean;
  boundary_treatment?: string;
}

export interface SubVertical {
  id: string;
  subvertical_name: string;
  description: string;
  thematic_fit_explanation: string;
  lender_fit_explanation: string;
  thematic_fit_score: number;
  lender_fit_score: number;
  total_recommendation_score: number;
  recommendation_status: RecommendationStatus;
  demand_profile: string;
  cyclicality_profile: string;
  recurring_revenue_profile: string;
  margin_profile: string;
  capital_intensity_profile: string;
  ownership_landscape: string;
  example_borrower_archetypes: string[];
  reasons_to_lend: string[];
  reasons_not_to_lend: string[];
  confidence: number;
  user_selected: boolean;
  data?: Record<string, unknown>;
}

export type RecommendationStatus = 'strong_fit' | 'moderate_fit' | 'watchlist' | 'avoid';

export interface SourceRecommendation {
  id: string;
  source_name: string;
  source_type: string;
  url?: string;
  mapped_subverticals: string[];
  rationale: string;
  expected_company_type: string;
  expected_data_quality: string;
  access_type: string;
  recommendation_priority: SourcePriority;
  user_selected: boolean;
  data?: Record<string, unknown>;
}

export type SourcePriority = 'core' | 'useful' | 'optional' | 'manual_only';

export interface Company {
  id: string;
  canonical_name: string;
  data: CompanyData;
}

export interface CompanyData {
  canonical_name: string;
  name_variants?: string[];
  website?: string;
  hq_city?: string;
  hq_state?: string;
  hq_country?: string;
  founded_year?: number;
  employee_count?: number;
  subvertical_tags?: string[];
  industry_exposure_descriptor?: string;
  industry_exposure_intensity?: string;
  ownership_tier?: string;
  disposition?: string;
  is_public?: boolean;
  revenue_estimate?: number;
  revenue_quality?: string;
  revenue_source?: string;
  ebitda_estimate?: number;
  ebitda_quality?: string;
  recurring_revenue_estimate?: number;
  pb_status?: string;
  pb_entity_id?: string;
  sponsor_names?: string[];
  investor_names?: string[];
  has_debt?: boolean;
  lender_names?: string[];
  facility_type?: string;
  facility_amount?: number;
  pricing?: string;
  close_date?: string;
  maturity_date?: string;
  bizapi_status?: string;
  bizapi_duns?: string;
  bizapi_match_confidence?: number;
  naics_code?: string;
  naics_description?: string;
  sic_code?: string;
  sic_description?: string;
  ciq_status?: string;
  ciq_entity_id?: string;
  ciq_revenue?: number;
  ciq_ebitda?: number;
  ciq_total_debt?: number;
  ciq_net_debt?: number;
  ciq_ownership_type?: string;
  ciq_key_investors?: string[];
  total_score?: number;
  score_components?: Record<string, number>;
  eligible_for_outreach?: boolean;
  review_required?: boolean;
  review_reasons?: string[];
  ai_provenance?: Record<string, unknown>;
  source_tags?: string[];
  workflow_stage?: string;
}

export interface CompanyListResponse {
  run_id: string;
  total: number;
  limit: number;
  offset: number;
  companies: Company[];
}

export interface ReviewQueueItem {
  id: string;
  reason: string;
  details: string;
  resolved: boolean;
  resolution?: string;
  candidate_a?: Record<string, unknown>;
  candidate_b?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export interface Checkpoint {
  id: string;
  stage: string;
  company_count: number;
  created_at: string;
  notes: string;
}

export interface ExportManifest {
  id: string;
  created_at: string;
  data: Record<string, unknown>;
}

export interface ConnectorStatus {
  connectors: Record<string, { available: boolean; message: string }>;
  registered: string[];
}

export interface ExecuteResponse {
  status: 'accepted' | 'completed';
  job_id?: string;
  run_id: string;
  result?: Record<string, unknown>;
}

export interface RunStatus {
  id: string;
  current_stage: string;
  status: string;
}

// Pipeline stage names in execution order
export const PIPELINE_STAGES = [
  'name_generation',
  'name_normalization',
  'web_enhancement',
  'dispositioning',
  'bizapi_enrichment',
  'pitchbook_enrichment',
  'capitaliq_enrichment',
  'cascade_expansion',
  'final_dedup',
  'qa_validation',
  'scoring',
  'export',
] as const;

export const STAGE_LABELS: Record<string, string> = {
  name_generation: 'Name Generation',
  name_normalization: 'Name Normalization',
  web_enhancement: 'Web Enhancement',
  dispositioning: 'Dispositioning',
  bizapi_enrichment: 'BizAPI Enrichment',
  pitchbook_enrichment: 'PitchBook Enrichment',
  capitaliq_enrichment: 'Capital IQ Enrichment',
  cascade_expansion: 'Cascade Expansion',
  final_dedup: 'Final Dedup',
  qa_validation: 'QA Validation',
  scoring: 'Scoring',
  export: 'Export',
};
