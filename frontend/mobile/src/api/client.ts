import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import type {
  User,
  UserProfile,
  Job,
  ScoredJob,
  JobMatch,
  SearchQuery,
  SearchResponse,
  AuthResponse,
  PaginatedResponse,
  GeneratedProposal,
  AllTonesResponse,
  ParsedJD,
  Resume,
  SubscriptionWithUsage,
  JobMatchStatus,
} from '../../shared/src/types';

// For simulators/emulators:
// - iOS Simulator: Use machine's IP address
// - Android Emulator: Use 10.0.2.2 (special alias for host)
function getDefaultApiUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return Platform.select({
    ios: 'http://192.168.1.160:8080',
    android: 'http://10.0.2.2:8080',
    default: 'http://localhost:8080',
  }) as string;
}

const API_URL = getDefaultApiUrl();
const TOKEN_KEY = 'auth_token';

console.log('[API] Initialized with URL:', API_URL);

// In-memory token cache to prevent race conditions with SecureStore
let tokenCache: string | null = null;

// Token management with in-memory cache
export async function getToken(): Promise<string | null> {
  // Return cached token immediately if available
  if (tokenCache) {
    console.log('[API] getToken (cached):', `${tokenCache.substring(0, 20)}...`);
    return tokenCache;
  }

  try {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    console.log('[API] getToken (SecureStore):', token ? `${token.substring(0, 20)}...` : 'null');
    if (token) {
      tokenCache = token; // Update cache
    }
    return token;
  } catch (error) {
    console.log('[API] getToken error:', error);
    return null;
  }
}

export async function setToken(token: string): Promise<void> {
  console.log('[API] setToken:', token ? `${token.substring(0, 20)}...` : 'null');

  // Set in-memory cache immediately
  tokenCache = token;
  console.log('[API] setToken: cached in memory');

  // Also persist to SecureStore
  try {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    // Verify it was stored
    const stored = await SecureStore.getItemAsync(TOKEN_KEY);
    console.log('[API] setToken verified in SecureStore:', stored ? 'yes' : 'NO!');
  } catch (error) {
    console.log('[API] setToken SecureStore error (using memory cache):', error);
  }
}

