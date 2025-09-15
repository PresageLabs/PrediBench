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
  const drivers: DecisionDriver[] = []
  let totalReturn = 0
  let totalBets = 0

  for (const eventDecision of decision.event_investment_decisions) {
    for (const marketDecision of eventDecision.market_investment_decisions) {
      const betAmount = marketDecision.decision.bet
      totalBets += 1
      const ret = marketDecision.gains_since_decision ?? 0
      totalReturn += ret

      drivers.push({
        eventId: eventDecision.event_id,
        eventTitle: eventDecision.event_title,
        marketQuestion: marketDecision.market_question || 'Market',
        betAmount: Math.abs(betAmount),
        returnAmount: ret,
        returnPercentage: Math.abs(betAmount) > 0 ? (ret / Math.abs(betAmount)) * 100 : 0,
        priceChange: 0,
        startPrice: 0,
        endPrice: 0,
      })
    }
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
