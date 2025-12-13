/**
 * Test utilities and mock factories for JobSeeker AI frontend tests.
 */

import type {
  User,
  UserProfile,
  Job,
  JobMatch,
  AuthResponse,
  Subscription,
  SubscriptionWithUsage,
} from '../../shared/src/types';

// ============= Mock Data Factories =============

export function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockProfile(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    id: 'profile-123',
    user_id: 'user-123',
    profession: 'Software Engineer',
    job_title: 'Senior Developer',
    skills: ['Python', 'TypeScript', 'React'],
    experience_years: 5,
    certifications: ['AWS Certified'],
    preferences: {
      remote_only: true,
      industries: ['tech'],
      job_types: ['full-time'],
    },
    min_rate_usd: 100000,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job-123',
    title: 'Senior Software Engineer',
    company: 'TechCorp',
    description: 'Build amazing things with a great team.',
    skills: ['Python', 'FastAPI', 'PostgreSQL'],
    rate_min: 120000,
    rate_max: 180000,
    rate_type: 'annual',
    location: 'San Francisco, CA',
    remote: true,
    employment_type: 'full-time',
    posted_at: '2024-01-01T00:00:00Z',
    source: 'linkedin',
    url: 'https://example.com/job/123',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockJobMatch(overrides: Partial<JobMatch> = {}): JobMatch {
  const job = createMockJob();
  return {
    id: 'match-123',
    user_id: 'user-123',
    job_id: job.id,
    job,
    total_score: 85.5,
    score_breakdown: {
      semantic_similarity: 80,
      skill_match: 90,
      experience_match: 85,
      compensation_match: 75,
      location_match: 100,
      freshness_score: 90,
      preference_match: 80,
    },
    explanation: 'Strong match based on skills and preferences.',
    status: 'new',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockAuthResponse(overrides: Partial<AuthResponse> = {}): AuthResponse {
  return {
    access_token: 'mock-jwt-token-123',
    token_type: 'bearer',
    user: createMockUser(),
    ...overrides,
  };
}

export function createMockSubscription(
  overrides: Partial<SubscriptionWithUsage> = {}
): SubscriptionWithUsage {
  return {
    id: 'sub-123',
    user_id: 'user-123',
    tier: 'free',
    has_stripe_customer: false,
    has_active_subscription: false,
    cancel_at_period_end: false,
    proposal_count: 0,
    jd_parse_count: 0,
    job_search_count_today: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    proposals_remaining: 3,
    jd_parses_remaining: 5,
    searches_remaining_today: 10,
    tier_limits: {
      proposals_per_month: 3,
      jd_parses_per_month: 5,
      job_searches_per_day: 10,
      resume_uploads: 1,
      features: {
        proposal_tones: ['short', 'medium'],
        proposal_enhance: false,
        auto_apply: false,
        priority_support: false,
        analytics: false,
      },
    },
    is_active: true,
    ...overrides,
  };
}

// ============= API Mock Helpers =============

export function mockFetchSuccess<T>(data: T, status = 200) {
  return (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Created',
    json: async () => data,
  });
}

export function mockFetchError(error: string, status = 400) {
  return (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Bad Request',
    json: async () => ({ detail: error }),
  });
}

export function mockFetchNetworkError(message = 'Network error') {
  return (global.fetch as jest.Mock).mockRejectedValueOnce(new Error(message));
}

// ============= SecureStore Mock Helpers =============

export function mockSecureStore() {
  const store: Record<string, string> = {};
  const SecureStore = require('expo-secure-store');

  SecureStore.getItemAsync.mockImplementation(async (key: string) => store[key] || null);
  SecureStore.setItemAsync.mockImplementation(async (key: string, value: string) => {
    store[key] = value;
  });
  SecureStore.deleteItemAsync.mockImplementation(async (key: string) => {
    delete store[key];
  });

  return {
    store,
    clear: () => {
      Object.keys(store).forEach((key) => delete store[key]);
    },
  };
}

// ============= Test Wrapper Components =============

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface TestProvidersProps {
  children: React.ReactNode;
  queryClient?: QueryClient;
}

export function TestProviders({ children, queryClient }: TestProvidersProps) {
  const client = queryClient || createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

// ============= Wait Helpers =============

export function waitFor(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function flushPromises(): Promise<void> {
  await new Promise((resolve) => setImmediate(resolve));
}
