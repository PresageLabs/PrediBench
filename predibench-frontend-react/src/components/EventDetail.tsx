import { ExternalLink } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { Event, LeaderboardEntry } from '../api'
import { getChartColor } from './ui/chart-colors'
import { VisxLineChart } from './ui/visx-line-chart'
import { useAnalytics } from '../hooks/useAnalytics'

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
  agent_name: string
  bet: number
  odds: number
  rationale: string
}

export function EventDetail({ event }: EventDetailProps) {
  const [marketPricesData, setMarketPricesData] = useState<{ [marketId: string]: PriceData[] }>({})
  const { trackEvent, trackUserAction } = useAnalytics()
  const [investmentDecisions, setInvestmentDecisions] = useState<MarketInvestmentDecision[]>([])
  const [loading, setLoading] = useState(false)

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
      const [marketPrices, investmentDecisions] = await Promise.all([
        fetch(`http://localhost:8080/api/event/${eventId}/market_prices`).then(r => r.json()),
        fetch(`http://localhost:8080/api/event/${eventId}/investment_decisions`).then(r => r.json())
      ])

      // Transform market prices data from {marketId: {date: price}} to {marketId: [{date, price}]}
      const transformedPrices: { [marketId: string]: PriceData[] } = {}
      Object.entries(marketPrices).forEach(([marketId, pricesByDate]) => {
        transformedPrices[marketId] = Object.entries(pricesByDate as Record<string, number>).map(([date, price]) => ({
          date,
          price,
          marketId
        }))
      })

      setMarketPricesData(transformedPrices)
      setInvestmentDecisions(investmentDecisions)
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
        event_title: event.title,
        event_status: event.status
      })
    }
  }, [event, trackEvent])
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => {
            trackUserAction('back_button_click', 'navigation', 'event_detail')
            window.history.back()
          }}
          className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to events
        </button>
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
              <span className="ml-1">{event.volume ? `$${(event.volume / 1000).toFixed(0)}K` : 'N/A'}</span>
            </div>

            <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-gray-50 text-gray-900 border border-gray-200">
              <span className="font-medium">Ends:</span>
              <span className="ml-1">{event.end_datetime ? new Date(event.end_datetime).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Market Price Charts - Superposed */}
        <div>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="w-full">
              {/* Market Legend */}
              <div className="mb-4 flex flex-wrap gap-2">
                {event?.markets?.map((market, index) => (
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
                  series={event?.markets?.map((market, index) => ({
                    dataKey: `market_${market.id}`,
                    data: (marketPricesData[market.id] || []).map(point => ({
                      x: point.date,
                      y: point.price
                    })),
                    stroke: getChartColor(index),
                    name: market.question.length > 30 ? market.question.substring(0, 27) + '...' : market.question
                  })) || []}
                />
              </div>
            </div>
          )}
        </div>

        {/* Event Description */}
        <div className="mt-8 mb-8">
          <h3 className="text-lg font-bold mb-4">Description</h3>
          <div className="text-muted-foreground text-base leading-relaxed">
            {linkify(event.description)}
          </div>
        </div>

        {/* Latest Model Predictions */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-6">Latest Predictions</h2>
          <p className="text-sm text-muted-foreground mb-4">Latest predictions from models</p>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground"></th>
                    {/* Create column headers for each unique model */}
                    {[...new Set(investmentDecisions.map(decision => decision.agent_name))].map(modelName => (
                      <th key={modelName} className="text-center py-3 px-4 text-sm font-medium text-muted-foreground">
                        {modelName}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Bet row */}
                  <tr className="border-b border-border bg-muted/50">
                    <td className="py-3 px-4 font-medium text-sm">Bet</td>
                    {[...new Set(investmentDecisions.map(decision => decision.agent_name))].map(modelName => {
                      const decision = investmentDecisions.find(d => d.agent_name === modelName)
                      return (
                        <td key={modelName} className="py-3 px-4 text-center">
                          {decision && (
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${decision.bet < 0
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                              }`}>
                              {decision.bet.toFixed(2)}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>

                  {/* Confidence row */}
                  <tr>
                    <td className="py-3 px-4 font-medium text-sm">Confidence</td>
                    {[...new Set(investmentDecisions.map(decision => decision.agent_name))].map(modelName => {
                      const decision = investmentDecisions.find(d => d.agent_name === modelName)
                      return (
                        <td key={modelName} className="py-3 px-4 text-center text-sm text-muted-foreground">
                          {decision && `${(decision.odds * 100).toFixed(0)}%`}
                        </td>
                      )
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}