export async function removeToken(): Promise<void> {
  console.log('[API] removeToken');
  tokenCache = null; // Clear cache
  try {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch (error) {
    console.log('[API] removeToken error:', error);
  }
}

// Initialize token from SecureStore on module load
(async () => {
  try {
    const storedToken = await SecureStore.getItemAsync(TOKEN_KEY);
    if (storedToken) {
      tokenCache = storedToken;
      console.log('[API] Initialized token cache from SecureStore');
    }
  } catch (error) {
    console.log('[API] Failed to initialize token cache:', error);
  }
})();

// Base fetch wrapper
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  console.log(`[API] ${options.method || 'GET'} ${endpoint}`);
  const token = await getToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    console.log('[API] Authorization header set');
  } else {
    console.log('[API] No token available for request');
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  console.log(`[API] Response: ${response.status} ${response.statusText}`);

  if (response.status === 401) {
    console.log('[API] 401 Unauthorized - clearing token');
    await removeToken();
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    console.log('[API] Error:', error);
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

// Auth API
export const authApi = {
  async login(email: string, password: string): Promise<AuthResponse> {
    console.log(`[API] login attempt for: ${email}`);
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    console.log(`[API] login response: ${response.status}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      console.log('[API] login error:', error);
      throw new Error(error.detail || 'Login failed');
    }

    const data: AuthResponse = await response.json();
    console.log('[API] login success, token received:', data.access_token ? 'yes' : 'no');
    await setToken(data.access_token);
    return data;
  },

  async register(email: string, password: string, fullName?: string): Promise<User> {
    console.log(`[API] register attempt for: ${email}`);
    const user = await apiFetch<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        username: email,
        password,
        full_name: fullName,
      }),
    });
    console.log('[API] register success, user id:', user.id);
    return user;
  },

  async getCurrentUser(): Promise<User & { profile?: UserProfile }> {
    return apiFetch('/auth/me');
  },

  async logout(): Promise<void> {
    await removeToken();
  },
};

// Jobs API
// Note: FastAPI requires trailing slashes - without them, it returns 307 redirects
// which cause the Authorization header to be lost
export const jobsApi = {
  async getJobs(page = 1, size = 20): Promise<PaginatedResponse<Job>> {
    const offset = (page - 1) * size;
    const jobs = await apiFetch<Job[]>(`/jobs/?limit=${size}&offset=${offset}`);
    return {
      items: jobs,
      total: jobs.length,
      page,
      size,
      pages: 1,
    };
  },

  async getJob(jobId: string): Promise<Job> {
    return apiFetch(`/jobs/${jobId}/`);
  },

  async searchJobs(query: SearchQuery): Promise<SearchResponse> {
    return apiFetch('/jobs/search/', {
      method: 'POST',
      body: JSON.stringify(query),
    });
  },
};

// Matches API
export const matchesApi = {
  async getMatches(
    page = 1,
    size = 20,
    statusFilter?: JobMatchStatus,
    minScore = 0
  ): Promise<PaginatedResponse<JobMatch>> {
    const offset = (page - 1) * size;
    let url = `/matches/?limit=${size}&offset=${offset}&min_score=${minScore}`;
    if (statusFilter) {
      url += `&status_filter=${statusFilter}`;
    }
    const matches = await apiFetch<JobMatch[]>(url);
    return {
      items: matches,
      total: matches.length,
      page,
      size,
      pages: 1,
    };
  },

  async create(jobId: string): Promise<JobMatch> {
    return apiFetch('/matches/', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId }),
    });
  },

  async getMatch(matchId: string): Promise<JobMatch> {
    return apiFetch(`/matches/${matchId}/`);
  },

  async updateStatus(matchId: string, status: JobMatchStatus): Promise<JobMatch> {
    return apiFetch(`/matches/${matchId}/status/`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  },

  async updateMatchNotes(matchId: string, notes: string): Promise<JobMatch> {
    return apiFetch(`/matches/${matchId}/notes/`, {
      method: 'PUT',
      body: JSON.stringify({ client_notes: notes }),
    });
  },
};

// Profile API
export const profileApi = {
  async getProfile(): Promise<UserProfile> {
    return apiFetch('/users/profile/');
  },

  async updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
    return apiFetch('/users/profile/', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  },
};

// Resume API
export const resumeApi = {
  async getResume(): Promise<Resume> {
    return apiFetch('/resume/');
  },

  async uploadResume(file: {
    uri: string;
    name: string;
    type: string;
  }): Promise<{ message: string; resume: Resume }> {
    const token = await getToken();
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.type,
    } as any);

    const response = await fetch(`${API_URL}/resume/upload/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  },

  async deleteResume(): Promise<{ message: string }> {
    return apiFetch('/resume/', { method: 'DELETE' });
  },
};

// Proposals API
export const proposalsApi = {
  async generate(
    jobId: string,
    tone: 'short' | 'medium' | 'full' = 'medium'
  ): Promise<GeneratedProposal> {
    return apiFetch('/proposals/generate/', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, tone }),
    });
  },

  async generateProposal(request: {
    job_id?: string;
    parsed_jd?: ParsedJD;
    tone: 'short' | 'medium' | 'full';
    additional_context?: string;
  }): Promise<GeneratedProposal> {
    return apiFetch('/proposals/generate/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async generateAllTones(request: {
    job_id?: string;
    parsed_jd?: ParsedJD;
    additional_context?: string;
  }): Promise<AllTonesResponse> {
    return apiFetch('/proposals/generate-all/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
};

// Subscription API
export const subscriptionApi = {
  async getSubscription(): Promise<SubscriptionWithUsage> {
    return apiFetch('/subscription/');
  },
};

// Health check
export const healthApi = {
  async check(): Promise<{ status: string; timestamp: string }> {
    return apiFetch('/health/');
  },
};
