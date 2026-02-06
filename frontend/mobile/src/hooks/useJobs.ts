import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, matchesApi, profileApi, usersApi, subscriptionApi } from '../api/client';
import type { SearchQuery, JobMatchStatus, UserProfile, Resume, User, JobFilters } from '@jobseeker/shared';
import { useAuth } from '../contexts/AuthContext';

// Fetch jobs with infinite scroll
export function useJobsInfinite(options?: { filters?: JobFilters; size?: number }) {
  const size = options?.size ?? 20;
  const filters = options?.filters;
  const { isAuthenticated, isLoading } = useAuth();

  return useInfiniteQuery({
    queryKey: ['jobs', 'infinite', filters],
    queryFn: async ({ pageParam = 1 }) => {
      const result = await jobsApi.getJobs(pageParam, size, filters);
      // Transform to match expected format (items -> jobs)
      return {
        jobs: result.items,
        total: result.total,
        page: result.page,
        size: result.size,
        pages: result.pages,
      };
    },
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.jobs.length < size) return undefined;
      return allPages.length + 1;
    },
    initialPageParam: 1,
    enabled: isAuthenticated && !isLoading, // Only fetch when authenticated and not loading
    retry: false, // Don't retry on auth failures
  });
}

// Fetch single job
export function useJob(jobId: string) {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => jobsApi.getJob(jobId),
    enabled: !!jobId && isAuthenticated,
  });
}

// Search jobs
export function useJobSearch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (query: SearchQuery) => jobsApi.searchJobs(query),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

// Fetch job matches with infinite scroll
export function useMatchesInfinite(
  statusFilter?: JobMatchStatus,
  minScore = 0,
  size = 20
) {
  const { isAuthenticated } = useAuth();

  return useInfiniteQuery({
    queryKey: ['matches', 'infinite', statusFilter, minScore],
    queryFn: ({ pageParam = 1 }) =>
      matchesApi.getMatches(pageParam, size, statusFilter, minScore),
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.items.length < size) return undefined;
      return allPages.length + 1;
    },
    initialPageParam: 1,
    enabled: isAuthenticated,
  });
}

// Fetch single match
export function useMatch(matchId: string) {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['matches', matchId],
    queryFn: () => matchesApi.getMatch(matchId),
    enabled: !!matchId && isAuthenticated,
  });
}

// Update match status
export function useUpdateMatchStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: JobMatchStatus }) =>
      matchesApi.updateStatus(matchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    },
  });
}

// Update match notes
export function useUpdateMatchNotes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ matchId, notes }: { matchId: string; notes: string }) =>
      matchesApi.updateMatchNotes(matchId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    },
  });
}

// Save a job (create a match with 'saved' status)
export function useSaveJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobId: string) => {
      // Create the match first
      const match = await matchesApi.create(jobId);
      // Then update status to 'saved'
      return matchesApi.updateStatus(match.id, 'saved');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

// ============= Profile Hooks =============

// Fetch user profile
export function useProfile() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['profile'],
    queryFn: () => profileApi.getProfile(),
    enabled: isAuthenticated,
  });
}

// Update user profile
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (profile: Partial<UserProfile>) => profileApi.updateProfile(profile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
}

// ============= Resume Hooks =============
import { resumeApi } from '../api/client';

// Fetch current user's resume
export function useResume() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['resume'],
    queryFn: () => resumeApi.getResume(),
    enabled: isAuthenticated,
    staleTime: 0, // Always fetch fresh data for resume
  });
}

// Upload resume with full cache invalidation
export function useUploadResume() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: async (file: { uri: string; name: string; type: string }) => {
      return resumeApi.uploadResume(file);
    },
    onSuccess: async () => {
      // Force invalidate ALL resume-related caches
      await queryClient.invalidateQueries({ queryKey: ['resume'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['auth'] });

      // Also reset the queries to force fresh fetch
      queryClient.resetQueries({ queryKey: ['resume'] });

      // Refresh the user object in AuthContext
      await refreshUser();
    },
  });
}

// Re-parse existing resume with updated parsing logic
export function useReparseResume() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: async () => {
      return resumeApi.reparseResume();
    },
    onSuccess: async () => {
      // Force invalidate ALL resume-related caches
      await queryClient.invalidateQueries({ queryKey: ['resume'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['auth'] });

      // Also reset the queries to force fresh fetch
      queryClient.resetQueries({ queryKey: ['resume'] });

      // Refresh the user object in AuthContext
      await refreshUser();
    },
  });
}

// Submit resume as plain text (bypasses PDF extraction issues)
export function useSubmitResumeText() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: async (text: string) => {
      return resumeApi.submitResumeText(text);
    },
    onSuccess: async () => {
      // Force invalidate ALL resume-related caches
      await queryClient.invalidateQueries({ queryKey: ['resume'] });
      await queryClient.invalidateQueries({ queryKey: ['resume-debug'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['auth'] });

      // Also reset the queries to force fresh fetch
      queryClient.resetQueries({ queryKey: ['resume'] });

      // Refresh the user object in AuthContext
      await refreshUser();
    },
  });
}

// Get resume debug info (raw text extraction details)
export function useResumeDebug() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['resume-debug'],
    queryFn: () => resumeApi.getResumeDebug(),
    enabled: isAuthenticated,
    staleTime: 0, // Always fetch fresh
  });
}

// ============= User Hooks =============

// Update user contact info (full_name, phone)
export function useUpdateUser() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: (data: { full_name?: string; phone?: string }) =>
      usersApi.updateUser(data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      await refreshUser();
    },
  });
}

// Upload user avatar
export function useUploadAvatar() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: (file: { uri: string; name: string; type: string }) =>
      usersApi.uploadAvatar(file),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      await refreshUser();
    },
  });
}

// Delete user avatar
export function useDeleteAvatar() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: () => usersApi.deleteAvatar(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      await refreshUser();
    },
  });
}

// ============= Subscription Hooks =============

// Fetch user subscription
export function useSubscription() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['subscription'],
    queryFn: () => subscriptionApi.getSubscription(),
    enabled: isAuthenticated,
  });
}

// ============= Digest Settings Hooks =============
import { digestApi, DigestSettings } from '../api/client';

// Fetch digest settings
export function useDigestSettings() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['digestSettings'],
    queryFn: () => digestApi.getSettings(),
    enabled: isAuthenticated,
  });
}

// Update digest settings
export function useUpdateDigestSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: Partial<DigestSettings>) => digestApi.updateSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['digestSettings'] });
    },
  });
}

// Get digest preview
export function useDigestPreview() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['digestPreview'],
    queryFn: () => digestApi.getPreview(),
    enabled: false, // Only fetch when explicitly requested
  });
}

// Send digest now
export function useSendDigest() {
  return useMutation({
    mutationFn: () => digestApi.sendNow(),
  });
}
