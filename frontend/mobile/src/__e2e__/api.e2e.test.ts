/**
 * E2E tests for the frontend API client against a live backend.
 *
 * These tests verify that the API client correctly communicates with the backend.
 * They run against a real server and test the complete request/response cycle.
 *
 * Usage:
 *   # Start the backend first:
 *   uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
 *
 *   # Run E2E tests:
 *   npm run test:e2e
 *
 *   # Or with a different base URL:
 *   BASE_URL=http://localhost:8080 npm run test:e2e
 */

// Base URL for the backend API
const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';
const TEST_TIMESTAMP = Date.now();
const TEST_EMAIL = `e2e_frontend_${TEST_TIMESTAMP}@test.com`;
const TEST_USERNAME = `e2e_fe_user_${TEST_TIMESTAMP}`;
const TEST_PASSWORD = 'TestPassword123!';

// Shared state across tests
let accessToken: string | null = null;
let userId: string | null = null;
let jobId: string | null = null;
let matchId: string | null = null;

// Helper to make authenticated requests
async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

// Helper to make form-encoded requests (for login)
async function formRequest(
  path: string,
  data: Record<string, string>
): Promise<Response> {
  const url = `${BASE_URL}${path}`;
  const body = new URLSearchParams(data).toString();

  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  });
}

