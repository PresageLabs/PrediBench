import { ExternalLink } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Event, LeaderboardEntry, ModelInvestmentDecision } from '../api'
import { apiService } from '../api'
import { useAnalytics } from '../hooks/useAnalytics'
import { encodeSlashes, formatVolume } from '../lib/utils'
import { getChartColor } from './ui/chart-colors'
import { EventDecisionThumbnail } from './ui/EventDecisionThumbnail'
import { VisxLineChart } from './ui/visx-line-chart'

interface EventDetailProps {
  event: Event
  leaderboard: LeaderboardEntry[]
}

interface PriceData {
  date: string
  price: number
  marketId?: string
  marketName?: string
}



interface MarketInvestmentDecision {
  market_id: string
  model_name: string
  bet: number
  estimated_probability: number
  rationale: string
}

export function EventDetail({ event }: EventDetailProps) {
  const navigate = useNavigate()
  const [marketPricesData, setMarketPricesData] = useState<{ [marketId: string]: PriceData[] }>({})
  const { trackEvent, trackUserAction } = useAnalytics()
  const [loading, setLoading] = useState(false)
  const [latestDecisionDate, setLatestDecisionDate] = useState<string | null>(null)
  const [modelIdToName, setModelIdToName] = useState<Record<string, string>>({})
  const [eventModelDecisions, setEventModelDecisions] = useState<ModelInvestmentDecision[]>([])

  // Configuration for market filtering
  const MAX_VISIBLE_MARKETS = 8
  const PRICE_THRESHOLD = 0.01

  // Function to convert URLs in text to clickable links
  const linkify = (text: string | null | undefined) => {
    if (!text) return null

    const urlRegex = /(https?:\/\/[^\s]+)/g

    return text.split(urlRegex).map((part, index) => {
      // Check if this part is a URL by testing against a fresh regex
      if (/^https?:\/\//.test(part)) {
        // Remove trailing punctuation from the URL
        const cleanUrl = part.replace(/[.,;:!?)\]]+$/, '')
        const trailingPunct = part.slice(cleanUrl.length)

        return (
          <span key={index}>
            <a
              href={cleanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              {cleanUrl}
            </a>
            {trailingPunct}
          </span>
        )
      }
      return part
    })
  }

  const loadEventDetails = async (eventId: string) => {
    setLoading(true)
    try {
      // Get market investment decisions by event
      const modelResultsByEvent = await apiService.getModelResultsByEvent(eventId)

      // Extract market prices from event.markets
      // Filter to last 2 months only to reduce frontend load
      const twoMonthsAgo = new Date()
      twoMonthsAgo.setMonth(twoMonthsAgo.getMonth() - 2)

      const transformedPrices: { [marketId: string]: PriceData[] } = {}
      event.markets.forEach(market => {
        if (market.prices) {
          const filteredPrices = market.prices.filter(pricePoint => {
            try {
              const priceDate = new Date(pricePoint.date)
              return priceDate >= twoMonthsAgo
            } catch {
              // If date parsing fails, include the price point to be safe
              return true
            }
          })

          transformedPrices[market.id] = filteredPrices.map(pricePoint => ({
            date: pricePoint.date,
            price: pricePoint.value,
            marketId: market.id,
            marketName: market.question
          }))
        }
      })

      // Transform investment decisions to match the component's expected format (for prior table; no longer displayed)
      const transformedDecisions: MarketInvestmentDecision[] = []
      let maxDate: string | null = null
      modelResultsByEvent.forEach(modelResult => {
        modelResult.event_investment_decisions.forEach(eventDecision => {
          if (eventDecision.event_id === eventId) {
            // use the top-level decision target_date as the model's decision date
            if (modelResult.target_date) {
              if (!maxDate || modelResult.target_date > maxDate) maxDate = modelResult.target_date
            }
            eventDecision.market_investment_decisions.forEach(marketDecision => {
              transformedDecisions.push({
                market_id: marketDecision.market_id,
                model_name: modelResult.model_id, // keep id here; we map to pretty name for display
                bet: marketDecision.decision.bet,
                estimated_probability: marketDecision.decision.estimated_probability,
                rationale: marketDecision.decision.rationale
              })
            })
          }
        })
      })

      setMarketPricesData(transformedPrices)
      setEventModelDecisions(modelResultsByEvent)
      setLatestDecisionDate(maxDate)
    } catch (error) {
      console.error('Error loading event details:', error)
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (event) {
      loadEventDetails(event.id)
      trackEvent('event_view', {
        event_id: event.id,
        event_title: event.title
      })
    }
  }, [event, trackEvent])

  // Build a map of model_id -> pretty model name using performance endpoint
  useEffect(() => {
    let cancelled = false
    apiService.getPerformance()
      .then(perfs => {
        if (cancelled) return
        const map: Record<string, string> = {}
        perfs.forEach(p => {
          map[p.model_id] = p.model_name
        })
        setModelIdToName(map)
      })
      .catch(console.error)
    return () => { cancelled = true }
  }, [])

  // Prepare latest decision per model for this event
  const latestByModel = useMemo(() => {
    const byModel: Record<string, ModelInvestmentDecision | undefined> = {}
    eventModelDecisions.forEach(dec => {
      const hasEvent = dec.event_investment_decisions.some(ed => ed.event_id === event.id)
      if (!hasEvent) return
      const current = byModel[dec.model_id]
      if (!current || dec.target_date > current.target_date) {
        byModel[dec.model_id] = dec
      }
    })
    return byModel
  }, [eventModelDecisions, event.id])

  const uniqueModelIds = useMemo(() => Object.keys(latestByModel), [latestByModel])

  // Filter markets: show all if under MAX_VISIBLE_MARKETS, else show top MAX_VISIBLE_MARKETS + any additional above threshold
  const visibleMarkets = useMemo(() => {
    if (!event?.markets) return []

    // Add max value to each market for sorting
    const marketsWithMaxValue = event.markets.map((market) => {
      const marketData = marketPricesData[market.id] || []
      const maxValue = marketData.length > 0 ? Math.max(...marketData.map(point => point.price)) : 0
      return { market, maxValue }
    })

    // If we have MAX_VISIBLE_MARKETS or fewer markets, show all
    if (marketsWithMaxValue.length <= MAX_VISIBLE_MARKETS) {
      return marketsWithMaxValue.map(({ market }) => market)
    }

    marketsWithMaxValue.sort((a, b) => b.maxValue - a.maxValue)

    const topMarkets = marketsWithMaxValue.slice(0, MAX_VISIBLE_MARKETS)

    const additionalMarkets = marketsWithMaxValue.slice(MAX_VISIBLE_MARKETS).filter(({ maxValue }) => maxValue >= PRICE_THRESHOLD)

    const selectedMarkets = [...topMarkets, ...additionalMarkets]

    return selectedMarkets.map(({ market }) => market)
  }, [event?.markets, marketPricesData])
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <a
          href="/events"
          className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to events
        </a>
        <a
          href={`https://polymarket.com/event/${event.slug}`}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => trackUserAction('external_link_click', 'engagement', 'polymarket')}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          Visit on Polymarket
          <ExternalLink className="h-4 w-4 ml-2" />
        </a>
      </div>

      <div>
        {/* Title */}
        <div className="mb-4">
          <h1 className="text-4xl font-bold mb-4">{event.title}</h1>

          {/* Status indicators and info */}
          <div className="flex items-center space-x-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
              {event.end_datetime && new Date(event.end_datetime) > new Date() ? 'LIVE' : 'CLOSED'}
            </span>

            <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-blue-50 text-blue-900 border border-blue-200">
              <span className="font-medium">Volume:</span>
              <span className="ml-1">{formatVolume(event.volume)}</span>
            </div>

            <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-gray-50 text-gray-900 border border-gray-200">
              <span className="font-medium">Ends:</span>
              <span className="ml-1">{event.end_datetime ? new Date(event.end_datetime).toLocaleDateString('en-US') : 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Market Price Charts - Superposed */}
        <div>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                <div className="text-sm text-muted-foreground">Loading market data...</div>
              </div>
            </div>
          ) : (
            <div className="w-full">
              {/* Market Legend - only show markets that will be displayed in chart */}
              <div className="mb-4 flex flex-wrap gap-2">
                {visibleMarkets.map((market, index) => (
                  <div key={market.id} className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        backgroundColor: getChartColor(index)
                      }}
                    ></div>
                    <span className="text-sm text-muted-foreground">
                      {market.question.length > 50 ? market.question.substring(0, 47) + '...' : market.question}
                    </span>
                  </div>
                ))}
              </div>

              <div className="w-full h-96">
                <VisxLineChart
                  height={384}
                  margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                  yDomain={[0, 1]}
                  series={visibleMarkets.map((market, index) => ({
                    dataKey: `market_${market.id}`,
                    data: (marketPricesData[market.id] || []).map(point => ({
                      date: point.date,
                      value: point.price
                    })),
                    stroke: getChartColor(index),
                    name: market.question.length > 30 ? market.question.substring(0, 27) + '...' : market.question
                  }))}
                />
              </div>
            </div>
          )}
        </div>

        {/* Event Description */}
        <div className="mt-8 mb-8">
          <div className="text-muted-foreground text-base leading-relaxed">
            {linkify(event.description)}
          </div>
        </div>

        {/* Latest Model Predictions */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-4">
            Latest Predictions{latestDecisionDate ? ` (${new Date(latestDecisionDate).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })})` : ''}
          </h2>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-center">
                <div className="w-6 h-6 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                <div className="text-sm text-muted-foreground">Loading predictions...</div>
              </div>
            </div>
          ) : uniqueModelIds.length === 0 ? (
            <div className="text-sm text-muted-foreground">No predictions available.</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {uniqueModelIds.map(modelId => {
                const md = latestByModel[modelId]!
                const ed = md.event_investment_decisions.find(ed => ed.event_id === event.id)!
                const top = [...ed.market_investment_decisions].sort((a, b) => Math.abs(b.decision.bet) - Math.abs(a.decision.bet))[0]
                const topBet = top?.decision.bet ?? null
                const topQuestion = top?.market_question || 'Top market'

                return (
                  <EventDecisionThumbnail
                    key={modelId}
                    title={modelIdToName[modelId] || modelId}
                    topMarketName={topQuestion}
                    topBet={topBet}
                    decisionsCount={ed.market_investment_decisions.length}
                    onClick={() => {
                      // Only include source parameter to indicate navigation origin
                      const searchParams = new URLSearchParams({
                        source: 'event'
                      })
                      navigate(`/decision/${encodeSlashes(modelId)}/${event.id}/${md.target_date}?${searchParams.toString()}`)
                    }}
                  />
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
