/**
 * Shared Constants
 * Constants used across web and mobile frontends
 */

import type { SubscriptionTier, TierLimits, TierFeatures, ProposalTone } from '../types';

// ============= App Config =============
export const APP_NAME = 'JobSeeker AI';
export const APP_VERSION = '1.0.0';

// ============= API Config =============
export const API_TIMEOUT = 30000; // 30 seconds
export const MAX_RETRY_ATTEMPTS = 3;
export const RETRY_DELAY = 1000; // 1 second

// ============= Pagination =============
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// ============= Subscription Tiers =============
export const SUBSCRIPTION_TIERS: Record<SubscriptionTier, { name: string; price: number; description: string }> = {
  free: {
    name: 'Free',
    price: 0,
    description: 'Basic features to get started',
  },
  starter: {
    name: 'Starter',
    price: 9,
    description: 'For casual job seekers',
  },
  pro: {
    name: 'Pro',
    price: 19,
    description: 'For serious job seekers',
  },
  power: {
    name: 'Power',
    price: 39,
    description: 'For power users and agencies',
  },
};

export const TIER_LIMITS: Record<SubscriptionTier, TierLimits> = {
  free: {
    proposals_per_month: 5,
    jd_parses_per_month: 10,
    job_searches_per_day: 5,
    resume_uploads: 1,
    features: {
      proposal_tones: ['medium'] as ProposalTone[],
      proposal_enhance: false,
      auto_apply: false,
      priority_support: false,
      analytics: false,
    },
  },
  starter: {
    proposals_per_month: 25,
    jd_parses_per_month: 50,
    job_searches_per_day: 20,
    resume_uploads: 1,
    features: {
      proposal_tones: ['short', 'medium'] as ProposalTone[],
      proposal_enhance: false,
      auto_apply: false,
      priority_support: false,
      analytics: false,
    },
  },
  pro: {
    proposals_per_month: 100,
    jd_parses_per_month: 200,
    job_searches_per_day: 50,
    resume_uploads: 3,
    features: {
      proposal_tones: ['short', 'medium', 'full'] as ProposalTone[],
      proposal_enhance: true,
      auto_apply: false,
      priority_support: false,
      analytics: true,
    },
  },
  power: {
    proposals_per_month: -1, // unlimited
    jd_parses_per_month: -1, // unlimited
    job_searches_per_day: -1, // unlimited
    resume_uploads: 10,
    features: {
      proposal_tones: ['short', 'medium', 'full'] as ProposalTone[],
      proposal_enhance: true,
      auto_apply: true,
      priority_support: true,
      analytics: true,
    },
  },
};

// ============= Job Sources =============
export const JOB_SOURCES = {
  UPWORK: 'upwork',
  LINKEDIN: 'linkedin',
  INDEED: 'indeed',
  FREELANCER: 'freelancer',
  REMOTE_OK: 'remoteok',
  WE_WORK_REMOTELY: 'weworkremotely',
  MANUAL: 'manual',
} as const;

export const JOB_SOURCE_LABELS: Record<string, string> = {
  [JOB_SOURCES.UPWORK]: 'Upwork',
  [JOB_SOURCES.LINKEDIN]: 'LinkedIn',
  [JOB_SOURCES.INDEED]: 'Indeed',
  [JOB_SOURCES.FREELANCER]: 'Freelancer',
  [JOB_SOURCES.REMOTE_OK]: 'Remote OK',
  [JOB_SOURCES.WE_WORK_REMOTELY]: 'We Work Remotely',
  [JOB_SOURCES.MANUAL]: 'Manual Entry',
};

// ============= Employment Types =============
export const EMPLOYMENT_TYPES = {
  FULL_TIME: 'full_time',
  PART_TIME: 'part_time',
  CONTRACT: 'contract',
  FREELANCE: 'freelance',
  INTERNSHIP: 'internship',
} as const;

export const EMPLOYMENT_TYPE_LABELS: Record<string, string> = {
  [EMPLOYMENT_TYPES.FULL_TIME]: 'Full-time',
  [EMPLOYMENT_TYPES.PART_TIME]: 'Part-time',
  [EMPLOYMENT_TYPES.CONTRACT]: 'Contract',
  [EMPLOYMENT_TYPES.FREELANCE]: 'Freelance',
  [EMPLOYMENT_TYPES.INTERNSHIP]: 'Internship',
};

// ============= Rate Types =============
export const RATE_TYPES = {
  HOURLY: 'hourly',
  DAILY: 'daily',
  WEEKLY: 'weekly',
  MONTHLY: 'monthly',
  YEARLY: 'yearly',
  FIXED: 'fixed',
} as const;

// ============= Industries =============
export const INDUSTRIES = [
  'Technology',
  'Healthcare',
  'Finance',
  'Education',
  'Marketing',
  'Design',
  'Sales',
  'Engineering',
  'Legal',
  'Media',
  'Consulting',
  'Real Estate',
  'Manufacturing',
  'Retail',
  'Non-profit',
] as const;

// ============= Common Skills =============
export const COMMON_SKILLS = {
  development: [
    'JavaScript',
    'TypeScript',
    'Python',
    'React',
    'Node.js',
    'AWS',
    'Docker',
    'PostgreSQL',
    'MongoDB',
    'GraphQL',
    'REST APIs',
    'Git',
    'CI/CD',
    'Kubernetes',
  ],
  design: [
    'UI/UX Design',
    'Figma',
    'Adobe XD',
    'Sketch',
    'Adobe Creative Suite',
    'Prototyping',
    'User Research',
    'Wireframing',
  ],
  marketing: [
    'SEO',
    'Content Marketing',
    'Social Media Marketing',
    'Google Ads',
    'Email Marketing',
    'Analytics',
    'Copywriting',
  ],
} as const;

// ============= Proposal Tones =============
export const PROPOSAL_TONE_LABELS: Record<ProposalTone, { name: string; description: string }> = {
  short: {
    name: 'Concise',
    description: '50-100 words, straight to the point',
  },
  medium: {
    name: 'Standard',
    description: '150-250 words, balanced detail',
  },
  full: {
    name: 'Comprehensive',
    description: '300-500 words, detailed pitch',
  },
};

// ============= Error Messages =============
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Unable to connect. Please check your internet connection.',
  UNAUTHORIZED: 'Your session has expired. Please log in again.',
  FORBIDDEN: 'You do not have permission to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  SERVER_ERROR: 'Something went wrong. Please try again later.',
  RATE_LIMIT: 'Too many requests. Please wait a moment and try again.',
  SUBSCRIPTION_REQUIRED: 'This feature requires a subscription upgrade.',
  LIMIT_REACHED: 'You have reached your usage limit for this feature.',
} as const;

// ============= Storage Keys =============
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
  THEME: 'theme',
  ONBOARDING_COMPLETE: 'onboarding_complete',
  LAST_SEARCH: 'last_search',
  NOTIFICATION_PREFERENCES: 'notification_preferences',
} as const;

// ============= Query Keys (for React Query/SWR) =============
export const QUERY_KEYS = {
  USER: 'user',
  PROFILE: 'profile',
  JOBS: 'jobs',
  JOB: 'job',
  JOB_FEED: 'jobFeed',
  MATCHES: 'matches',
  MATCH: 'match',
  RESUME: 'resume',
  SUBSCRIPTION: 'subscription',
  NOTIFICATIONS: 'notifications',
} as const;
