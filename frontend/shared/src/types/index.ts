// JobSeeker AI Shared Types

// ============= User Types =============
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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
