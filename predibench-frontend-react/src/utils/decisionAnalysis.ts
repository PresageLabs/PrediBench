import type { ModelInvestmentDecision } from '../api'
import { apiService } from '../api'

export interface DecisionDriver {
  eventTitle: string
  marketQuestion: string
  betAmount: number
  returnAmount: number
  returnPercentage: number
  priceChange: number
  startPrice: number
  endPrice: number
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
  const eventDriversMap = new Map<string, DecisionDriver>()
  let totalReturn = 0
  let totalBets = 0

  // Determine the end date for this position (when the next decision was made)
  const endDate = nextDecision?.target_date || null


  // Process each event decision
  for (const eventDecision of decision.event_investment_decisions) {
    try {
      // Get event details including market prices
      const event = await apiService.getEventDetails(eventDecision.event_id)

      let eventTotalReturn = 0
      let eventTotalBet = 0
      let eventBetCount = 0
      let eventMarketQuestions: string[] = []

      // Process each market decision within this event
      for (const marketDecision of eventDecision.market_investment_decisions) {
        const betAmount = marketDecision.model_decision.bet
        totalBets++
        eventBetCount++
        eventTotalBet += Math.abs(betAmount)

        // Collect market questions for aggregated display
        if (marketDecision.market_question) {
          eventMarketQuestions.push(marketDecision.market_question)
        }

        // Find the market in the event data
        const market = event.markets.find(m => m.id === marketDecision.market_id)
        if (!market || !market.prices || market.prices.length === 0) continue

        // Find start price (price on decision date)
        const startPricePoint = market.prices.find(p => p.date >= decision.target_date)
        if (!startPricePoint) continue
        const startPrice = startPricePoint.value

        // Find end price (latest price before or on end date, or latest available)
        let endPrice = startPrice
        if (endDate) {
          // Find the latest price before or on the end date
          const endPricePoint = market.prices
            .filter(p => p.date <= endDate)
            .sort((a, b) => b.date.localeCompare(a.date))[0]
          if (endPricePoint) {
            endPrice = endPricePoint.value
          }
        } else {
          // Use the latest available price
          const latestPrice = market.prices
            .sort((a, b) => b.date.localeCompare(a.date))[0]
          if (latestPrice) {
            endPrice = latestPrice.value
          }
        }

        // Calculate returns using the same logic as in ModelsPage
        const priceChange = endPrice - startPrice
        const returnAmount = betAmount * priceChange

        totalReturn += returnAmount
        eventTotalReturn += returnAmount
      }

      const eventReturnPercentage = eventTotalBet > 0 ? (eventTotalReturn / eventTotalBet) * 100 : 0
      const marketSummary = eventMarketQuestions.length > 0
        ? eventMarketQuestions.slice(0, 2).join(", ") + (eventMarketQuestions.length > 2 ? "..." : "")
        : eventBetCount > 0 ? `${eventBetCount} markets` : `${eventDecision.market_investment_decisions.length} markets`

      // Check if we already have this event title and merge if so
      const existingEvent = eventDriversMap.get(eventDecision.event_title)
      if (existingEvent) {
        // Only merge if both have bets or if existing has no bets and current has bets
        const combinedBetAmount = existingEvent.betAmount + eventTotalBet
        const combinedReturnAmount = existingEvent.returnAmount + eventTotalReturn
        const combinedReturnPercentage = combinedBetAmount > 0 ? (combinedReturnAmount / combinedBetAmount) * 100 : 0

        eventDriversMap.set(eventDecision.event_title, {
          eventTitle: eventDecision.event_title,
          marketQuestion: marketSummary, // Use latest market summary
          betAmount: combinedBetAmount,
          returnAmount: combinedReturnAmount,
          returnPercentage: combinedReturnPercentage,
          priceChange: 0, // Not meaningful at event level
          startPrice: 0,  // Not meaningful at event level
          endPrice: 0     // Not meaningful at event level
        })
      } else {
        // Add new event (even if no bets)
        eventDriversMap.set(eventDecision.event_title, {
          eventTitle: eventDecision.event_title,
          marketQuestion: marketSummary,
          betAmount: eventTotalBet,
          returnAmount: eventTotalReturn,
          returnPercentage: eventReturnPercentage,
          priceChange: 0, // Not meaningful at event level
          startPrice: 0,  // Not meaningful at event level
          endPrice: 0     // Not meaningful at event level
        })
      }
    } catch (error) {
      console.error(`Failed to analyze event ${eventDecision.event_id}:`, error)
    }
  }

  // Convert map to array and sort: events with bets first (by return impact), then events without bets
  const drivers = Array.from(eventDriversMap.values())
  const sortedDrivers = drivers.sort((a, b) => {
    // If one has bets and the other doesn't, prioritize the one with bets
    if (a.betAmount > 0 && b.betAmount === 0) return -1
    if (a.betAmount === 0 && b.betAmount > 0) return 1

    // If both have bets or both have no bets, sort by absolute return amount
    return Math.abs(b.returnAmount) - Math.abs(a.returnAmount)
  })

  return {
    totalReturn,
    totalBets,
    topDrivers: sortedDrivers // Return all event drivers, sorted by impact
  }
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