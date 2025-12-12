/**
 * Helper Utilities
 * Shared business logic helpers for web and mobile
 */

import type { Job, ScoredJob, JobMatch, JobMatchStatus, UserProfile, ScoreBreakdown } from '../types';

// ============= Job Helpers =============

/**
 * Check if a job is remote
 */
export function isRemoteJob(job: Job | ScoredJob): boolean {
  return job.remote || job.location?.toLowerCase().includes('remote') || false;
}

/**
 * Get job location display string
 */
export function getJobLocationDisplay(job: Job | ScoredJob): string {
  if (job.remote) {
    return job.location ? `Remote (${job.location})` : 'Remote';
  }
  return job.location || 'Location not specified';
}

/**
 * Check if job matches user's rate requirements
 */
export function jobMeetsRateRequirements(
  job: Job | ScoredJob,
  minRate: number | undefined
): boolean {
  if (!minRate) return true;
  if (!job.rate_min && !job.rate_max) return true; // Unknown rate
  if (job.rate_max && job.rate_max >= minRate) return true;
  if (job.rate_min && job.rate_min >= minRate) return true;
  return false;
}

/**
 * Get matching skills between job and user
 */
export function getMatchingSkills(
  jobSkills: string[] | undefined,
  userSkills: string[]
): string[] {
  if (!jobSkills || !userSkills) return [];

  const normalizedUserSkills = userSkills.map((s) => s.toLowerCase());
  return jobSkills.filter((skill) =>
    normalizedUserSkills.includes(skill.toLowerCase())
  );
}

/**
 * Get missing skills for a job
 */
export function getMissingSkills(
  jobSkills: string[] | undefined,
  userSkills: string[]
): string[] {
  if (!jobSkills) return [];
  if (!userSkills || userSkills.length === 0) return jobSkills;

  const normalizedUserSkills = userSkills.map((s) => s.toLowerCase());
  return jobSkills.filter(
    (skill) => !normalizedUserSkills.includes(skill.toLowerCase())
  );
}

/**
 * Calculate skill match percentage
 */
export function calculateSkillMatchPercent(
  jobSkills: string[] | undefined,
  userSkills: string[]
): number {
  if (!jobSkills || jobSkills.length === 0) return 100;
  const matching = getMatchingSkills(jobSkills, userSkills);
  return Math.round((matching.length / jobSkills.length) * 100);
}

// ============= Match Status Helpers =============

export const MATCH_STATUS_ORDER: JobMatchStatus[] = [
  'new',
  'saved',
  'applied',
  'interviewing',
  'hired',
  'rejected',
];

export const MATCH_STATUS_LABELS: Record<JobMatchStatus, string> = {
  new: 'New',
  saved: 'Saved',
  applied: 'Applied',
  interviewing: 'Interviewing',
  hired: 'Hired',
  rejected: 'Rejected',
  pending: 'Pending',
  viewed: 'Viewed',
};

export const MATCH_STATUS_COLORS: Record<JobMatchStatus, string> = {
  new: '#3b82f6', // blue
  saved: '#8b5cf6', // purple
  applied: '#f59e0b', // amber
  interviewing: '#06b6d4', // cyan
  hired: '#22c55e', // green
  rejected: '#ef4444', // red
  pending: '#6b7280', // gray
  viewed: '#6b7280', // gray
};

/**
 * Get next status in pipeline
 */
export function getNextStatus(currentStatus: JobMatchStatus): JobMatchStatus | null {
  const index = MATCH_STATUS_ORDER.indexOf(currentStatus);
  if (index === -1 || index >= MATCH_STATUS_ORDER.length - 1) return null;
  return MATCH_STATUS_ORDER[index + 1];
}

/**
 * Check if status transition is valid
 */
