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