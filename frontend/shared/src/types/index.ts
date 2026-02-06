// JobSeeker AI Shared Types

// ============= User Types =============
export interface UserResumeSummary {
  id: string;
  file_name?: string;
  url?: string;
  uploaded_at: string;
  full_name?: string;
  skills: string[];
  parse_quality_score?: number;
  total_experience_years?: number;
  work_experience_count?: number;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  resume?: UserResumeSummary;
}

export interface UserProfile {
  id: string;
  user_id: string;
  profession?: string;
  job_title?: string;
  skills: string[];
  experience_years?: number;
  experience?: string;
  education?: string;
  certifications: string[];
  preferences: {
    remote_only?: boolean;
    industries?: string[];
    job_types?: string[];
    avoid_keywords?: string[];
  };
  min_rate_usd?: number;
  location?: string;
  portfolio?: Record<string, any>;
  timezone?: string;
  created_at: string;
  updated_at: string;
}

// ============= Job Types =============
export interface Job {
  id: string;
  title: string;
  company: string;
  description: string;
  skills?: string[];
  requirements?: Record<string, any>;
  rate_min?: number;
  rate_max?: number;
  rate_type: string;
  location?: string;
  remote: boolean;
  employment_type: string;
  hours_per_week?: number;
  posted_at: string;
  source: string;
  url: string;
  created_at: string;
  updated_at: string;
}

export interface ScoreBreakdown {
  semantic_similarity: number;
  skill_match: number;
  experience_match: number;
  compensation_match: number;
  location_match: number;
  freshness_score: number;
  preference_match: number;
}

export interface ScoredJob extends Job {
  total_score: number;
  score_breakdown: ScoreBreakdown;
  explanation: string;
  recommended: boolean;
}

// ============= Job Match Types =============
export type JobMatchStatus =
  | 'new'
  | 'saved'
  | 'applied'
  | 'interviewing'
  | 'hired'
  | 'rejected'
  | 'pending'
  | 'viewed';

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  job: Job;
  total_score: number;
  score_breakdown: Record<string, number>;
  explanation: string;
  status: JobMatchStatus;
  client_notes?: string;
  proposal_version?: number;
  created_at: string;
  updated_at: string;
}

// ============= Filter Types =============
export interface JobFilters {
  remote_only?: boolean;
  min_rate?: number;
  max_rate?: number;
  source?: string;
  location?: string;
  rate_type?: 'hourly' | 'fixed' | 'annual';
}

// ============= Search Types =============
export interface SearchQuery {
  keywords?: string[];
  profession?: string;
  location?: string;
  remote_only?: boolean;
  min_rate?: number;
  max_rate?: number;
  limit?: number;
}

export interface SearchResponse {
  success: boolean;
  total_results: number;
  source_stats: Record<string, number>;
  jobs: ScoredJob[];
  error?: string;
}

// ============= Proposal Types =============
export type ProposalTone = 'short' | 'medium' | 'full';

export type EnhancementType =
  | 'add_keywords'
  | 'improve_tone'
  | 'add_metrics'
  | 'shorten'
  | 'expand';

export interface GeneratedProposal {
  content: string;
  tone: ProposalTone;
  word_count: number;
  keywords_used: string[];
  experience_highlighted: string[];
}

export interface AllTonesResponse {
  short: GeneratedProposal;
  medium: GeneratedProposal;
  full: GeneratedProposal;
}

export interface ParsedJD {
  title?: string;
  company?: string;
  required_skills: string[];
  nice_to_have_skills: string[];
  experience_level?: string;
  experience_years_min?: number;
  experience_years_max?: number;
  compensation_min?: number;
  compensation_max?: number;
  compensation_type?: string;
  location?: string;
  remote: boolean;
  employment_type?: string;
  key_requirements: string[];
  keywords_to_emphasize: string[];
  responsibilities: string[];
  benefits: string[];
}