describe('Frontend E2E API Tests', () => {
  // Skip all tests if we can't connect to the backend
  beforeAll(async () => {
    try {
      const response = await fetch(`${BASE_URL}/`);
      if (!response.ok && response.status !== 404 && response.status !== 307) {
        throw new Error(`Backend returned ${response.status}`);
      }
    } catch (error) {
      console.error(
        `Cannot connect to backend at ${BASE_URL}. ` +
          'Make sure the server is running: ' +
          'uvicorn backend.api.main:app --host 0.0.0.0 --port 8000'
      );
      throw error;
    }
  });

  // ============= Health Check =============

  describe('Health Check', () => {
    it('should reach the backend server', async () => {
      const response = await fetch(`${BASE_URL}/`);
      // Accept various success/redirect codes
      expect([200, 307, 404]).toContain(response.status);
    });
  });

  // ============= Authentication Flow =============

  describe('Authentication', () => {
    it('should register a new user', async () => {
      const response = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: TEST_EMAIL,
          username: TEST_USERNAME,
          password: TEST_PASSWORD,
        }),
      });

      expect([200, 201]).toContain(response.status);

      const data = await response.json();
      expect(data).toHaveProperty('id');
      expect(data.email).toBe(TEST_EMAIL);
      console.log(`✓ Registered user: ${TEST_USERNAME}`);
    });

    it('should login and receive access token', async () => {
      const response = await formRequest('/auth/login', {
        username: TEST_EMAIL,
        password: TEST_PASSWORD,
      });

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('access_token');
      expect(data).toHaveProperty('token_type', 'bearer');

      accessToken = data.access_token;
      console.log('✓ Login successful, token received');
    });

    it('should get current user with valid token', async () => {
      const response = await apiRequest('/auth/me');

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.email).toBe(TEST_EMAIL);
      userId = data.id;
      console.log(`✓ Got current user: ${data.email}`);
    });

    it('should reject invalid tokens', async () => {
      const response = await fetch(`${BASE_URL}/auth/me`, {
        headers: {
          Authorization: 'Bearer invalid_token_12345',
        },
      });

      expect([401, 403]).toContain(response.status);
      console.log('✓ Invalid token correctly rejected');
    });

    it('should reject requests without token', async () => {
      const response = await fetch(`${BASE_URL}/auth/me`);

      expect([401, 403]).toContain(response.status);
      console.log('✓ Unauthenticated request correctly rejected');
    });
  });

  // ============= Profile Management =============

  describe('Profile', () => {
    it('should get user profile', async () => {
      const response = await apiRequest('/users/profile/');

      // Profile might exist (200) or not yet (404)
      expect([200, 404]).toContain(response.status);
      console.log(`✓ Profile endpoint accessible (status: ${response.status})`);
    });

    it('should update user profile', async () => {
      const profileData = {
        profession: 'Frontend Developer',
        skills: ['TypeScript', 'React', 'React Native', 'Jest'],
        experience_years: 3,
        preferences: {
          remote_only: true,
          job_types: ['full_time'],
        },
      };

      const response = await apiRequest('/users/profile/', {
        method: 'PUT',
        body: JSON.stringify(profileData),
      });

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.profession).toBe('Frontend Developer');
      expect(data.skills).toContain('TypeScript');
      console.log(`✓ Profile updated: ${data.profession}`);
    });

    it('should persist profile changes', async () => {
      const response = await apiRequest('/users/profile/');

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.profession).toBe('Frontend Developer');
      expect(data.experience_years).toBe(3);
      console.log('✓ Profile changes persisted');
    });
  });

  // ============= Jobs =============

  describe('Jobs', () => {
    it('should list available jobs', async () => {
      const response = await apiRequest('/jobs/');

      expect(response.status).toBe(200);

      const data = await response.json();
      // Response could be array or paginated
      const jobs = Array.isArray(data)
        ? data
        : data.items || data.jobs || [];

      if (jobs.length > 0) {
        jobId = jobs[0].id;
        console.log(`✓ Listed ${jobs.length} jobs, first ID: ${jobId}`);
      } else {
        console.log('✓ Jobs endpoint works (no jobs in database)');
      }
    });

    it('should get single job details', async () => {
      if (!jobId) {
        console.log('⏭ Skipping: No jobs available');
        return;
      }

      const response = await apiRequest(`/jobs/${jobId}/`);

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.id).toBe(jobId);
      console.log(`✓ Got job: ${data.title || 'N/A'}`);
    });

    it('should search jobs with filters', async () => {
      const response = await apiRequest('/jobs/?remote=true&limit=10');

      expect(response.status).toBe(200);
      console.log('✓ Job search with filters works');
    });
  });

  // ============= Matches =============

  describe('Matches', () => {
    it('should create a match (save job)', async () => {
      if (!jobId) {
        console.log('⏭ Skipping: No jobs available');
        return;
      }

      const response = await apiRequest('/matches/', {
        method: 'POST',
        body: JSON.stringify({
          job_id: jobId,
          status: 'saved',
        }),
      });

      // 200/201 for created, 409 if already exists
      expect([200, 201, 409]).toContain(response.status);

      if (response.status !== 409) {
        const data = await response.json();
        matchId = data.id;
        console.log(`✓ Created match ID: ${matchId}`);
      } else {
        console.log('✓ Job already saved');
      }
    });

    it('should list user matches', async () => {
      const response = await apiRequest('/matches/');

      expect(response.status).toBe(200);

      const data = await response.json();
      const matches = Array.isArray(data)
        ? data
        : data.items || data.matches || [];

      // Get matchId if we don't have one
      if (!matchId && matches.length > 0) {
        matchId = matches[0].id;
      }

      console.log(`✓ Listed ${matches.length} matches`);
    });

    it('should update match status', async () => {
      if (!matchId) {
        console.log('⏭ Skipping: No matches available');
        return;
      }

      const response = await apiRequest(`/matches/${matchId}/status/`, {
        method: 'PUT',
        body: JSON.stringify({ status: 'applied' }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.status).toBe('applied');
      console.log('✓ Match status updated to: applied');
    });

    it('should filter matches by status', async () => {
      const response = await apiRequest('/matches/?status=applied');

      expect(response.status).toBe(200);
      console.log('✓ Match filtering works');
    });
  });

  // ============= Subscriptions (if available) =============

  describe('Subscriptions', () => {
    it('should get subscription status', async () => {
      const response = await apiRequest('/subscriptions/status');

      if (response.status === 200) {
        const data = await response.json();
        console.log(`✓ Subscription tier: ${data.tier || 'unknown'}`);
      } else if (response.status === 404) {
        console.log('✓ Subscription endpoint not implemented');
      } else {
        console.log(`! Subscription returned: ${response.status}`);
      }
    });
  });

  // ============= Error Handling =============

  describe('Error Handling', () => {
    it('should return 404 for non-existent resources', async () => {
      const response = await apiRequest('/jobs/non-existent-job-id-12345/');

      expect([404, 422]).toContain(response.status);
      console.log('✓ 404 returned for non-existent resource');
    });

    it('should return validation error for invalid data', async () => {
      const response = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: 'invalid-email',
          password: '123', // Too short
        }),
      });

      expect([400, 422]).toContain(response.status);
      console.log('✓ Validation error returned for invalid data');
    });
  });

  // ============= Token Refresh (if available) =============

  describe('Token Refresh', () => {
    it('should refresh access token', async () => {
      const response = await apiRequest('/auth/refresh', {
        method: 'POST',
      });

      if (response.status === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('access_token');
        console.log('✓ Token refreshed successfully');
      } else if (response.status === 404) {
        console.log('✓ Token refresh not implemented (stateless JWT)');
      }
    });
  });
});
