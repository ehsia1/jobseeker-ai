// Custom hooks for API calls using SWR

import { useState } from 'react';
import useSWR from 'swr';
import { apiClient } from '@/lib/api/client';
import type {
  User,
  UserProfile,
  Job,
  JobMatch,
  Notification,
  PaginatedResponse,
  ApiResponse,
  UsageStats,
  SubscriptionWithUsage,
} from '@/lib/types';

// Current user hooks
export function useCurrentUser() {
  const { data, error, mutate } = useSWR(
    'current-user',
    () => apiClient.getCurrentUser(),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
    }
  );

  return {
    user: data?.data,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

export function useUserProfile(userId?: string) {
  const { data, error, mutate } = useSWR(
    userId ? `user-profile-${userId}` : 'my-profile',
    () => apiClient.getUserProfile(userId),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    profile: data?.data,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

// Job hooks
export function useJobs(page = 1, size = 20) {
  const { data, error, mutate } = useSWR(
    `jobs-${page}-${size}`,
    () => apiClient.getJobs(page, size),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    jobs: data?.data?.items || [],
    pagination: {
      total: data?.data?.total || 0,
      page: data?.data?.page || 1,
      size: data?.data?.size || size,
      pages: data?.data?.pages || 1,
    },
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

export function useJob(jobId: string | null) {
  const { data, error, mutate } = useSWR(
    jobId ? `job-${jobId}` : null,
    () => jobId ? apiClient.getJob(jobId) : null,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    job: data?.data,
    loading: !data && !error && !!jobId,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

// Job matches hooks
export function useJobMatches(userId?: string, page = 1, size = 20) {
  const { data, error, mutate } = useSWR(
    `job-matches-${userId || 'me'}-${page}-${size}`,
    () => apiClient.getJobMatches(userId, page, size),
    {
      revalidateOnFocus: false,
      refreshInterval: 30000, // Refresh every 30 seconds
    }
  );

  return {
    matches: data?.data?.items || [],
    pagination: {
      total: data?.data?.total || 0,
      page: data?.data?.page || 1,
      size: data?.data?.size || size,
      pages: data?.data?.pages || 1,
    },
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

// Notifications hooks
export function useNotifications(page = 1, size = 20) {
  const { data, error, mutate } = useSWR(
    `notifications-${page}-${size}`,
    () => apiClient.getNotifications(page, size),
    {
      revalidateOnFocus: true,
      refreshInterval: 10000, // Refresh every 10 seconds
    }
  );

  return {
    notifications: data?.data?.items || [],
    pagination: {
      total: data?.data?.total || 0,
      page: data?.data?.page || 1,
      size: data?.data?.size || size,
      pages: data?.data?.pages || 1,
    },
    unreadCount: data?.data?.items?.filter((n: Notification) => !n.read).length || 0,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

// Health check hook
export function useHealthCheck() {
  const { data, error } = useSWR(
    'health',
    () => apiClient.healthCheck(),
    {
      refreshInterval: 30000, // Check every 30 seconds
      revalidateOnFocus: false,
    }
  );

  return {
    status: data?.status,
    healthy: data?.status === 'healthy',
    timestamp: data?.timestamp,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
  };
}

// JD Parser hooks
export function useJDParserHealth() {
  const { data, error } = useSWR(
    'jd-parser-health',
    () => apiClient.getJDParserHealth(),
    {
      revalidateOnFocus: false,
      refreshInterval: 60000,
    }
  );

  return {
    status: data?.status,
    llmProvider: data?.llm_provider,
    llmModel: data?.llm_model,
    llmAvailable: data?.llm_available,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
  };
}

// Proposals hooks
export function useProposalsHealth() {
  const { data, error } = useSWR(
    'proposals-health',
    () => apiClient.getProposalsHealth(),
    {
      revalidateOnFocus: false,
      refreshInterval: 60000,
    }
  );

  return {
    status: data?.status,
    llmProvider: data?.llm_provider,
    llmModel: data?.llm_model,
    llmAvailable: data?.llm_available,
    demoMode: data?.demo_mode,
    availableTones: data?.available_tones || [],
    availableEnhancements: data?.available_enhancements || [],
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
  };
}

// Subscription hooks
export function useSubscription() {
  const { data, error, mutate } = useSWR(
    'subscription',
    () => apiClient.getSubscription(),
    {
      revalidateOnFocus: false,
      refreshInterval: 60000, // Refresh every minute
    }
  );

  return {
    subscription: data,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

export function useUsageStats() {
  const { data, error, mutate } = useSWR(
    'usage-stats',
    () => apiClient.getUsageStats(),
    {
      revalidateOnFocus: false,
      refreshInterval: 30000, // Refresh every 30 seconds
    }
  );

  return {
    usage: data,
    loading: !data && !error,
    error: error?.response?.data?.error || error?.message,
    refresh: mutate,
  };
}

// Generic mutation hook
export function useAsyncMutation<T = any, P = any>(
  mutationFn: (params: P) => Promise<T>
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const mutate = async (params: P) => {
    setLoading(true);
    setError(null);

    try {
      const result = await mutationFn(params);
      setData(result);
      return result;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.error || err?.message || 'An error occurred';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setLoading(false);
    setError(null);
    setData(null);
  };

  return {
    mutate,
    loading,
    error,
    data,
    reset,
  };
}