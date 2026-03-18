import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | undefined | null): string {
  if (value == null) return '—';
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}B`;
  if (value >= 1) return `$${value.toFixed(0)}M`;
  return `$${(value * 1000).toFixed(0)}K`;
}

export function formatScore(score: number | undefined | null): string {
  if (score == null) return '—';
  return score.toFixed(0);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}
