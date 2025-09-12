import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatVolume(volume: number | null): string {
  if (!volume) return 'N/A'
  if (volume >= 1000000) {
    return `$${(volume / 1000000).toFixed(2)}M`
  }
  return `$${(volume / 1000).toFixed(0)}K`
}

/**
 * Encode slashes in model IDs for safe use in URLs
 * Replaces forward slashes (/) with double dashes (--)
 */
export function encodeSlashes(id: string): string {
  return id.replace(/\//g, '--')
}

/**
 * Decode slashes from URL-encoded model IDs
 * Replaces double dashes (--) with forward slashes (/)
 */
export function decodeSlashes(encodedId: string): string {
  return encodedId.replace(/--/g, '/')
}