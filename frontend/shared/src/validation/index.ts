/**
 * Validation Module
 * Zod schemas for runtime validation on web and mobile
 */

export * from './schemas';

// Re-export Zod for convenience
export { z } from 'zod';
export type { ZodError, ZodIssue } from 'zod';
