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
  AgentRunResponse,
  AgentStatusResponse,
  JobRadarRequest,
  JobRadarResult,
  CoverLetterRequest,
  CoverLetterResult,
  ResumeOptimizeRequest,
  ResumeOptimizeResult,
  InterviewPrepRequest,
  InterviewPrepResult,
  SalaryResearchRequest,
  SalaryResearchResult,
  SkillGapRequest,
  SkillGapResult,
  ApplicationTrackerRequest,
  ApplicationTrackerResult,
  NetworkIntelligenceRequest,
  NetworkIntelligenceResult,
  AutoApplyRequest,
  AutoApplyResult,
  JobFilters,
} from '@jobseeker/shared';

// For simulators/emulators:
// - iOS Simulator: Use machine's IP address
// - Android Emulator: Use 10.0.2.2 (special alias for host)
function getDefaultApiUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return Platform.select({
    ios: 'http://192.168.1.160:8000',
    android: 'http://10.0.2.2:8000',
    default: 'http://localhost:8000',
  }) as string;
}

export const API_URL = getDefaultApiUrl();
const TOKEN_KEY = 'auth_token';

console.log('[API] Initialized with URL:', API_URL);

// In-memory token cache to prevent race conditions with SecureStore
let tokenCache: string | null = null;

// Token management with in-memory cache
export async function getToken(): Promise<string | null> {
  // Return cached token immediately if available
  if (tokenCache) {
    console.log('[API] getToken (cached):', `${tokenCache}...`);
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
  async getJobs(page = 1, size = 20, filters?: JobFilters): Promise<PaginatedResponse<Job>> {
    const offset = (page - 1) * size;
    const params = new URLSearchParams();
    params.set('limit', size.toString());
    params.set('offset', offset.toString());

    // Add filter parameters if provided
    if (filters?.remote_only) params.set('remote_only', 'true');
    if (filters?.min_rate !== undefined) params.set('min_rate', filters.min_rate.toString());
    if (filters?.max_rate !== undefined) params.set('max_rate', filters.max_rate.toString());
    if (filters?.source) params.set('source', filters.source);
    if (filters?.location) params.set('location', filters.location);
    if (filters?.rate_type) params.set('rate_type', filters.rate_type);

    const jobs = await apiFetch<Job[]>(`/jobs/?${params.toString()}`);
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

// Users API - for updating user contact info and avatar
export const usersApi = {
  async updateUser(data: { full_name?: string; phone?: string }): Promise<User> {
    return apiFetch('/users/me/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async uploadAvatar(file: {
    uri: string;
    name: string;
    type: string;
  }): Promise<User> {
    const token = await getToken();
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      name: file.name,
      type: file.type,
    } as any);

    const response = await fetch(`${API_URL}/users/me/avatar`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Avatar upload failed');
    }

    return response.json();
  },

  async deleteAvatar(): Promise<User> {
    return apiFetch('/users/me/avatar', { method: 'DELETE' });
  },
};

// Resume API
const MAX_RESUME_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_RESUME_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];

export interface ResumeUploadOptions {
  onProgress?: (progress: number) => void;
}

// Resume upload error types for better user feedback
export class ResumeUploadError extends Error {
  code: string;
  constructor(message: string, code: string) {
    super(message);
    this.code = code;
    this.name = 'ResumeUploadError';
  }
}

