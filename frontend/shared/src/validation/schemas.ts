/**
 * Zod Validation Schemas
 * Shared runtime validation between web and mobile
 */

import { z } from 'zod';

// ============= Auth Schemas =============
export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

export const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  username: z
    .string()
    .min(3, 'Username must be at least 3 characters')
    .max(100, 'Username must be less than 100 characters')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores, and hyphens'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .max(100, 'Password must be less than 100 characters'),
});

// ============= Profile Schemas =============
export const updateProfileSchema = z.object({
  profession: z.string().optional(),
  job_title: z.string().optional(),
  skills: z.array(z.string()).optional(),
  experience_years: z.number().min(0).max(50).optional(),
  certifications: z.array(z.string()).optional(),
  preferences: z.object({
    remote_only: z.boolean().optional(),
    industries: z.array(z.string()).optional(),
    job_types: z.array(z.string()).optional(),
    avoid_keywords: z.array(z.string()).optional(),
  }).optional(),
  min_rate_usd: z.number().min(0).optional(),
  max_hours_per_week: z.number().min(1).max(168).optional(),
  availability: z.record(z.any()).optional(),
  portfolio: z.record(z.any()).optional(),
});

// ============= Job Search Schemas =============
export const jobSearchSchema = z.object({
  keywords: z.array(z.string()).optional(),
  profession: z.string().optional(),
  location: z.string().optional(),
  remote_only: z.boolean().optional(),
  min_rate: z.number().min(0).optional(),
  max_rate: z.number().min(0).optional(),
  limit: z.number().min(1).max(100).optional(),
});

// ============= Match Schemas =============
export const jobMatchStatusSchema = z.enum([
  'new',
  'saved',
  'applied',
  'interviewing',
  'hired',
  'rejected',
  'pending',
  'viewed',
]);

export const createMatchSchema = z.object({
  job_id: z.string().uuid('Invalid job ID'),
  status: jobMatchStatusSchema.optional(),
});

export const updateMatchSchema = z.object({
  status: jobMatchStatusSchema.optional(),
  client_notes: z.string().max(5000).optional(),
});

// ============= Proposal Schemas =============
export const proposalToneSchema = z.enum(['short', 'medium', 'full']);

export const enhancementTypeSchema = z.enum([
  'add_keywords',
  'improve_tone',
  'add_metrics',
  'shorten',
  'expand',
]);

export const generateProposalSchema = z.object({
  job_id: z.string().uuid().optional(),
  job_description: z.string().min(50).max(50000).optional(),
  tone: proposalToneSchema.optional(),
  custom_instructions: z.string().max(2000).optional(),
}).refine(
  (data) => data.job_id || data.job_description,
  { message: 'Either job_id or job_description is required' }
);

export const enhanceProposalSchema = z.object({
  proposal: z.string().min(50, 'Proposal must be at least 50 characters'),
  enhancement_type: enhancementTypeSchema,
  job_description: z.string().optional(),
});

export const parseJDSchema = z.object({
  job_description: z.string().min(50, 'Job description must be at least 50 characters'),
});

// ============= Subscription Schemas =============
export const subscriptionTierSchema = z.enum(['free', 'starter', 'pro', 'power']);

export const createCheckoutSchema = z.object({
  tier: subscriptionTierSchema,
  success_url: z.string().url().optional(),
  cancel_url: z.string().url().optional(),
});

// ============= Pagination Schemas =============
export const paginationSchema = z.object({
  page: z.number().min(1).optional().default(1),
  size: z.number().min(1).max(100).optional().default(20),
});

// ============= Type Exports =============
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type UpdateProfileInput = z.infer<typeof updateProfileSchema>;
export type JobSearchInput = z.infer<typeof jobSearchSchema>;
export type CreateMatchInput = z.infer<typeof createMatchSchema>;
export type UpdateMatchInput = z.infer<typeof updateMatchSchema>;
export type GenerateProposalInput = z.infer<typeof generateProposalSchema>;
export type EnhanceProposalInput = z.infer<typeof enhanceProposalSchema>;
export type ParseJDInput = z.infer<typeof parseJDSchema>;
export type CreateCheckoutInput = z.infer<typeof createCheckoutSchema>;
export type PaginationInput = z.infer<typeof paginationSchema>;