// ============= Resume Types =============
export interface WorkExperience {
  id: string;
  company: string;
  title: string;
  location?: string;
  employment_type?: string;
  is_remote: boolean;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
  achievements: string[];
  skills_used: string[];
  metrics: Record<string, any>;
  duration_months: number;
  duration_text: string;
}

export interface EducationEntry {
  degree?: string;
  field?: string;
  school?: string;
  year?: string;
  gpa?: string;
}

export interface Resume {
  id: string;
  user_id: string;
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  summary?: string;
  skills: string[];
  education: EducationEntry[];
  certifications: string[];
  languages: string[];
  file_name?: string;
  file_type?: string;
  file_size?: number;
  parsed_at?: string;
  parse_quality_score?: number;
  total_experience_years: number;
  work_experiences: WorkExperience[];
  created_at: string;
  updated_at: string;
}

// ============= Subscription Types =============
export type SubscriptionTier = 'free' | 'starter' | 'pro' | 'power';

export interface TierFeatures {
  proposal_tones: ProposalTone[];
  proposal_enhance: boolean;
  auto_apply: boolean;
  priority_support: boolean;
  analytics: boolean;
}

export interface TierLimits {
  proposals_per_month: number;
  jd_parses_per_month: number;
  job_searches_per_day: number;
  resume_uploads: number;
  features: TierFeatures;
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: SubscriptionTier;
  has_stripe_customer: boolean;
  has_active_subscription: boolean;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
  proposal_count: number;
  jd_parse_count: number;
  job_search_count_today: number;
  usage_reset_date?: string;
  daily_reset_date?: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionWithUsage extends Subscription {
  proposals_remaining: number;
  jd_parses_remaining: number;
  searches_remaining_today: number;
  tier_limits: TierLimits;
  is_active: boolean;
}

// ============= API Types =============
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

// ============= Notification Types =============
export interface Notification {
  id: string;
  user_id: string;
  type: 'job_match' | 'proposal_generated' | 'system';
  title: string;
  message: string;
  data?: Record<string, any>;
  read: boolean;
  created_at: string;
}

// ============= Agent Types =============
export type AgentStatus = 'pending' | 'running' | 'completed' | 'failed';

// Generic agent response types
export interface AgentRunResponse {
  run_id: string;
  status: AgentStatus;
  message?: string;
}

export interface AgentStatusResponse {
  run_id: string;
  status: AgentStatus;
  progress_percent: number;
  current_step: string;
  messages: string[];
  errors: string[];
}

// Job Radar Agent
export interface JobRadarRequest {
  keywords?: string[];
  profession?: string;
  remote_only?: boolean;
  min_score?: number;
  generate_proposals?: boolean;
  max_proposals?: number;
}

export interface JobRadarMatch {
  job_id: string;
  title: string;
  company: string;
  location?: string;
  remote: boolean;
  score: number;
  explanation?: string;
  proposal?: string;
}

export interface JobRadarResult {
  run_id: string;
  status: AgentStatus;
  user_id: string;
  started_at: string;
  completed_at?: string;
  jobs_found: number;
  jobs_scored: number;
  matches_found: number;
  proposals_generated: number;
  top_matches: JobRadarMatch[];
  messages: string[];
  errors: string[];
}

// Cover Letter Agent
export type CoverLetterStyle = 'traditional' | 'modern' | 'creative' | 'executive';
export type CoverLetterLength = 'concise' | 'standard' | 'detailed';

export interface CoverLetterRequest {
  job_id?: string;
  job_description?: string;
  style?: CoverLetterStyle;
  length?: CoverLetterLength;
  include_salary_expectations?: boolean;
  emphasize_remote?: boolean;
}

export interface SkillAlignment {
  matched_skills: string[];
  missing_skills: string[];
  transferable_skills: string[];
  alignment_score: number;
}

export interface ExperienceMatch {
  requirement: string;
  match_type: 'direct' | 'transferable' | 'partial' | 'learning';
  confidence: number;
  highlight_points: string[];
}

export interface CoverLetterResultData {
  cover_letter: string;
  ats_score: number;
  keywords_used: string[];
  keywords_missing: string[];
  skill_alignment?: SkillAlignment;
  experience_matches: ExperienceMatch[];
  suggestions: string[];
}

export interface CoverLetterResult {
  run_id: string;
  status: AgentStatus;
  user_id: string;
  started_at: string;
  completed_at?: string;
  result?: CoverLetterResultData;
  target_job_title?: string;
  target_company?: string;
  style_used?: string;
  length_used?: string;
  messages: string[];
  errors: string[];
}

// Resume Optimizer Agent
export interface ResumeOptimizeRequest {
  target_job_id?: string;
  focus_areas?: string[];
}

export interface ResumeOptimizeSuggestion {
  category: string;
  issue: string;
  fix: string;
  priority: 'high' | 'medium' | 'low';
}

export interface ResumeOptimizeResult {
  run_id: string;
  status: AgentStatus;
  ats_score?: number;
  suggestions: ResumeOptimizeSuggestion[];
  keywords_missing: string[];
  keywords_present: string[];
  section_scores?: Record<string, number>;
  messages: string[];
  errors: string[];
}

// Interview Prep Agent
export interface InterviewPrepRequest {
  job_id?: string;
  interview_type?: 'behavioral' | 'technical' | 'system_design' | 'case_study' | 'auto';
  difficulty?: 'entry' | 'mid' | 'senior' | 'lead' | 'executive';
  num_questions?: number;
}

export interface InterviewQuestion {
  question: string;
  type: string;
  difficulty: string;
  tips: string[];
  sample_answer?: string;
}

export interface InterviewPrepResult {
  run_id: string;
  status: AgentStatus;
  questions: InterviewQuestion[];
  focus_areas: string[];
  prep_tips: string[];
  messages: string[];
  errors: string[];
}

// Salary Research Agent
export interface SalaryResearchRequest {
  job_id?: string;
  title?: string;
  location?: string;
  skills?: string[];
  experience_years?: number;
}

export interface SalaryRange {
  min_salary: number;
  max_salary: number;
  median_salary: number;
  median?: number;
  currency: string;
}

export interface MarketData {
  base_salary?: SalaryRange;
  total_compensation?: Record<string, number>;
  typical_bonus_percent?: number;
  typical_equity_value?: number;
  market_demand?: string;
  salary_trend?: string;
  key_factors: string[];
  data_sources: string[];
}

export interface NegotiationScript {
  scenario: string;
  opening: string;
  response_to_lowball: string;
  closing: string;
}

export interface NegotiationStrategy {
  approach: string;
  key_points: string[];
  timing_recommendations: string[];
  risks_to_avoid: string[];
}

export interface SalaryResearchResultData {
  job_title: string;
  location: string;
  salary_range: SalaryRange;
  market_data?: MarketData;
  compensation_analysis?: Record<string, any>;
  total_comp_estimate: number;
  location_adjustment: number;
  experience_adjustment: number;
  negotiation_leverage: string[];
  negotiation_strategy?: NegotiationStrategy;
  negotiation_scripts: NegotiationScript[];
  counter_offer_template: string;
}

export interface SalaryResearchResult {
  run_id: string;
  status: AgentStatus;
  user_id: string;
  started_at: string;
  completed_at?: string;
  result?: SalaryResearchResultData;
  messages: string[];
  errors: string[];
}

// Skill Gap Agent
export interface SkillGapRequest {
  target_job_title: string;
  target_job_description?: string;
  target_industry?: string;
  focus_areas?: string[];
}

export interface SkillGapItem {
  skill: string;
  importance: 'required' | 'preferred';
  current_level?: string;
  resources?: string[];
}

export interface SkillGapResult {
  run_id: string;
  status: AgentStatus;
  match_score?: number;
  matched_skills: string[];
  missing_skills: SkillGapItem[];
  recommendations: string[];
  messages: string[];
  errors: string[];
}

// Application Tracker Agent
export interface ApplicationTrackerRequest {
  include_insights?: boolean;
}

export interface ApplicationActionItem {
  job_id: string;
  job_title: string;
  company: string;
  action: string;
  priority: 'high' | 'medium' | 'low';
  due_date?: string;
}

export interface PortfolioAnalysis {
  health_score: number;
  total_count: number;
  active_count: number;
  interview_count: number;
  offer_count: number;
  response_rate: number;
  activity_trend: string;
  insights: string[];
  status_distribution: Record<string, number>;
}

export interface StaleApplication {
  application_id: string;
  job_title: string;
  company: string;
  status: string;
  days_stale: number;
  threshold: number;
  urgency: string;
  reason: string;
}

export interface TrackerRecommendation {
  type: string;
  title: string;
  description: string;
  priority: string;
}

export interface TrackerActionItem {
  type: string;
  priority: string;
  title: string;
  description: string;
  application_id?: string;
  reminder_id?: string;
}

export interface ApplicationStats {
  total_applications: number;
  active_applications: number;
  response_rate: number;
  upcoming_reminders: number;
  overdue_reminders: number;
  by_status: Record<string, number>;
}

export interface ApplicationTrackerResult {
  run_id: string;
  status: AgentStatus;
  user_id: string;
  started_at: string;
  completed_at?: string;
  briefing: string;
  portfolio_analysis?: PortfolioAnalysis;
  stale_applications: StaleApplication[];
  recommendations: TrackerRecommendation[];
  action_items: TrackerActionItem[];
  stats?: ApplicationStats;
  messages: string[];
  errors: string[];
}

// Network Intelligence Agent
export interface NetworkIntelligenceRequest {
  target_company: string;
  target_role?: string;
  target_industry?: string;
}

export interface NetworkIntelligenceResult {
  run_id: string;
  status: AgentStatus;
  company_insights?: {
    culture: string[];
    recent_news: string[];
    hiring_trends: string[];
  };
  potential_connections: string[];
  outreach_suggestions: string[];
  messages: string[];
  errors: string[];
}

// Auto-Apply Agent
export interface AutoApplyRequest {
  job_title: string;
  company_name: string;
  job_description: string;
  job_url?: string;
  application_type?: string;
}

export interface AutoApplyResult {
  run_id: string;
  status: AgentStatus;
  fit_assessment?: {
    overall_fit: number;
    strengths: string[];
    gaps: string[];
  };
  prepared_materials?: {
    cover_letter: string;
    resume_highlights: string[];
    screening_answers?: Record<string, string>;
  };
  messages: string[];
  errors: string[];
}

// ============= A/B Testing Types =============

export type ABTestStatus = 'draft' | 'active' | 'paused' | 'completed';

export interface ProposalVariant {
  id: string;
  user_id: string;
  job_match_id?: string;
  ab_test_id?: string;

