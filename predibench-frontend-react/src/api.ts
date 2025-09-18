const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api'

export interface DecisionReturns {
  one_day_return: number
  two_day_return: number
  seven_day_return: number
  all_time_return: number
}

export interface DecisionBrier {
  one_day_brier: number
  two_day_brier: number
  seven_day_brier: number
  all_time_brier: number
}

export interface DecisionSharpe {
  one_day_sharpe: number
  two_day_sharpe: number
  seven_day_sharpe: number
  all_time_sharpe: number
}

export interface LeaderboardEntry {
  model_id: string
  model_name: string
  final_profit: number
  trades_count: number
  lastUpdated: string
  trend: 'up' | 'down' | 'stable'
  compound_profit_history: { date: string; value: number }[]
  cumulative_profit_history: { date: string; value: number }[]
  trades_dates: string[]
  final_brier_score: number
  average_returns: DecisionReturns
  sharpe: DecisionSharpe
  brier: DecisionBrier
}

export interface TimeseriesPoint {
  date: string
  value: number
}

export interface MarketBackend {
  id: string
  question: string
  slug: string
  description: string
  prices?: TimeseriesPoint[]
  outcomes: MarketOutcome[]
}

export interface MarketData {
  market_id: string
  question: string
  prices: { date: string; price: number }[]
  positions: { date: string; position: number }[]
  pnl_data: { date: string; pnl: number }[]
}

export interface ModelMarketDetails {
  [marketId: string]: MarketData
}

export interface Market {
  id: string
  question: string
  slug: string
  description: string
  outcomes: MarketOutcome[]
}

export interface MarketOutcome {
  name: string
  price: number
}

export interface Event {
  id: string
  slug: string
  title: string
  tags: string[] | null
  description: string | null
  start_datetime: string | null
  end_datetime: string | null
  creation_datetime: string
  volume: number | null
  volume24hr: number | null
  volume1wk: number | null
  volume1mo: number | null
  volume1yr: number | null
  liquidity: number | null
  markets: MarketBackend[]
}

export interface ModelInvestmentDecision {
  model_id: string
  target_date: string
  decision_datetime: string
  event_investment_decisions: EventInvestmentDecision[]
  // Backend-computed cumulative net gains for the whole model between this decision and the next
  // Values are net gains relative to 1.0 starting portfolio for the decision period
  net_gains_until_next_decision: TimeseriesPoint[]
}

export interface EventInvestmentDecision {
  event_id: string
  event_title: string
  event_description: string | null
  market_investment_decisions: MarketInvestmentDecision[]
  unallocated_capital: number
  // Backend-computed cumulative PnL time series for this event since the decision date
  net_gains_until_next_decision: TimeseriesPoint[]
  sources_google: string[] | null
  sources_visit_webpage: string[] | null
}

export interface MarketInvestmentDecision {
  market_id: string
  decision: SingleInvestmentDecision
  market_question: string | null
  // Backend-computed gains for this market since the decision date (optional)
  net_gains_at_decision_end: number | null
  // Backend-computed pair: [current_price, estimated_odds] (optional)
  brier_score_pair_current: [number, number] | null
}

export interface SingleInvestmentDecision {
  rationale: string
  estimated_probability: number
  bet: number
  confidence: number
}

export interface ModelPerformance {
  model_name: string
  model_id: string
  final_profit: number
  final_brier_score: number
  trades_count: number
  trades_dates: string[]
  brier_scores: TimeseriesPoint[]
  event_brier_scores: EventBrierScore[]
  market_brier_scores: MarketBrierScore[]
  compound_profit_history: TimeseriesPoint[]
  pnl_per_event_decision: { [eventId: string]: EventPnlBackend }
}

export interface EventBrierScore {
  event_id: string
  brier_score: TimeseriesPoint[]
}

export interface MarketBrierScore {
  market_id: string
  brier_score: TimeseriesPoint[]
}

export interface EventPnlBackend {
  event_id: string
  pnl: TimeseriesPoint[]
}

export interface MarketPnlBackend {
  market_id: string
  pnl: TimeseriesPoint[]
}

export interface FullModelResult {
  model_id: string
  event_id: string
  target_date: string
  full_result_listdict: unknown[] | unknown
}

class ApiService {
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 30000): Promise<Response> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      return response
    } catch (error) {
      clearTimeout(timeoutId)
      throw error
    }
  }

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/leaderboard`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEvents(params?: {
    search?: string
    sort_by?: 'volume' | 'date'
    order?: 'desc' | 'asc'
    limit?: number
  }): Promise<Event[]> {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.append('search', params.search)
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.order) searchParams.append('order', params.order)
    if (params?.limit) searchParams.append('limit', params.limit.toString())

    const url = `${API_BASE_URL}/events${searchParams.toString() ? `?${searchParams.toString()}` : ''}`
    const response = await this.fetchWithTimeout(url)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getPredictionDates(): Promise<string[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/prediction_dates`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getModelResults(): Promise<ModelInvestmentDecision[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model_results`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getModelResultsById(modelId: string): Promise<ModelInvestmentDecision[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model_results/by_id?model_id=${encodeURIComponent(modelId)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getModelResultsByDate(predictionDate: string): Promise<ModelInvestmentDecision[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model_results/by_date?prediction_date=${encodeURIComponent(predictionDate)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getModelResultsByIdAndDate(modelId: string, predictionDate: string): Promise<ModelInvestmentDecision> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model_results/by_id_and_date?model_id=${encodeURIComponent(modelId)}&prediction_date=${encodeURIComponent(predictionDate)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getModelResultsByEvent(eventId: string): Promise<ModelInvestmentDecision[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/model_results/by_event?event_id=${encodeURIComponent(eventId)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getPerformance(): Promise<ModelPerformance[]> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/performance`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getPerformanceByModel(modelId: string): Promise<ModelPerformance> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/performance/by_model?model_id=${encodeURIComponent(modelId)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getEventDetails(eventId: string): Promise<Event> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/events/by_id?event_id=${encodeURIComponent(eventId)}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  }

  async getFullDecisionByModelAndEvent(modelId: string, eventId: string, targetDate: string): Promise<FullModelResult | null> {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/decision_details/by_model_and_event?model_id=${encodeURIComponent(modelId)}&event_id=${encodeURIComponent(eventId)}&target_date=${encodeURIComponent(targetDate)}`)
    if (response.status === 404) {
      console.log('Full result not found', { modelId, eventId, targetDate })
      return null
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    // Do not rely on response.text() logging here; read JSON body
    const data = await response.json()
    return data
  }
}

export const apiService = new ApiService()
