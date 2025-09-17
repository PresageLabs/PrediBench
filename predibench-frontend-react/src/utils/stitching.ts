import type { TimeseriesPoint } from '../api'

function sortByDateAsc<T extends { date: string }>(arr: T[]): T[] {
  return [...arr].sort((a, b) => a.date.localeCompare(b.date))
}

/**
 * Apply cutoff date rescaling to a pnl_history series from the backend.
 * The backend now provides portfolio values (starting around 1.0) in pnl_history.
 */
export function rescalePnlHistoryFromCutoff(
  pnlHistory: TimeseriesPoint[],
  cutoffDate: string
): TimeseriesPoint[] {
  if (pnlHistory.length === 0) return []

  // Sort all points by date
  const sortedSeries = sortByDateAsc(pnlHistory)

  // Find the value at cutoff date (or closest after)
  const cutoffPoint = sortedSeries.find(point => point.date >= cutoffDate)
  if (!cutoffPoint) return []

  const cutoffPortfolioValue = cutoffPoint.value

  // Rescale: divide by cutoff portfolio value to normalize to start at 1.0 on cutoff date
  // Values before cutoff are set to 1
  return sortedSeries.map(point => {
    if (point.date < cutoffDate) {
      return { date: point.date, value: 1 }
    }

    const rescaledPortfolioValue = point.value / cutoffPortfolioValue
    return {
      date: point.date,
      value: rescaledPortfolioValue
    }
  })
}
