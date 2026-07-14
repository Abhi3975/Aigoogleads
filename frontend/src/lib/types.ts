/** API types mirroring the backend Pydantic schemas. */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export type OrgRole = 'owner' | 'admin' | 'manager' | 'analyst' | 'viewer';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
  role: OrgRole;
}

export interface OrgMember {
  user_id: string;
  email: string;
  full_name: string | null;
  role: OrgRole;
  created_at: string;
}

export interface GoogleAdsConnection {
  id: string;
  organization_id: string;
  status: string;
  login_customer_id: string | null;
  last_synced_at: string | null;
  accounts_count: number;
}

export interface GoogleAdsAccount {
  customer_id: string;
  descriptive_name: string | null;
  currency_code: string | null;
  time_zone: string | null;
  is_manager: boolean;
  is_test_account: boolean;
}

export type MarketingGoal =
  | 'generate_leads'
  | 'increase_sales'
  | 'website_traffic'
  | 'app_installs'
  | 'brand_awareness'
  | 'local_store_visits';

export interface OnboardingPayload {
  business_name: string;
  description: string;
  industry: string;
  website_url?: string | null;
  product_service_description?: string | null;
  usp?: string | null;
  location?: string | null;
  target_countries: string[];
  target_cities: string[];
  languages: string[];
  goal: MarketingGoal;
  budget: {
    daily_budget: number;
    monthly_budget: number;
    currency: string;
    max_cpa?: number | null;
    target_roas?: number | null;
  };
  audience?: {
    age_min?: number | null;
    age_max?: number | null;
    gender?: string | null;
    locations: string[];
    interests: string[];
    pain_points: string[];
    existing_customer_profile?: string | null;
  } | null;
  products: {
    name: string;
    pricing?: string | null;
    features: string[];
    benefits: string[];
    landing_url?: string | null;
  }[];
}

export interface BusinessProfile extends OnboardingPayload {
  id: string;
  status: string;
  created_at: string;
}

export interface AgentStep {
  id: string;
  sequence: number;
  agent_name: string;
  status: string;
  reasoning: string | null;
  output: Record<string, unknown> | null;
  tool_calls: unknown[];
  usage: Record<string, number>;
  created_at: string;
}

export interface AgentRun {
  id: string;
  workflow: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  total_tokens: number;
  created_at: string;
  steps?: AgentStep[];
}

export interface CampaignBlueprint {
  id: string;
  campaign_name: string;
  campaign_type: string;
  objective: string;
  daily_budget: number;
  bidding_strategy: string;
  status: string;
  customer_id: string | null;
  google_campaign_id: string | null;
  structure: BlueprintStructure;
  created_at: string;
}

export interface BlueprintStructure {
  campaign_name: string;
  campaign_type: string;
  objective: string;
  daily_budget: number;
  bidding_strategy: string;
  location_targeting: string[];
  audience_targeting: string;
  ad_groups: {
    name: string;
    theme: string;
    keywords: { text: string; match_type: string; intent: string }[];
    negative_keywords: string[];
    ad: {
      headlines: string[];
      descriptions: string[];
      final_url: string;
    } | null;
  }[];
  shared_negative_keywords: string[];
  extensions: { sitelinks: { text: string; url?: string }[]; callouts: string[] };
  validation_warnings: string[];
}

export interface CampaignPlanResponse {
  run: AgentRun;
  blueprint: CampaignBlueprint;
}

export interface ExecutionLog {
  id: string;
  sequence: number;
  action: string;
  resource_type: string | null;
  google_resource_id: string | null;
  status: string;
  error: string | null;
  created_at: string;
}

export interface OptimizationPolicy {
  enabled: boolean;
  auto_execute: boolean;
  max_budget_increase_pct: number;
  max_budget_decrease_pct: number;
  max_bid_change_pct: number;
  min_days_active: number;
  min_clicks_required: number;
  min_keyword_clicks: number;
  min_keyword_days: number;
  min_confidence: number;
  date_range: string;
}

export interface OptimizationLog {
  id: string;
  customer_id: string | null;
  campaign_id: string | null;
  action_type: string;
  target: string | null;
  previous_value: number | null;
  new_value: number | null;
  reasoning: string | null;
  explanation: string | null;
  confidence: number;
  status: string;
  created_at: string;
}

export interface OptimizationRunSummary {
  run_id: string;
  applied: number;
  pending: number;
  rejected: number;
  failed: number;
  logs: OptimizationLog[];
}

export interface KpiTotals {
  impressions: number;
  clicks: number;
  cost: number;
  conversions: number;
  conversions_value: number;
  ctr: number;
  average_cpc: number;
  cpa: number;
  roas: number;
  conversion_rate: number;
}

export interface CampaignPerformance {
  campaign_id: string;
  campaign_name: string | null;
  cost: number;
  clicks: number;
  conversions: number;
  ctr: number;
  cpa: number;
  roas: number;
}

export interface AnalyticsSummary {
  as_of: string | null;
  totals: KpiTotals;
  campaigns: CampaignPerformance[];
}

export interface TimeseriesPoint {
  date: string;
  cost: number;
  clicks: number;
  conversions: number;
  conversions_value: number;
}

export interface AnalyticsTimeseries {
  points: TimeseriesPoint[];
}

export interface AppNotification {
  id: string;
  type: string;
  severity: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}
