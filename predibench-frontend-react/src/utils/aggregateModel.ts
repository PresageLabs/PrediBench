import type { LeaderboardEntry, TimeseriesPoint } from '../api'

const REQUIRED_MODELS = ['sonar-deep-research', 'grok-4-0709', 'gpt-5', 'deepseek-ai/DeepSeek-R1']
const AGGREGATE_MODEL_ID = 'presage-aggregate'
const AGGREGATE_MODEL_NAME = 'Presage Aggregate'

interface ModelDecision {
  model_id: string
  target_date: string
  event_id: string
  market_id: string
  bet: number
  estimated_probability: number
}

/**
 * Computes the median of an array of numbers
 */
function median(values: number[]): number {
  if (values.length === 0) {
    throw new Error('Cannot compute median of empty array')
  }

  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)

  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2
  }
  return sorted[mid]
}

/**
 * Creates an aggregate model based on median bets from the four required models
 * Only includes decisions for events where all 4 models have predictions
 */
export async function createAggregateModel(
  leaderboard: LeaderboardEntry[]
): Promise<LeaderboardEntry | null> {
  // First, we need to fetch all model decisions to compute the aggregate
  // We'll need to import apiService
  const { apiService } = await import('../api')

  // Filter to only the required models
  const requiredModelEntries = leaderboard.filter(entry =>
    REQUIRED_MODELS.includes(entry.model_id)
  )

  if (requiredModelEntries.length !== REQUIRED_MODELS.length) {
    return null
  }

  // Fetch all model results for the required models
  const modelResultsPromises = REQUIRED_MODELS.map(modelId =>
    apiService.getModelResultsById(modelId)
  )

  const allModelResults = await Promise.all(modelResultsPromises)

  // Build a structure to track decisions by (event_id, target_date, market_id)
  const decisionMap: Record<string, ModelDecision[]> = {}

  allModelResults.forEach((modelResults, modelIndex) => {
    const modelId = REQUIRED_MODELS[modelIndex]

    modelResults.forEach(decision => {
      const targetDate = decision.target_date

      decision.event_investment_decisions.forEach(eventDecision => {
        const eventId = eventDecision.event_id

        eventDecision.market_investment_decisions.forEach(marketDecision => {
          const marketId = marketDecision.market_id
          const bet = marketDecision.decision.bet
          const estimatedProbability = marketDecision.decision.estimated_probability

          // Only consider non-zero bets
          if (bet !== 0) {
            const key = `${eventId}|${targetDate}|${marketId}`

            if (!decisionMap[key]) {
              decisionMap[key] = []
            }

            decisionMap[key].push({
              model_id: modelId,
              target_date: targetDate,
              event_id: eventId,
              market_id: marketId,
              bet: bet,
              estimated_probability: estimatedProbability
            })
          }
        })
      })
    })
  })

  // Now create aggregate decisions: for each (event_id, target_date) where ALL 4 models have at least one decision,
  // compute median bet for each market

  // Group by event and target date
  const eventDateMap: Record<string, Set<string>> = {} // event_id|target_date -> Set<model_id>
  const eventDateMarkets: Record<string, Set<string>> = {} // event_id|target_date -> Set<market_id>

  Object.keys(decisionMap).forEach(key => {
    const decisions = decisionMap[key]
    const [eventId, targetDate, marketId] = key.split('|')
    const eventDateKey = `${eventId}|${targetDate}`

    if (!eventDateMap[eventDateKey]) {
      eventDateMap[eventDateKey] = new Set()
      eventDateMarkets[eventDateKey] = new Set()
    }

    decisions.forEach(d => eventDateMap[eventDateKey].add(d.model_id))
    eventDateMarkets[eventDateKey].add(marketId)
  })

  // Filter to only events where all 4 models made decisions
  const validEventDates = Object.keys(eventDateMap).filter(key =>
    eventDateMap[key].size === REQUIRED_MODELS.length
  )

  if (validEventDates.length === 0) {
    console.warn('No events found where all 4 required models made decisions')
    return null
  }

  // Now compute median bets AND median estimated_probability for each market in valid event-dates
  interface AggregateDecision {
    bet: number
    estimated_probability: number
  }
  const aggregateDecisions: { [key: string]: AggregateDecision } = {} // key: event_id|target_date|market_id

  validEventDates.forEach(eventDateKey => {
    const markets = eventDateMarkets[eventDateKey]

    markets.forEach(marketId => {
      const key = `${eventDateKey}|${marketId}`
      const decisions = decisionMap[key] || []

      // Only compute median if we have decisions
      if (decisions.length > 0) {
        const bets = decisions.map(d => d.bet)
        const estimatedProbabilities = decisions.map(d => d.estimated_probability)

        aggregateDecisions[key] = {
          bet: median(bets),
          estimated_probability: median(estimatedProbabilities)
        }
      }
    })
  })

  // Now we need to compute performance metrics for the aggregate model
  // For now, we'll create a synthetic leaderboard entry
  // The backend would normally compute these, but we're doing it in the frontend

  // Get performance data for the aggregate decisions
  const aggregatePerformance = await computeAggregatePerformance(aggregateDecisions, leaderboard)

  // Create the aggregate leaderboard entry
  const aggregateEntry: LeaderboardEntry = {
    model_id: AGGREGATE_MODEL_ID,
    model_name: AGGREGATE_MODEL_NAME,
    final_profit: aggregatePerformance.final_profit,
    trades_count: aggregatePerformance.trades_count,
    lastUpdated: new Date().toISOString(),
    trend: 'stable' as const,
    compound_profit_history: aggregatePerformance.compound_profit_history,
    cumulative_profit_history: aggregatePerformance.cumulative_profit_history,
    trades_dates: aggregatePerformance.trades_dates,
    final_brier_score: aggregatePerformance.final_brier_score,
    average_returns: aggregatePerformance.average_returns,
    daily_returns: aggregatePerformance.daily_returns,
    sharpe: aggregatePerformance.sharpe
  }

  return aggregateEntry
}