export const resumeApi = {
  async getResume(): Promise<Resume> {
    return apiFetch('/resume');
  },

  validateResumeFile(file: { uri: string; name: string; type: string; size?: number }): void {
    // Validate file type
    if (!ALLOWED_RESUME_TYPES.includes(file.type)) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      // Also check by extension as MIME type may be unreliable
      const validExtensions = ['pdf', 'doc', 'docx', 'txt'];
      if (!ext || !validExtensions.includes(ext)) {
        throw new ResumeUploadError(
          'Invalid file type. Please upload a PDF, Word document (.doc, .docx), or text file.',
          'INVALID_FILE_TYPE'
        );
      }
    }

    // Validate file size if available
    if (file.size && file.size > MAX_RESUME_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      throw new ResumeUploadError(
        `File too large (${sizeMB}MB). Maximum size is 10MB.`,
        'FILE_TOO_LARGE'
      );
    }
  },

  async uploadResume(
    file: { uri: string; name: string; type: string; size?: number },
    options?: ResumeUploadOptions
  ): Promise<{ message: string; resume: Resume }> {
    // Validate file before upload
    this.validateResumeFile(file);

    const token = await getToken();
    if (!token) {
      throw new ResumeUploadError('Not authenticated. Please log in again.', 'NOT_AUTHENTICATED');
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      if (options?.onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            options.onProgress!(progress);
          }
        };
      }

      xhr.onload = async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch {
            reject(new ResumeUploadError('Invalid response from server', 'PARSE_ERROR'));
          }
        } else {
          // Parse error response
          try {
            const error = JSON.parse(xhr.responseText);
            const message = error.detail || 'Upload failed';

            // Map specific error codes
            if (xhr.status === 413) {
              reject(new ResumeUploadError('File too large. Maximum size is 10MB.', 'FILE_TOO_LARGE'));
            } else if (xhr.status === 415) {
              reject(new ResumeUploadError('Invalid file type. Please upload a PDF or Word document.', 'INVALID_FILE_TYPE'));
            } else if (xhr.status === 401) {
              reject(new ResumeUploadError('Session expired. Please log in again.', 'NOT_AUTHENTICATED'));
            } else if (message.includes('extract') || message.includes('parse')) {
              reject(new ResumeUploadError(
                'Could not read your resume. Try a simpler PDF format or paste your resume text directly.',
                'EXTRACTION_FAILED'
              ));
            } else {
              reject(new ResumeUploadError(message, 'UPLOAD_FAILED'));
            }
          } catch {
            reject(new ResumeUploadError('Upload failed. Please try again.', 'UPLOAD_FAILED'));
          }
        }
      };

      xhr.onerror = () => {
        reject(new ResumeUploadError(
          'Network error. Please check your connection and try again.',
          'NETWORK_ERROR'
        ));
      };

      xhr.ontimeout = () => {
        reject(new ResumeUploadError(
          'Upload timed out. Please try again with a smaller file or better connection.',
          'TIMEOUT'
        ));
      };

      // Set timeout to 2 minutes for large files
      xhr.timeout = 120000;

      xhr.open('POST', `${API_URL}/resume/upload`);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);

      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.type,
      } as any);

      xhr.send(formData);
    });
  },

  async deleteResume(): Promise<{ message: string }> {
    return apiFetch('/resume', { method: 'DELETE' });
  },

  async updateResume(data: {
    full_name?: string;
    email?: string;
    phone?: string;
    location?: string;
    summary?: string;
    linkedin_url?: string;
    github_url?: string;
    portfolio_url?: string;
    skills?: string[];
  }): Promise<Resume> {
    return apiFetch('/resume', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async reparseResume(): Promise<{ message: string; resume: Resume }> {
    return apiFetch('/resume/reparse', { method: 'POST' });
  },

  async submitResumeText(text: string): Promise<{ message: string; resume: Resume }> {
    return apiFetch('/resume/text', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  async getResumeDebug(): Promise<{
    file_name?: string;
    file_type?: string;
    raw_text_length: number;
    raw_text_preview?: string;
    parse_quality_score?: number;
    extracted_full_name?: string;
    extracted_skills_count: number;
    extracted_work_exp_count: number;
  }> {
    return apiFetch('/resume/debug/raw-text');
  },
};

// Proposals API
export const proposalsApi = {
  async generate(
    jobId: string,
    tone: 'short' | 'medium' | 'full' = 'medium'
  ): Promise<GeneratedProposal> {
    return apiFetch('/proposals/generate', {
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
    return apiFetch('/proposals/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async generateAllTones(request: {
    job_id?: string;
    parsed_jd?: ParsedJD;
    additional_context?: string;
  }): Promise<AllTonesResponse> {
    return apiFetch('/proposals/generate-all', {
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

// Digest Settings types
export interface DigestSettings {
  enabled: boolean;
  frequency: 'daily' | 'weekly';
  min_match_score: number;
  max_jobs: number;
  include_applied: boolean;
  preferred_time: string;
}

export interface DigestPreview {
  html_content: string;
  matches_count: number;
  stats: {
    total_new: number;
    high_quality_count: number;
    applied_count: number;
    average_score: number;
  };
}

// Digest API
export const digestApi = {
  async getSettings(): Promise<DigestSettings> {
    return apiFetch('/users/me/digest/settings');
  },

  async updateSettings(settings: Partial<DigestSettings>): Promise<DigestSettings> {
    return apiFetch('/users/me/digest/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  },

  async getPreview(): Promise<DigestPreview> {
    return apiFetch('/users/me/digest/preview');
  },

  async sendNow(): Promise<{ message: string; status: string }> {
    return apiFetch('/users/me/digest/send', { method: 'POST' });
  },
};

// Health check
export const healthApi = {
  async check(): Promise<{ status: string; timestamp: string }> {
    return apiFetch('/health/');
  },
};

// Agent API - Generic agent run/status/result pattern
export const agentApi = {
  // Job Radar
  async runJobRadar(request: JobRadarRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/radar/run', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getJobRadarStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/radar/status/${runId}`);
  },
  async getJobRadarResult(runId: string): Promise<JobRadarResult> {
    return apiFetch(`/agent/radar/result/${runId}`);
  },

  // Cover Letter
  async runCoverLetter(request: CoverLetterRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/cover-letter/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getCoverLetterStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/cover-letter/status/${runId}`);
  },
  async getCoverLetterResult(runId: string): Promise<CoverLetterResult> {
    return apiFetch(`/agent/cover-letter/result/${runId}`);
  },

  // Resume Optimizer
  async runResumeOptimize(request: ResumeOptimizeRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/resume/optimize', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getResumeOptimizeStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/resume/status/${runId}`);
  },
  async getResumeOptimizeResult(runId: string): Promise<ResumeOptimizeResult> {
    return apiFetch(`/agent/resume/result/${runId}`);
  },

  // Interview Prep
  async runInterviewPrep(request: InterviewPrepRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/interview/prep', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getInterviewPrepStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/interview/status/${runId}`);
  },
  async getInterviewPrepResult(runId: string): Promise<InterviewPrepResult> {
    return apiFetch(`/agent/interview/result/${runId}`);
  },

  // Salary Research
  async runSalaryResearch(request: SalaryResearchRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/salary/research', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getSalaryResearchStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/salary/status/${runId}`);
  },
  async getSalaryResearchResult(runId: string): Promise<SalaryResearchResult> {
    return apiFetch(`/agent/salary/result/${runId}`);
  },

  // Skill Gap
  async runSkillGap(request: SkillGapRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/skill-gap/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getSkillGapStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/skill-gap/status/${runId}`);
  },
  async getSkillGapResult(runId: string): Promise<SkillGapResult> {
    return apiFetch(`/agent/skill-gap/result/${runId}`);
  },

  // Application Tracker
  async runApplicationTracker(request: ApplicationTrackerRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/tracker/briefing', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getApplicationTrackerStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/tracker/status/${runId}`);
  },
  async getApplicationTrackerResult(runId: string): Promise<ApplicationTrackerResult> {
    return apiFetch(`/agent/tracker/result/${runId}`);
  },

  // Network Intelligence
  async runNetworkIntelligence(request: NetworkIntelligenceRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/network/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getNetworkIntelligenceStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/network/status/${runId}`);
  },
  async getNetworkIntelligenceResult(runId: string): Promise<NetworkIntelligenceResult> {
    return apiFetch(`/agent/network/result/${runId}`);
  },

  // Auto-Apply
  async runAutoApply(request: AutoApplyRequest): Promise<AgentRunResponse> {
    return apiFetch('/agent/apply/prepare', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },
  async getAutoApplyStatus(runId: string): Promise<AgentStatusResponse> {
    return apiFetch(`/agent/apply/status/${runId}`);
  },
  async getAutoApplyResult(runId: string): Promise<AutoApplyResult> {
    return apiFetch(`/agent/apply/result/${runId}`);
  },
};

// Reminder types
export interface Reminder {
  id: string;
  job_match_id: string;
  reminder_type: 'follow_up' | 'interview_prep' | 'interview' | 'deadline' | 'custom';
  title: string;
  description?: string;
  scheduled_for: string;
  is_completed: boolean;
  completed_at?: string;
  is_dismissed: boolean;
  notification_sent: boolean;
  created_at: string;
  updated_at: string;
  job_title?: string;
  company?: string;
}

export interface ReminderListResponse {
  reminders: Reminder[];
  total: number;
  overdue_count: number;
  upcoming_count: number;
}

// Reminders API
export const remindersApi = {
  async getReminders(
    includeCompleted = false,
    includeDismissed = false,
    limit = 50
  ): Promise<ReminderListResponse> {
    const params = new URLSearchParams();
    params.set('include_completed', includeCompleted.toString());
    params.set('include_dismissed', includeDismissed.toString());
    params.set('limit', limit.toString());
    return apiFetch(`/applications/reminders?${params.toString()}`);
  },

  async getUpcomingReminders(hoursAhead = 24): Promise<{ reminders: Reminder[]; hours_window: number }> {
    return apiFetch(`/applications/reminders/upcoming?hours_ahead=${hoursAhead}`);
  },

  async getOverdueReminders(): Promise<Reminder[]> {
    return apiFetch('/applications/reminders/overdue');
  },

  async createReminder(
    matchId: string,
    data: {
      title: string;
      scheduled_for: string;
      reminder_type?: 'follow_up' | 'interview_prep' | 'interview' | 'deadline' | 'custom';
      description?: string;
    }
  ): Promise<Reminder> {
    return apiFetch(`/applications/matches/${matchId}/reminders`, {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        reminder_type: data.reminder_type || 'custom',
      }),
    });
  },

  async completeReminder(reminderId: string): Promise<Reminder> {
    return apiFetch(`/applications/reminders/${reminderId}/complete`, {
      method: 'POST',
    });
  },

  async dismissReminder(reminderId: string): Promise<Reminder> {
    return apiFetch(`/applications/reminders/${reminderId}/dismiss`, {
      method: 'POST',
    });
  },

  async deleteReminder(reminderId: string): Promise<void> {
    return apiFetch(`/applications/reminders/${reminderId}`, {
      method: 'DELETE',
    });
  },
};
