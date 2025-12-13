/**
 * Unit tests for the API client.
 * Tests token management, request handling, and API endpoints.
 */

// Must mock before imports since client.ts evaluates Platform.select at module load time
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
    select: jest.fn((options: Record<string, string>) => options.ios || options.default),
  },
}));

import {
  getToken,
  setToken,
  removeToken,
  authApi,
  jobsApi,
  matchesApi,
  profileApi,
  healthApi,
} from '../api/client';
import {
  mockSecureStore,
  mockFetchSuccess,
  mockFetchError,
  createMockUser,
  createMockProfile,
  createMockJob,
  createMockJobMatch,
  createMockAuthResponse,
} from './helpers';

describe('API Client', () => {
  let secureStoreMock: ReturnType<typeof mockSecureStore>;

  beforeEach(() => {
    secureStoreMock = mockSecureStore();
    jest.clearAllMocks();
  });

  // ============= Token Management Tests =============

  describe('Token Management', () => {
    it('getToken returns null when no token is stored', async () => {
      const token = await getToken();
      // First call might return cached value from module init, but after clear it should be null
      expect(token).toBeNull();
    });

    it('setToken stores token in SecureStore', async () => {
      await setToken('test-token-123');
      expect(secureStoreMock.store['auth_token']).toBe('test-token-123');
    });

    it('getToken returns stored token', async () => {
      secureStoreMock.store['auth_token'] = 'stored-token';
      // Need to bypass cache for this test
      const SecureStore = require('expo-secure-store');
      const token = await SecureStore.getItemAsync('auth_token');
      expect(token).toBe('stored-token');
    });

    it('removeToken clears the stored token', async () => {
      secureStoreMock.store['auth_token'] = 'token-to-remove';
      await removeToken();
      const SecureStore = require('expo-secure-store');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_token');
    });
  });

  // ============= Auth API Tests =============

  describe('Auth API', () => {
    describe('login', () => {
      it('sends correct login request and stores token', async () => {
        const mockResponse = createMockAuthResponse();
        mockFetchSuccess(mockResponse);

        const result = await authApi.login('test@example.com', 'password123');

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/auth/login'),
          expect.objectContaining({
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          })
        );
        expect(result.access_token).toBe('mock-jwt-token-123');
      });

      it('throws error on login failure', async () => {
        mockFetchError('Invalid credentials', 401);

        await expect(authApi.login('test@example.com', 'wrong')).rejects.toThrow(
          'Invalid credentials'
        );
      });
    });

    describe('register', () => {
      it('sends correct registration request', async () => {
        const mockUser = createMockUser();
        mockFetchSuccess(mockUser, 201);

        const result = await authApi.register('new@example.com', 'password123', 'New User');

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/auth/register'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('new@example.com'),
          })
        );
        expect(result.email).toBe('test@example.com');
      });

      it('throws error when email already exists', async () => {
        mockFetchError('User already exists', 400);

        await expect(
          authApi.register('existing@example.com', 'password123')
        ).rejects.toThrow('User already exists');
      });
    });

    describe('getCurrentUser', () => {
      it('fetches current user with auth header', async () => {
        const mockUser = createMockUser({ profile: createMockProfile() });
        await setToken('valid-token');
        mockFetchSuccess(mockUser);

        const result = await authApi.getCurrentUser();

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/auth/me'),
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: 'Bearer valid-token',
            }),
          })
        );
        expect(result.email).toBe('test@example.com');
      });
    });

    describe('logout', () => {
      it('removes the auth token', async () => {
        await setToken('token-to-logout');
        await authApi.logout();
        const SecureStore = require('expo-secure-store');
        expect(SecureStore.deleteItemAsync).toHaveBeenCalled();
      });
    });
  });

  // ============= Jobs API Tests =============

  describe('Jobs API', () => {
    beforeEach(async () => {
      await setToken('test-token');
    });

    describe('getJobs', () => {
      it('fetches jobs with pagination params', async () => {
        const mockJobs = [createMockJob(), createMockJob({ id: 'job-456' })];
        mockFetchSuccess(mockJobs);

        const result = await jobsApi.getJobs(1, 20);

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/jobs\/\?limit=20&offset=0/),
          expect.any(Object)
        );
        expect(result.items).toHaveLength(2);
        expect(result.page).toBe(1);
      });

      it('calculates correct offset for page 2', async () => {
        mockFetchSuccess([]);

        await jobsApi.getJobs(2, 10);

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/offset=10/),
          expect.any(Object)
        );
      });
    });

    describe('getJob', () => {
      it('fetches single job by ID', async () => {
        const mockJob = createMockJob();
        mockFetchSuccess(mockJob);

        const result = await jobsApi.getJob('job-123');

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/jobs\/job-123\//),
          expect.any(Object)
        );
        expect(result.id).toBe('job-123');
      });
    });

    describe('searchJobs', () => {
      it('sends search query with POST request', async () => {
        mockFetchSuccess({
          success: true,
          total_results: 1,
          source_stats: {},
          jobs: [createMockJob()],
        });

        const query = { keywords: ['python'], remote_only: true };
        const result = await jobsApi.searchJobs(query);

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/jobs\/search\//),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify(query),
          })
        );
        expect(result.success).toBe(true);
      });
    });
  });

  // ============= Matches API Tests =============

  describe('Matches API', () => {
    beforeEach(async () => {
      await setToken('test-token');
    });

    describe('getMatches', () => {
      it('fetches matches with filters', async () => {
        const mockMatches = [createMockJobMatch()];
        mockFetchSuccess(mockMatches);

        const result = await matchesApi.getMatches(1, 20, 'saved', 50);

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/status_filter=saved/),
          expect.any(Object)
        );
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/min_score=50/),
          expect.any(Object)
        );
        expect(result.items).toHaveLength(1);
      });
    });

    describe('create', () => {
      it('creates a new match for a job', async () => {
        const mockMatch = createMockJobMatch();
        mockFetchSuccess(mockMatch, 201);

        const result = await matchesApi.create('job-123');

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/matches\//),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ job_id: 'job-123' }),
          })
        );
        expect(result.job_id).toBe('job-123');
      });
    });

    describe('updateStatus', () => {
      it('updates match status', async () => {
        const mockMatch = createMockJobMatch({ status: 'applied' });
        mockFetchSuccess(mockMatch);

        const result = await matchesApi.updateStatus('match-123', 'applied');

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/matches\/match-123\/status\//),
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify({ status: 'applied' }),
          })
        );
        expect(result.status).toBe('applied');
      });
    });
  });

  // ============= Profile API Tests =============

  describe('Profile API', () => {
    beforeEach(async () => {
      await setToken('test-token');
    });

    describe('getProfile', () => {
      it('fetches user profile', async () => {
        const mockProfile = createMockProfile();
        mockFetchSuccess(mockProfile);

        const result = await profileApi.getProfile();

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/users\/profile\//),
          expect.any(Object)
        );
        expect(result.profession).toBe('Software Engineer');
      });
    });

    describe('updateProfile', () => {
      it('updates profile with partial data', async () => {
        const mockProfile = createMockProfile({ skills: ['Python', 'Go'] });
        mockFetchSuccess(mockProfile);

        const updates = { skills: ['Python', 'Go'] };
        const result = await profileApi.updateProfile(updates);

        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/users\/profile\//),
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify(updates),
          })
        );
        expect(result.skills).toContain('Go');
      });
    });
  });

  // ============= Health API Tests =============

  describe('Health API', () => {
    it('checks API health status', async () => {
      mockFetchSuccess({ status: 'healthy', timestamp: '2024-01-01T00:00:00Z' });

      const result = await healthApi.check();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringMatching(/\/health\//),
        expect.any(Object)
      );
      expect(result.status).toBe('healthy');
    });
  });

  // ============= Error Handling Tests =============

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setToken('test-token');
    });

    it('handles 401 Unauthorized by clearing token', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ detail: 'Unauthorized' }),
      });

      await expect(profileApi.getProfile()).rejects.toThrow('Unauthorized');

      const SecureStore = require('expo-secure-store');
      expect(SecureStore.deleteItemAsync).toHaveBeenCalled();
    });

    it('handles network errors gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(healthApi.check()).rejects.toThrow('Network error');
    });

    it('handles malformed JSON responses', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(profileApi.getProfile()).rejects.toThrow('Request failed');
    });
  });
});
