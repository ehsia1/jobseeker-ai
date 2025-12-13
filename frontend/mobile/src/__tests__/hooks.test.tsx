/**
 * Unit tests for React Query hooks.
 * Tests jobs, matches, and profile data fetching hooks.
 */

// Must mock before imports since client.ts evaluates Platform.select at module load time
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
    select: jest.fn((options: Record<string, string>) => options.ios || options.default),
  },
}));

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useJobsInfinite,
  useJob,
  useJobSearch,
  useMatchesInfinite,
  useMatch,
  useUpdateMatchStatus,
  useSaveJob,
  useProfile,
  useUpdateProfile,
} from '../hooks/useJobs';
import {
  createTestQueryClient,
  createMockJob,
  createMockJobMatch,
  createMockProfile,
} from './helpers';

// Mock the auth context
const mockAuthContext = {
  user: null,
  isLoading: false,
  isAuthenticated: true,
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  refreshUser: jest.fn(),
};

jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockAuthContext,
}));

// Mock the API client
jest.mock('../api/client', () => ({
  jobsApi: {
    getJobs: jest.fn(),
    getJob: jest.fn(),
    searchJobs: jest.fn(),
  },
  matchesApi: {
    getMatches: jest.fn(),
    getMatch: jest.fn(),
    create: jest.fn(),
    updateStatus: jest.fn(),
    updateMatchNotes: jest.fn(),
  },
  profileApi: {
    getProfile: jest.fn(),
    updateProfile: jest.fn(),
  },
}));

import { jobsApi, matchesApi, profileApi } from '../api/client';

