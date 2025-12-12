/**
 * API Request/Response Types
 * Shared between web and mobile frontends
 */

import type {
  User,
  UserProfile,
  Job,
  ScoredJob,
  JobMatch,
  JobMatchStatus,
  Resume,
  Subscription,
  SubscriptionWithUsage,
  Notification,
  GeneratedProposal,
  AllTonesResponse,
  ParsedJD,
  ProposalTone,
  EnhancementType,
  PaginatedResponse,
} from '../types';

// ============= Auth Requests =============
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

// ============= User Requests =============
export interface UpdateProfileRequest {
  profession?: string;
  job_title?: string;
  skills?: string[];
  experience_years?: number;
  certifications?: string[];
  preferences?: {
    remote_only?: boolean;
    industries?: string[];
    job_types?: string[];
    avoid_keywords?: string[];
  };
  min_rate_usd?: number;
  max_hours_per_week?: number;
  availability?: Record<string, any>;
  portfolio?: Record<string, any>;
}

export interface UserWithProfile extends User {
  profile?: UserProfile;
}

// ============= Job Requests =============
export interface JobListParams {
  page?: number;
  size?: number;
  source?: string;
  remote_only?: boolean;
  min_rate?: number;
  max_rate?: number;
}

export interface JobSearchRequest {
  keywords?: string[];
  profession?: string;
  location?: string;
  remote_only?: boolean;
  min_rate?: number;
  max_rate?: number;
  limit?: number;
}

export interface JobSearchResponse {
  success: boolean;
  total_results: number;
  source_stats: Record<string, number>;
  jobs: ScoredJob[];
  error?: string;
}

export interface JobFeedParams {
  page?: number;
  size?: number;
}

export interface JobFeedResponse {
  jobs: ScoredJob[];
  total: number;
  page: number;
  size: number;
}

// ============= Match Requests =============
export interface MatchListParams {
  page?: number;
  size?: number;
  status?: JobMatchStatus;
}

export interface CreateMatchRequest {
  job_id: string;
  status?: JobMatchStatus;
}

export interface UpdateMatchRequest {
  status?: JobMatchStatus;
  client_notes?: string;
}

// ============= Resume Requests =============
export interface ResumeUploadFile {
  uri: string;
  name: string;
  type: string;
}

// ============= Proposal Requests =============
export interface GenerateProposalRequest {
  job_id?: string;
  job_description?: string;
  tone?: ProposalTone;
  custom_instructions?: string;
}

export interface GenerateAllTonesRequest {
  job_id?: string;
  job_description?: string;
  custom_instructions?: string;
}

export interface EnhanceProposalRequest {
  proposal: string;
  enhancement_type: EnhancementType;
  job_description?: string;
}

export interface EnhanceProposalResponse {
  enhanced_content: string;
  changes_made: string[];
}

export interface ParseJDRequest {
  job_description: string;
}

// ============= Subscription Requests =============
export interface CreateCheckoutRequest {
  tier: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface PortalResponse {
  portal_url: string;
}

// ============= Notification Requests =============
export interface NotificationListParams {
  page?: number;
  size?: number;
}

// ============= Generic Response Types =============
export type JobListResponse = PaginatedResponse<Job>;
export type MatchListResponse = PaginatedResponse<JobMatch>;
export type NotificationListResponse = PaginatedResponse<Notification>;
