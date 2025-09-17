import type { ModelInvestmentDecision } from '../api'

export interface DecisionDriver {
  eventId: string
  eventTitle: string
  marketQuestion: string
  betAmount: number
  returnAmount: number // dollars
  returnPercentage: number // optional, unused in UI
  priceChange: number // unused in UI
  startPrice: number // unused in UI
  endPrice: number // unused in UI
}

export interface DecisionAnalysis {
  totalReturn: number
  totalBets: number
  topDrivers: DecisionDriver[]
}

/**
 * Calculate returns for a specific decision and identify the top contributing factors
 */
export async function calculateDecisionReturns(
  decision: ModelInvestmentDecision,
  nextDecision?: ModelInvestmentDecision
): Promise<DecisionAnalysis> {
  // Use backend event-level net_gains_until_next_decision when available; fallback to summing market gains
  const endDate = nextDecision?.target_date || null
  const drivers: DecisionDriver[] = []
  let totalReturn = 0
  let totalBets = 0

  for (const eventDecision of decision.event_investment_decisions) {
    const marketCount = eventDecision.market_investment_decisions.length
    const eventBet = eventDecision.market_investment_decisions.reduce((acc, md) => acc + Math.abs(md.decision.bet), 0)

    let eventReturn = 0
    const series = eventDecision.net_gains_until_next_decision || []
    if (series.length > 0) {
      if (!endDate) {
        eventReturn = series[series.length - 1]?.value ?? 0
      } else {
        const candidates = series.filter(p => p.date <= endDate)
        eventReturn = candidates.length ? candidates[candidates.length - 1].value : 0
      }
    } else {
      // Fallback: sum market gains
      eventReturn = eventDecision.market_investment_decisions.reduce((acc, md) => acc + (md.net_gains_at_decision_end ?? 0), 0)
    }

    totalReturn += eventReturn
    totalBets += marketCount
    drivers.push({
      eventId: eventDecision.event_id,
      eventTitle: eventDecision.event_title,
      marketQuestion: `${marketCount} markets`,
      betAmount: eventBet,
      returnAmount: eventReturn,
      returnPercentage: eventBet > 0 ? (eventReturn / eventBet) * 100 : 0,
      priceChange: 0,
      startPrice: 0,
      endPrice: 0,
    })
  }

  const sortedDrivers = drivers.sort((a, b) => Math.abs(b.returnAmount) - Math.abs(a.returnAmount))
  return { totalReturn, totalBets, topDrivers: sortedDrivers }
}

/**
 * Get the next decision date for a given decision to determine position end date
 */
export function findNextDecision(
  currentDecision: ModelInvestmentDecision,
  allDecisions: ModelInvestmentDecision[]
): ModelInvestmentDecision | undefined {
  // Sort all decisions by date
  const sortedDecisions = [...allDecisions].sort((a, b) =>
    a.target_date.localeCompare(b.target_date)
  )

  // Find current decision index
  const currentIndex = sortedDecisions.findIndex(d =>
    d.target_date === currentDecision.target_date
  )

  // Return next decision if it exists
  if (currentIndex >= 0 && currentIndex < sortedDecisions.length - 1) {
    return sortedDecisions[currentIndex + 1]
  }

  return undefined
}

/**
 * Format a decision summary for tooltip display
 */
export function formatDecisionSummary(
  date: string,
  analysis: DecisionAnalysis
): string {
  const formattedDate = new Date(date).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric'
  })

  let summary = `${formattedDate}: ${analysis.totalBets} bets taken`

  if (analysis.topDrivers.length > 0) {
    summary += '\n'
    analysis.topDrivers.forEach((driver) => {
      const sign = driver.returnAmount >= 0 ? '+' : ''
      summary += `• ${driver.eventTitle} - bet on ${driver.marketQuestion.substring(0, 30)}${driver.marketQuestion.length > 30 ? '...' : ''}, ${sign}${(driver.returnPercentage).toFixed(1)}% returns\n`
    })
  }

  return summary.trim()
}