  // Content
  content: string;
  variant_name?: string;

  // Generation parameters
  tone?: string;
  style?: string;
  length?: string;
  variant_label?: string; // "A" or "B"

  // Metadata
  generation_method?: string;
  model_used?: string;
  word_count?: number;
  keywords_used: string[];
  ats_score?: number;

  // A/B Test tracking
  is_control: boolean;
  is_selected: boolean;

  // Outcome tracking
  was_sent: boolean;
  sent_at?: string;
  got_response: boolean;
  response_at?: string;
  got_interview: boolean;
  interview_at?: string;
  got_offer: boolean;
  offer_at?: string;

  // Computed
  outcome_score: number;
  days_to_response?: number;

  created_at: string;
  updated_at: string;
}

export interface ABTestParameters {
  variant_a?: Record<string, any>;
  variant_b?: Record<string, any>;
}

export interface ABTestMetrics {
  count: number;
  sent: number;
  responses: number;
  interviews: number;
  offers: number;
  response_rate: number;
  interview_rate: number;
  offer_rate?: number;
}

export interface ABTestResults {
  variant_a?: ABTestMetrics;
  variant_b?: ABTestMetrics;
  winner?: string;
  completed_at?: string;
}

export interface ABTest {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  test_type: string;
  status: ABTestStatus;

