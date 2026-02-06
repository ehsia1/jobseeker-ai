import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, matchesApi, profileApi, usersApi, subscriptionApi, abTestApi } from '../api/client';
import type { SearchQuery, JobMatchStatus, UserProfile, Resume, User, JobFilters, ABTestStatus, ABTestCreateRequest, VariantCreateRequest, GenerateABVariantsRequest } from '@jobseeker/shared';
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
import { resumeApi, ResumeUploadError } from '../api/client';
import { useState, useCallback } from 'react';

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

// Upload resume with progress tracking and better error handling
export function useUploadResume() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();
  const [uploadProgress, setUploadProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: async (file: { uri: string; name: string; type: string; size?: number }) => {
      setUploadProgress(0);
      return resumeApi.uploadResume(file, {
        onProgress: (progress) => setUploadProgress(progress),
      });
    },
    onSuccess: async () => {
      setUploadProgress(100);
      // Force invalidate ALL resume-related caches
      await queryClient.invalidateQueries({ queryKey: ['resume'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['auth'] });

      // Also reset the queries to force fresh fetch
      queryClient.resetQueries({ queryKey: ['resume'] });

      // Refresh the user object in AuthContext
      await refreshUser();
    },
    onError: () => {
      setUploadProgress(0);
    },
    onSettled: () => {
      // Reset progress after a delay to allow UI to show completion
      setTimeout(() => setUploadProgress(0), 1000);
    },
  });

  const resetProgress = useCallback(() => setUploadProgress(0), []);

  return {
    ...mutation,
    uploadProgress,
    resetProgress,
  };
}

// Validate resume file before upload (can be called separately for early validation)
export function validateResumeFile(file: { uri: string; name: string; type: string; size?: number }) {
  try {
    resumeApi.validateResumeFile(file);
    return { valid: true, error: null };
  } catch (error) {
    if (error instanceof ResumeUploadError) {
      return { valid: false, error: error.message, code: error.code };
    }
    return { valid: false, error: 'Invalid file', code: 'UNKNOWN' };
  }
}

// Update resume fields manually
export function useUpdateResume() {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();

  return useMutation({
    mutationFn: async (data: {
      full_name?: string;
      email?: string;
      phone?: string;
      location?: string;
      summary?: string;
      linkedin_url?: string;
      github_url?: string;
      portfolio_url?: string;
      skills?: string[];
    }) => {
      return resumeApi.updateResume(data);
    },
    onSuccess: async () => {
      // Invalidate resume-related caches
      await queryClient.invalidateQueries({ queryKey: ['resume'] });
      await queryClient.invalidateQueries({ queryKey: ['profile'] });
      await queryClient.invalidateQueries({ queryKey: ['auth'] });

      // Refresh user
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

// ============= A/B Testing Hooks =============

// Fetch all A/B tests
export function useABTests(statusFilter?: ABTestStatus) {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['abTests', statusFilter],
    queryFn: () => abTestApi.getTests(statusFilter),
    enabled: isAuthenticated,
  });
}

// Fetch single A/B test with variants
export function useABTest(testId: string) {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['abTests', testId],
    queryFn: () => abTestApi.getTest(testId),
    enabled: !!testId && isAuthenticated,
  });
}

// Create A/B test
export function useCreateABTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ABTestCreateRequest) => abTestApi.createTest(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Start A/B test
export function useStartABTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (testId: string) => abTestApi.startTest(testId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Pause A/B test
export function usePauseABTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (testId: string) => abTestApi.pauseTest(testId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Complete A/B test
export function useCompleteABTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (testId: string) => abTestApi.completeTest(testId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Delete A/B test
export function useDeleteABTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (testId: string) => abTestApi.deleteTest(testId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Fetch variants for job match or A/B test
export function useVariants(jobMatchId?: string, abTestId?: string) {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['variants', { jobMatchId, abTestId }],
    queryFn: () => abTestApi.getVariants({ job_match_id: jobMatchId, ab_test_id: abTestId }),
    enabled: isAuthenticated && (!!jobMatchId || !!abTestId),
  });
}

// Create variant
export function useCreateVariant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: VariantCreateRequest) => abTestApi.createVariant(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      if (variables.ab_test_id) {
        queryClient.invalidateQueries({ queryKey: ['abTests', variables.ab_test_id] });
      }
    },
  });
}

// Select variant (mark as chosen)
export function useSelectVariant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variantId: string) => abTestApi.selectVariant(variantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variants'] });
    },
  });
}

// Mark variant as sent
export function useMarkVariantSent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variantId: string) => abTestApi.markVariantSent(variantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
    },
  });
}

// Record variant outcome
export function useRecordOutcome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ variantId, outcomeType }: { variantId: string; outcomeType: 'response' | 'interview' | 'offer' }) =>
      abTestApi.recordOutcome(variantId, outcomeType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      queryClient.invalidateQueries({ queryKey: ['abTests'] });
      queryClient.invalidateQueries({ queryKey: ['variantStats'] });
    },
  });
}

// Fetch variant statistics
export function useVariantStats() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ['variantStats'],
    queryFn: () => abTestApi.getStats(),
    enabled: isAuthenticated,
  });
}

// Generate A/B variants for a job
export function useGenerateABVariants() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: GenerateABVariantsRequest) => abTestApi.generateABVariants(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      if (variables.ab_test_id) {
        queryClient.invalidateQueries({ queryKey: ['abTests', variables.ab_test_id] });
      }
    },
  });
}