function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('Job Hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthContext.isAuthenticated = true;
    mockAuthContext.isLoading = false;
  });

  // ============= useJobsInfinite Tests =============

  describe('useJobsInfinite', () => {
    it('fetches jobs when authenticated', async () => {
      const mockJobs = [createMockJob(), createMockJob({ id: 'job-456' })];
      (jobsApi.getJobs as jest.Mock).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      });

      const { result } = renderHook(() => useJobsInfinite(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(jobsApi.getJobs).toHaveBeenCalledWith(1, 20);
      expect(result.current.data?.pages[0].jobs).toHaveLength(2);
    });

    it('does not fetch when not authenticated', async () => {
      mockAuthContext.isAuthenticated = false;

      const { result } = renderHook(() => useJobsInfinite(), {
        wrapper: createWrapper(),
      });

      // Should not fetch
      expect(jobsApi.getJobs).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('does not fetch while auth is loading', async () => {
      mockAuthContext.isLoading = true;

      const { result } = renderHook(() => useJobsInfinite(), {
        wrapper: createWrapper(),
      });

      expect(jobsApi.getJobs).not.toHaveBeenCalled();
    });

    it('fetches next page correctly', async () => {
      const page1Jobs = Array(20).fill(null).map((_, i) => createMockJob({ id: `job-${i}` }));
      const page2Jobs = [createMockJob({ id: 'job-20' })];

      (jobsApi.getJobs as jest.Mock)
        .mockResolvedValueOnce({
          items: page1Jobs,
          total: 21,
          page: 1,
          size: 20,
          pages: 2,
        })
        .mockResolvedValueOnce({
          items: page2Jobs,
          total: 21,
          page: 2,
          size: 20,
          pages: 2,
        });

      const { result } = renderHook(() => useJobsInfinite(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Fetch next page
      await act(async () => {
        await result.current.fetchNextPage();
      });

      expect(jobsApi.getJobs).toHaveBeenCalledTimes(2);
      expect(jobsApi.getJobs).toHaveBeenLastCalledWith(2, 20);
    });
  });

  // ============= useJob Tests =============

  describe('useJob', () => {
    it('fetches single job by ID', async () => {
      const mockJob = createMockJob();
      (jobsApi.getJob as jest.Mock).mockResolvedValue(mockJob);

      const { result } = renderHook(() => useJob('job-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(jobsApi.getJob).toHaveBeenCalledWith('job-123');
      expect(result.current.data?.id).toBe('job-123');
    });

    it('does not fetch when jobId is empty', async () => {
      const { result } = renderHook(() => useJob(''), {
        wrapper: createWrapper(),
      });

      expect(jobsApi.getJob).not.toHaveBeenCalled();
    });
  });

  // ============= useJobSearch Tests =============

  describe('useJobSearch', () => {
    it('searches jobs with query', async () => {
      const mockSearchResult = {
        success: true,
        total_results: 1,
        source_stats: {},
        jobs: [createMockJob()],
      };
      (jobsApi.searchJobs as jest.Mock).mockResolvedValue(mockSearchResult);

      const { result } = renderHook(() => useJobSearch(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({ keywords: ['python'], remote_only: true });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(jobsApi.searchJobs).toHaveBeenCalledWith({
        keywords: ['python'],
        remote_only: true,
      });
    });
  });
});

describe('Match Hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthContext.isAuthenticated = true;
    mockAuthContext.isLoading = false;
  });

  // ============= useMatchesInfinite Tests =============

  describe('useMatchesInfinite', () => {
    it('fetches matches when authenticated', async () => {
      const mockMatches = [createMockJobMatch()];
      (matchesApi.getMatches as jest.Mock).mockResolvedValue({
        items: mockMatches,
        total: 1,
        page: 1,
        size: 20,
        pages: 1,
      });

      const { result } = renderHook(() => useMatchesInfinite(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.getMatches).toHaveBeenCalledWith(1, 20, undefined, 0);
    });

    it('applies status filter', async () => {
      (matchesApi.getMatches as jest.Mock).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 0,
      });

      const { result } = renderHook(() => useMatchesInfinite('saved'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.getMatches).toHaveBeenCalledWith(1, 20, 'saved', 0);
    });

    it('applies min score filter', async () => {
      (matchesApi.getMatches as jest.Mock).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 0,
      });

      const { result } = renderHook(() => useMatchesInfinite(undefined, 75), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.getMatches).toHaveBeenCalledWith(1, 20, undefined, 75);
    });
  });

  // ============= useMatch Tests =============

  describe('useMatch', () => {
    it('fetches single match by ID', async () => {
      const mockMatch = createMockJobMatch();
      (matchesApi.getMatch as jest.Mock).mockResolvedValue(mockMatch);

      const { result } = renderHook(() => useMatch('match-123'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.getMatch).toHaveBeenCalledWith('match-123');
      expect(result.current.data?.id).toBe('match-123');
    });
  });

  // ============= useUpdateMatchStatus Tests =============

  describe('useUpdateMatchStatus', () => {
    it('updates match status', async () => {
      const mockMatch = createMockJobMatch({ status: 'applied' });
      (matchesApi.updateStatus as jest.Mock).mockResolvedValue(mockMatch);

      const { result } = renderHook(() => useUpdateMatchStatus(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({ matchId: 'match-123', status: 'applied' });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.updateStatus).toHaveBeenCalledWith('match-123', 'applied');
    });
  });

  // ============= useSaveJob Tests =============

  describe('useSaveJob', () => {
    it('creates match and updates status to saved', async () => {
      const mockMatch = createMockJobMatch({ status: 'new' });
      const savedMatch = createMockJobMatch({ status: 'saved' });

      (matchesApi.create as jest.Mock).mockResolvedValue(mockMatch);
      (matchesApi.updateStatus as jest.Mock).mockResolvedValue(savedMatch);

      const { result } = renderHook(() => useSaveJob(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate('job-123');
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(matchesApi.create).toHaveBeenCalledWith('job-123');
      expect(matchesApi.updateStatus).toHaveBeenCalledWith('match-123', 'saved');
    });
  });
});

describe('Profile Hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuthContext.isAuthenticated = true;
    mockAuthContext.isLoading = false;
  });

  // ============= useProfile Tests =============

  describe('useProfile', () => {
    it('fetches profile when authenticated', async () => {
      const mockProfile = createMockProfile();
      (profileApi.getProfile as jest.Mock).mockResolvedValue(mockProfile);

      const { result } = renderHook(() => useProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(profileApi.getProfile).toHaveBeenCalled();
      expect(result.current.data?.profession).toBe('Software Engineer');
    });

    it('does not fetch when not authenticated', async () => {
      mockAuthContext.isAuthenticated = false;

      const { result } = renderHook(() => useProfile(), {
        wrapper: createWrapper(),
      });

      expect(profileApi.getProfile).not.toHaveBeenCalled();
    });
  });

  // ============= useUpdateProfile Tests =============

  describe('useUpdateProfile', () => {
    it('updates profile data', async () => {
      const updatedProfile = createMockProfile({ skills: ['Python', 'Go', 'Rust'] });
      (profileApi.updateProfile as jest.Mock).mockResolvedValue(updatedProfile);

      const { result } = renderHook(() => useUpdateProfile(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({ skills: ['Python', 'Go', 'Rust'] });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(profileApi.updateProfile).toHaveBeenCalledWith({
        skills: ['Python', 'Go', 'Rust'],
      });
    });
  });
});
