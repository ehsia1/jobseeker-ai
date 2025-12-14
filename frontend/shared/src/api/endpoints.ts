/**
 * API Endpoint Definitions
 * Shared between web and mobile frontends
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export interface EndpointConfig {
  path: string;
  method: HttpMethod;
  requiresAuth: boolean;
}

// ============= Auth Endpoints =============
export const AUTH_ENDPOINTS = {
  login: {
    path: '/auth/login',
    method: 'POST' as const,
    requiresAuth: false,
  },
  register: {
    path: '/auth/register',
    method: 'POST' as const,
    requiresAuth: false,
  },
  refreshToken: {
    path: '/auth/refresh',
    method: 'POST' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= User Endpoints =============
export const USER_ENDPOINTS = {
  getCurrentUser: {
    path: '/users/me',
    method: 'GET' as const,
    requiresAuth: true,
  },
  getProfile: {
    path: '/users/profile',
    method: 'GET' as const,
    requiresAuth: true,
  },
  updateProfile: {
    path: '/users/profile',
    method: 'PUT' as const,
    requiresAuth: true,
  },
  deleteProfile: {
    path: '/users/profile',
    method: 'DELETE' as const,
    requiresAuth: true,
  },
  getNotifications: {
    path: '/users/me/notifications',
    method: 'GET' as const,
    requiresAuth: true,
  },
  markNotificationRead: {
    path: '/users/me/notifications/:id/read',
    method: 'PUT' as const,
    requiresAuth: true,
  },
  markAllNotificationsRead: {
    path: '/users/me/notifications/read-all',
    method: 'PUT' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Job Endpoints =============
export const JOB_ENDPOINTS = {
  list: {
    path: '/jobs',
    method: 'GET' as const,
    requiresAuth: true,
  },
  getById: {
    path: '/jobs/:id',
    method: 'GET' as const,
    requiresAuth: true,
  },
  search: {
    path: '/jobs/search',
    method: 'POST' as const,
    requiresAuth: true,
  },
  getFeed: {
    path: '/jobs/feed',
    method: 'GET' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Match Endpoints =============
export const MATCH_ENDPOINTS = {
  list: {
    path: '/matches',
    method: 'GET' as const,
    requiresAuth: true,
  },
  create: {
    path: '/matches',
    method: 'POST' as const,
    requiresAuth: true,
  },
  getById: {
    path: '/matches/:id',
    method: 'GET' as const,
    requiresAuth: true,
  },
  update: {
    path: '/matches/:id',
    method: 'PUT' as const,
    requiresAuth: true,
  },
  delete: {
    path: '/matches/:id',
    method: 'DELETE' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Resume Endpoints =============
export const RESUME_ENDPOINTS = {
  get: {
    path: '/resume',
    method: 'GET' as const,
    requiresAuth: true,
  },
  upload: {
    path: '/resume/upload',
    method: 'POST' as const,
    requiresAuth: true,
  },
  delete: {
    path: '/resume',
    method: 'DELETE' as const,
    requiresAuth: true,
  },
  parse: {
    path: '/resume/parse',
    method: 'POST' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Proposal Endpoints =============
export const PROPOSAL_ENDPOINTS = {
  generate: {
    path: '/proposals/generate',
    method: 'POST' as const,
    requiresAuth: true,
  },
  generateAllTones: {
    path: '/proposals/generate-all-tones',
    method: 'POST' as const,
    requiresAuth: true,
  },
  enhance: {
    path: '/proposals/enhance',
    method: 'POST' as const,
    requiresAuth: true,
  },
  parseJD: {
    path: '/proposals/parse-jd',
    method: 'POST' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Subscription Endpoints =============
export const SUBSCRIPTION_ENDPOINTS = {
  get: {
    path: '/subscription',
    method: 'GET' as const,
    requiresAuth: true,
  },
  createCheckout: {
    path: '/subscription/checkout',
    method: 'POST' as const,
    requiresAuth: true,
  },
  createPortal: {
    path: '/subscription/portal',
    method: 'POST' as const,
    requiresAuth: true,
  },
  cancel: {
    path: '/subscription/cancel',
    method: 'POST' as const,
    requiresAuth: true,
  },
} satisfies Record<string, EndpointConfig>;

// ============= Agent Endpoints =============
export const AGENT_ENDPOINTS = {
  // Job Radar
  radarRun: {
    path: '/agent/radar/run',
    method: 'POST' as const,
    requiresAuth: true,
  },
  radarStatus: {
    path: '/agent/radar/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  radarResult: {
    path: '/agent/radar/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Cover Letter
  coverLetterRun: {
    path: '/agent/cover-letter/generate',
    method: 'POST' as const,
    requiresAuth: true,
  },
  coverLetterStatus: {
    path: '/agent/cover-letter/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  coverLetterResult: {
    path: '/agent/cover-letter/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Resume Optimizer
  resumeOptimizeRun: {
    path: '/agent/resume/optimize',
    method: 'POST' as const,
    requiresAuth: true,
  },
  resumeOptimizeStatus: {
    path: '/agent/resume/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  resumeOptimizeResult: {
    path: '/agent/resume/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Interview Prep
  interviewPrepRun: {
    path: '/agent/interview/prep',
    method: 'POST' as const,
    requiresAuth: true,
  },
  interviewPrepStatus: {
    path: '/agent/interview/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  interviewPrepResult: {
    path: '/agent/interview/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Salary Research
  salaryResearchRun: {
    path: '/agent/salary/research',
    method: 'POST' as const,
    requiresAuth: true,
  },
  salaryResearchStatus: {
    path: '/agent/salary/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  salaryResearchResult: {
    path: '/agent/salary/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Skill Gap
  skillGapRun: {
    path: '/agent/skill-gap/analyze',
    method: 'POST' as const,
    requiresAuth: true,
  },
  skillGapStatus: {
    path: '/agent/skill-gap/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  skillGapResult: {
    path: '/agent/skill-gap/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Application Tracker
  trackerRun: {
    path: '/agent/tracker/briefing',
    method: 'POST' as const,
    requiresAuth: true,
  },
  trackerStatus: {
    path: '/agent/tracker/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  trackerResult: {
    path: '/agent/tracker/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Network Intelligence
  networkRun: {
    path: '/agent/network/analyze',
    method: 'POST' as const,
    requiresAuth: true,
  },
  networkStatus: {
    path: '/agent/network/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  networkResult: {
    path: '/agent/network/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Auto-Apply
  autoApplyRun: {
    path: '/agent/apply/prepare',
    method: 'POST' as const,
    requiresAuth: true,
  },
  autoApplyStatus: {
    path: '/agent/apply/status/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  autoApplyResult: {
    path: '/agent/apply/result/:runId',
    method: 'GET' as const,
    requiresAuth: true,
  },
  // Health check
  health: {
    path: '/agent/health',
    method: 'GET' as const,
    requiresAuth: false,
  },
} satisfies Record<string, EndpointConfig>;

// ============= All Endpoints =============
export const API_ENDPOINTS = {
  auth: AUTH_ENDPOINTS,
  users: USER_ENDPOINTS,
  jobs: JOB_ENDPOINTS,
  matches: MATCH_ENDPOINTS,
  resume: RESUME_ENDPOINTS,
  proposals: PROPOSAL_ENDPOINTS,
  subscription: SUBSCRIPTION_ENDPOINTS,
  agent: AGENT_ENDPOINTS,
} as const;

/**
 * Replace path parameters with actual values
 * @example buildPath('/jobs/:id', { id: '123' }) => '/jobs/123'
 */
export function buildPath(
  path: string,
  params?: Record<string, string | number>
): string {
  if (!params) return path;

  let result = path;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(`:${key}`, String(value));
  }
  return result;
}

/**
 * Build query string from params object
 * @example buildQueryString({ page: 1, limit: 10 }) => '?page=1&limit=10'
 */
export function buildQueryString(
  params?: Record<string, string | number | boolean | undefined>
): string {
  if (!params) return '';

  const filtered = Object.entries(params)
    .filter(([_, value]) => value !== undefined)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);

  return filtered.length > 0 ? `?${filtered.join('&')}` : '';
}
