/**
 * Formatting Utilities
 * Shared formatters for consistent display across platforms
 */

/**
 * Format currency amount
 */
export function formatCurrency(
  amount: number | undefined | null,
  options: {
    currency?: string;
    locale?: string;
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
  } = {}
): string {
  if (amount === undefined || amount === null) return '-';

  const {
    currency = 'USD',
    locale = 'en-US',
    minimumFractionDigits = 0,
    maximumFractionDigits = 0,
  } = options;

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(amount);
}

/**
 * Format hourly rate range
 */
export function formatRateRange(
  min: number | undefined | null,
  max: number | undefined | null,
  rateType: string = 'hourly'
): string {
  const suffix = rateType === 'hourly' ? '/hr' : rateType === 'yearly' ? '/yr' : '';

  if (min && max) {
    return `${formatCurrency(min)} - ${formatCurrency(max)}${suffix}`;
  }
  if (min) {
    return `${formatCurrency(min)}+${suffix}`;
  }
  if (max) {
    return `Up to ${formatCurrency(max)}${suffix}`;
  }
  return 'Rate not specified';
}

/**
 * Format relative time (e.g., "2 hours ago", "3 days ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);

  if (months > 0) return `${months} month${months > 1 ? 's' : ''} ago`;
  if (weeks > 0) return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  return 'Just now';
}

/**
 * Format date for display
 */
export function formatDate(
  date: string | Date | undefined | null,
  options: Intl.DateTimeFormatOptions = {}
): string {
  if (!date) return '-';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  };

  return new Date(date).toLocaleDateString('en-US', defaultOptions);
}

/**
 * Format score as percentage
 */
export function formatScore(score: number | undefined | null): string {
  if (score === undefined || score === null) return '-';
  return `${Math.round(score)}%`;
}

/**
 * Format experience years
 */
export function formatExperience(years: number | undefined | null): string {
  if (years === undefined || years === null) return 'Not specified';
  if (years === 0) return 'Entry level';
  if (years === 1) return '1 year';
  return `${years} years`;
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(
  text: string | undefined | null,
  maxLength: number,
  suffix: string = '...'
): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - suffix.length).trim() + suffix;
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number | undefined | null): string {
  if (bytes === undefined || bytes === null) return '-';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}
