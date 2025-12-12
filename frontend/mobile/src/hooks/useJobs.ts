import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, matchesApi, profileApi } from '../api/client';
import type { SearchQuery, JobMatchStatus, UserProfile } from '../../shared/src/types';
import { useAuth } from '../contexts/AuthContext';

// Fetch jobs with infinite scroll
export function useJobsInfinite(options?: { remote_only?: boolean; size?: number }) {
  const size = options?.size ?? 20;
  const { isAuthenticated, isLoading } = useAuth();

  console.log('[useJobsInfinite] isAuthenticated:', isAuthenticated, 'isLoading:', isLoading);

  return useInfiniteQuery({
    queryKey: ['jobs', 'infinite', options?.remote_only],
    queryFn: async ({ pageParam = 1 }) => {
      console.log('[useJobsInfinite] queryFn called, page:', pageParam);
      const result = await jobsApi.getJobs(pageParam, size);
      console.log('[useJobsInfinite] got', result.items.length, 'jobs');
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