export function isValidStatusTransition(
  from: JobMatchStatus,
  to: JobMatchStatus
): boolean {
  // Can always go to rejected
  if (to === 'rejected') return true;

  // Can always save a new job
  if (from === 'new' && to === 'saved') return true;

  // Check forward progression
  const fromIndex = MATCH_STATUS_ORDER.indexOf(from);
  const toIndex = MATCH_STATUS_ORDER.indexOf(to);

  return toIndex > fromIndex;
}

// ============= Score Helpers =============

/**
 * Get score category label
 */
export function getScoreCategory(score: number): string {
  if (score >= 90) return 'Excellent Match';
  if (score >= 75) return 'Great Match';
  if (score >= 60) return 'Good Match';
  if (score >= 40) return 'Fair Match';
  return 'Low Match';
}

/**
 * Get score color
 */
export function getScoreColor(score: number): string {
  if (score >= 90) return '#22c55e'; // green
  if (score >= 75) return '#84cc16'; // lime
  if (score >= 60) return '#eab308'; // yellow
  if (score >= 40) return '#f97316'; // orange
  return '#ef4444'; // red
}

/**
 * Get most impactful score factors (top 3)
 */
export function getTopScoreFactors(
  breakdown: ScoreBreakdown | Record<string, number>
): { factor: string; score: number }[] {
  return Object.entries(breakdown)
    .map(([factor, score]) => ({
      factor: factor.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      score: score as number,
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

// ============= Profile Helpers =============

/**
 * Calculate profile completion percentage
 */
export function calculateProfileCompletion(profile: UserProfile | null): number {
  if (!profile) return 0;

  const fields = [
    { value: profile.profession, weight: 15 },
    { value: profile.skills?.length, weight: 20 },
    { value: profile.experience_years, weight: 15 },
    { value: profile.min_rate_usd, weight: 10 },
    { value: profile.certifications?.length, weight: 10 },
    { value: profile.preferences?.industries?.length, weight: 10 },
    { value: profile.portfolio?.github || profile.portfolio?.website, weight: 10 },
    { value: profile.job_title, weight: 10 },
  ];

  const total = fields.reduce((sum, field) => {
    const hasValue = field.value !== undefined && field.value !== null && field.value !== '' && field.value !== 0;
    return sum + (hasValue ? field.weight : 0);
  }, 0);

  return total;
}

/**
 * Get profile completion suggestions
 */
export function getProfileSuggestions(profile: UserProfile | null): string[] {
  if (!profile) return ['Create your profile to get personalized job matches'];

  const suggestions: string[] = [];

  if (!profile.profession) suggestions.push('Add your profession');
  if (!profile.skills?.length) suggestions.push('Add your skills');
  if (!profile.experience_years) suggestions.push('Add your years of experience');
  if (!profile.min_rate_usd) suggestions.push('Set your minimum rate');
  if (!profile.certifications?.length) suggestions.push('Add your certifications');
  if (!profile.preferences?.industries?.length) suggestions.push('Select preferred industries');
  if (!profile.portfolio?.github && !profile.portfolio?.website) {
    suggestions.push('Add your portfolio or GitHub');
  }

  return suggestions.slice(0, 3);
}

// ============= General Helpers =============

/**
 * Deep merge objects
 */
export function deepMerge<T extends Record<string, any>>(
  target: T,
  source: Partial<T>
): T {
  const result = { ...target };

  for (const key of Object.keys(source) as (keyof T)[]) {
    const sourceValue = source[key];
    const targetValue = target[key];

    if (
      sourceValue !== undefined &&
      typeof sourceValue === 'object' &&
      !Array.isArray(sourceValue) &&
      sourceValue !== null &&
      typeof targetValue === 'object' &&
      !Array.isArray(targetValue) &&
      targetValue !== null
    ) {
      result[key] = deepMerge(
        targetValue as Record<string, any>,
        sourceValue as Record<string, any>
      ) as T[keyof T];
    } else if (sourceValue !== undefined) {
      result[key] = sourceValue as T[keyof T];
    }
  }

  return result;
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Generate a unique ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}