  // Configuration
  parameters: ABTestParameters;
  target_sample_size: number;
  current_sample_size_a: number;
  current_sample_size_b: number;

  // Timing
  started_at?: string;
  ended_at?: string;

  // Results
  results: ABTestResults;
  winner_variant?: string;

  // Computed metrics
  variant_a_metrics: ABTestMetrics;
  variant_b_metrics: ABTestMetrics;

  // Variants (when fetched with details)
  variants?: ProposalVariant[];

  created_at: string;
  updated_at: string;
}

export interface ToneStyleStats {
  total: number;
  sent: number;
  responses: number;
  interviews: number;
  offers: number;
  response_rate: number;
  interview_rate: number;
}

export interface VariantStats {
  total_variants: number;
  sent_count: number;
  response_count: number;
  interview_count: number;
  offer_count: number;
  response_rate: number;
  interview_rate: number;
  offer_rate: number;
  by_tone: Record<string, ToneStyleStats>;
  by_style: Record<string, ToneStyleStats>;
}

export interface ABTestCreateRequest {
  name: string;
  test_type: string;
  description?: string;
  parameters?: ABTestParameters;
  target_sample_size?: number;
}

export interface VariantCreateRequest {
  content: string;
  job_match_id?: string;
  ab_test_id?: string;
  variant_name?: string;
  variant_label?: string;
  tone?: string;
  style?: string;
  length?: string;
  generation_method?: string;
  model_used?: string;
  keywords_used?: string[];
  ats_score?: number;
  is_control?: boolean;
}

export interface GenerateABVariantsRequest {
  job_match_id: string;
  ab_test_id?: string;
  variant_a_config: Record<string, any>;
  variant_b_config: Record<string, any>;
}

export interface GenerateABVariantsResponse {
  variant_a: ProposalVariant;
  variant_b: ProposalVariant;
  ab_test_id?: string;
}

// ============= Client Risk Types =============

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type RiskCategory = 'payment' | 'expectations' | 'scope' | 'communication' | 'company' | 'legal' | 'reputation';

export interface RedFlag {
  category: RiskCategory;
  flag: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  source?: string;
}

export interface GreenFlag {
  category: RiskCategory;
  flag: string;
  confidence: number;
  source?: string;
}

export interface RiskBreakdownCategory {
  score: number;
  factors: string[];
}

export interface ClientRiskAssessment {
  id: string;
  job_id: string;