/**
 * Computes performance metrics for aggregate decisions by averaging the four base models
 * This is a simplified approach - computing actual PnL would require full market data
 */
async function computeAggregatePerformance(
  aggregateDecisions: { [key: string]: { bet: number; estimated_probability: number } },
  leaderboard: LeaderboardEntry[]
) {
  // Get the 4 base model entries
  const baseModels = leaderboard.filter(entry =>
    REQUIRED_MODELS.includes(entry.model_id)
  )

  if (baseModels.length !== REQUIRED_MODELS.length) {
    throw new Error('Not all required models found in leaderboard')
  }

  // Extract unique dates for trades_dates
  const dates = new Set<string>()
  Object.keys(aggregateDecisions).forEach(key => {
    const [, targetDate] = key.split('|')
    dates.add(targetDate)
  })

  const trades_dates = Array.from(dates).sort()

  // Average the performance metrics across the 4 models
  const avgFinalProfit = baseModels.reduce((sum, m) => sum + m.final_profit, 0) / baseModels.length
  const avgBrierScore = baseModels.reduce((sum, m) => sum + m.final_brier_score, 0) / baseModels.length

  // Average returns
  const avgReturns = {
    one_day_return: baseModels.reduce((sum, m) => sum + m.average_returns.one_day_return, 0) / baseModels.length,
    two_day_return: baseModels.reduce((sum, m) => sum + m.average_returns.two_day_return, 0) / baseModels.length,
    seven_day_return: baseModels.reduce((sum, m) => sum + m.average_returns.seven_day_return, 0) / baseModels.length,
    all_time_return: baseModels.reduce((sum, m) => sum + m.average_returns.all_time_return, 0) / baseModels.length
  }

  // Average Sharpe ratios
  const avgSharpe = {
    one_day_annualized_sharpe: baseModels.reduce((sum, m) => sum + m.sharpe.one_day_annualized_sharpe, 0) / baseModels.length,
    two_day_annualized_sharpe: baseModels.reduce((sum, m) => sum + m.sharpe.two_day_annualized_sharpe, 0) / baseModels.length,
    seven_day_annualized_sharpe: baseModels.reduce((sum, m) => sum + m.sharpe.seven_day_annualized_sharpe, 0) / baseModels.length
  }

  // For profit history, we'll average the values at each date point
  const compound_profit_history = averageTimeseriesPoints(
    baseModels.map(m => m.compound_profit_history)
  )

  const cumulative_profit_history = averageTimeseriesPoints(
    baseModels.map(m => m.cumulative_profit_history)
  )

  const daily_returns = averageTimeseriesPoints(
    baseModels.map(m => m.daily_returns)
  )

  return {
    final_profit: avgFinalProfit,
    trades_count: Object.keys(aggregateDecisions).length,
    compound_profit_history,
    cumulative_profit_history,
    trades_dates,
    final_brier_score: avgBrierScore,
    average_returns: avgReturns,
    daily_returns,
    sharpe: avgSharpe
  }
}

/**
 * Averages multiple timeseries by taking the mean value at each date
 */
function averageTimeseriesPoints(seriesList: TimeseriesPoint[][]): TimeseriesPoint[] {
  // Filter out null/undefined series
  const validSeries = seriesList.filter(series => series !== null && series !== undefined && Array.isArray(series))

  if (validSeries.length === 0) {
    return []
  }

  // Collect all unique dates
  const dateSet = new Set<string>()
  validSeries.forEach(series => {
    if (Array.isArray(series)) {
      series.forEach(point => {
        if (point && point.date) {
          dateSet.add(point.date)
        }
      })
    }
  })

  const dates = Array.from(dateSet).sort()

  // For each date, average the values from all series that have data for that date
  return dates.map(date => {
    const values: number[] = []
    validSeries.forEach(series => {
      const point = series.find(p => p && p.date === date)
      if (point !== undefined && typeof point.value === 'number') {
        values.push(point.value)
      }
    })

    const avgValue = values.length > 0 ? values.reduce((sum, v) => sum + v, 0) / values.length : 0

    return { date, value: avgValue }
  })
}

/**
 * Checks if the aggregate model should be included
 */
export function shouldIncludeAggregate(leaderboard: LeaderboardEntry[]): boolean {
  const requiredModelEntries = leaderboard.filter(entry =>
    REQUIRED_MODELS.includes(entry.model_id)
  )

  return requiredModelEntries.length === REQUIRED_MODELS.length
}