  // Overall assessment
  risk_score: number;
  risk_level: RiskLevel;

  // Detailed breakdown
  risk_breakdown: Record<RiskCategory, RiskBreakdownCategory>;
  red_flags: RedFlag[];
  green_flags: GreenFlag[];

  // User-friendly content
  summary?: string;
  recommendations: string[];

  // Company context
  company_name?: string;
  company_risk_trend?: 'improving' | 'stable' | 'declining';

  // Metadata
  analysis_method: string;
  analyzed_at: string;
}

export interface ClientRiskBrief {
  job_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  top_concern?: string;
  analyzed_at: string;
}

export interface CompanyRiskProfile {
  id: string;
  company_name: string;

  // Aggregated scores
  average_risk_score: number;
  risk_level: RiskLevel;
  total_jobs_analyzed: number;

  // Patterns
  common_red_flags: Array<{ flag: string; count: number; percentage: number }>;
  common_green_flags: Array<{ flag: string; count: number; percentage: number }>;

  // Trend
  risk_trend?: 'improving' | 'stable' | 'declining';
  risk_history: Array<{ date: string; score: number }>;

  // User feedback
  user_reports: number;
  positive_outcomes: number;
  negative_outcomes: number;

  // External data
  external_ratings: Record<string, any>;

  first_seen: string;
  last_updated: string;
}

export interface RiskStats {
  total_analyzed: number;
  average_risk_score: number;
  risk_distribution: Record<RiskLevel, number>;
  top_concerns: Array<{ concern: string; count: number }>;
}
