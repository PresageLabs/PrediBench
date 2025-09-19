import Giscus from '@giscus/react'
import { ArrowLeft, ChevronDown, FileText, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import type { EventInvestmentDecision } from '../api'
import { apiService } from '../api'
import { useTheme } from '../contexts/ThemeContext'
import { decodeSlashes, encodeSlashes } from '../lib/utils'
import { AgentLogsDisplay } from './ui/AgentLogsDisplay'
import { getChartColor } from './ui/chart-colors'
import { ProfitDisplay } from './ui/profit-display'
import { VisxLineChart } from './ui/visx-line-chart'

interface EventDecisionDetailPageProps { }

export function EventDecisionDetailPage({ }: EventDecisionDetailPageProps) {
  const { modelId, eventId, decisionDate } = useParams<{
    modelId: string
    eventId: string
    decisionDate: string
  }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { theme } = useTheme()

  const [eventDecision, setEventDecision] = useState<EventInvestmentDecision | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // States from original modal
  const [popupPrices, setPopupPrices] = useState<Record<string, { date: string; price: number }[]>>({})
  const [popupMarketNames, setPopupMarketNames] = useState<Record<string, string>>({})
  const [realizedReturns, setRealizedReturns] = useState<Record<string, number>>({})
  const [totalEventPnL, setTotalEventPnL] = useState<number>(0)
  const [positionEndDate, setPositionEndDate] = useState<string | null>(null)
  const [pricesLoading, setPricesLoading] = useState<boolean>(false)
  const [agentLogs, setAgentLogs] = useState<unknown[] | unknown | null>(null)
  const [agentLogsLoading, setAgentLogsLoading] = useState<boolean>(false)
  const [agentLogsExpanded, setAgentLogsExpanded] = useState<boolean>(false)

  // Get navigation source from URL params
  const sourceType = searchParams.get('source') || 'event' // 'event' or 'model'
  const decisionDatetime = searchParams.get('decisionDatetime')
  const modelName = searchParams.get('modelName')
  const eventTitle = searchParams.get('eventTitle')
  const decisionDatesForEvent = searchParams.get('decisionDatesForEvent')?.split(',') || []

  // Only show agent logs for decisions strictly after this date (YYYY-MM-DD)
  const AGENT_LOGS_CUTOFF_DATE = '2025-09-09'
  const isDecisionAfterCutoff = useMemo(() => {
    return decisionDate ? decisionDate > AGENT_LOGS_CUTOFF_DATE : false
  }, [decisionDate])

  const headerTitle = useMemo(() => {
    const evt = eventTitle || eventDecision?.event_title || 'Event'
    return { evt, modelName }
  }, [eventTitle, eventDecision?.event_title, modelName])

  // Load event decision data
  useEffect(() => {
    let cancelled = false
    const loadEventDecision = async () => {
      if (!modelId || !eventId || !decisionDate) return

      setLoading(true)
      setError(null)
      try {
        const modelResult = await apiService.getModelResultsByIdAndDate(
          decodeSlashes(modelId || ''),
          decisionDate
        )

        if (cancelled) return

        const eventDecisionData = modelResult.event_investment_decisions.find(
          ed => ed.event_id === eventId
        )

        if (!eventDecisionData) {
          throw new Error('Event decision not found')
        }

        setEventDecision(eventDecisionData)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load event decision')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadEventDecision()
    return () => { cancelled = true }
  }, [modelId, eventId, decisionDate])

  // Compute end date as the next date after decisionDate in the provided sequence
  useEffect(() => {
    if (!decisionDatesForEvent || decisionDatesForEvent.length === 0) {
      setPositionEndDate(null)
      return
    }
    const sorted = [...decisionDatesForEvent].sort((a, b) => a.localeCompare(b))
    const idx = sorted.findIndex(d => d === decisionDate)
    if (idx >= 0 && idx < sorted.length - 1) {
      setPositionEndDate(sorted[idx + 1])
    } else {
      setPositionEndDate(null)
    }
  }, [decisionDatesForEvent, decisionDate])

  // Fetch full result data for agent logs (only for decisions after cutoff)
  useEffect(() => {
    let cancelled = false
    const loadFullResult = async () => {
      if (!eventDecision || !isDecisionAfterCutoff || !modelId || !eventId || !decisionDate) return

      setAgentLogs(null)
      setAgentLogsLoading(true)
      try {
        const result = await apiService.getFullDecisionByModelAndEvent(
          decodeURIComponent(modelId),
          eventId,
          decisionDate
        )
        if (cancelled) return
        if (!result) {
          throw new Error(`Full result missing for model=${modelId} event=${eventId} date=${decisionDate}`)
        }
        setAgentLogs(result.full_result_listdict)
      } catch (err) {
        console.error('Failed to load agent logs:', err)
      } finally {
        if (!cancelled) setAgentLogsLoading(false)
      }
    }

    if (eventDecision && isDecisionAfterCutoff) {
      loadFullResult()
    } else {
      setAgentLogs(null)
      setAgentLogsLoading(false)
    }
    return () => { cancelled = true }
  }, [modelId, eventId, decisionDate, eventDecision, isDecisionAfterCutoff])

  // Load market prices and names for the chart
  useEffect(() => {
    let cancelled = false
    const loadPrices = async () => {
      if (!eventDecision || !eventId || !decisionDate) return
      setPricesLoading(true)
      try {
        const event = await apiService.getEventDetails(eventId)
        const prices: Record<string, { date: string; price: number }[]> = {}
        const names: Record<string, string> = {}
        const marketIds = new Set(eventDecision.market_investment_decisions.map(md => md.market_id))
        event.markets.forEach(m => {
          if (marketIds.has(m.id)) {
            names[m.id] = m.question
            if (m.prices) {
              prices[m.id] = m.prices
                .filter(p => p.date >= decisionDate)
                .map(p => ({ date: p.date, price: p.value }))
            }
          }
        })
        if (!cancelled) {
          setPopupMarketNames(names)
          setPopupPrices(prices)
        }
      } catch (e) {
        console.error('Failed to load event prices and returns', e)
        if (!cancelled) {
          setPopupMarketNames({})
          setPopupPrices({})
        }
      } finally {
        if (!cancelled) setPricesLoading(false)
      }
    }
    loadPrices()
    return () => { cancelled = true }
  }, [eventDecision, eventId, decisionDate, positionEndDate])

  // Compute per-market returns from backend-provided net_gains_at_decision_end, and sum for overall
  useEffect(() => {
    if (!eventDecision) return

    const per: Record<string, number> = {}
    let total = 0
    eventDecision.market_investment_decisions.forEach(market_decision => {
      const g = market_decision.net_gains_at_decision_end
      if (g !== null && g !== undefined) {
        per[market_decision.market_id] = g
        total += g
      }
    })
    setRealizedReturns(per)
    setTotalEventPnL(total)
  }, [eventDecision])

  const formatLongDate = (dateStr: string) => {
    if (!dateStr) return ''
    const [y, m, d] = dateStr.split('-').map(Number)
    const dt = new Date(y, (m || 1) - 1, d || 1)
    return dt.toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const handleBack = () => {
    if (sourceType === 'model' && modelId) {
      navigate(`/models?selected=${encodeSlashes(decodeSlashes(modelId))}`)
    } else if (eventId) {
      navigate(`/events/${eventId}`)
    } else {
      navigate(-1)
    }
  }


  if (loading) {
    return (
      <div className="container mx-auto px-6 py-12">
        <div className="flex items-center justify-center min-h-96">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
            <span>Loading event decision...</span>
          </div>
        </div>
      </div>
    )
  }

  if (error || !eventDecision) {
    return (
      <div className="container mx-auto px-6 py-12">
        <button
          onClick={handleBack}
          className="mb-6 flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={16} />
          Back to {sourceType === 'model' ? `model: ${modelName || modelId}` : `event: ${eventTitle || eventId}`}
        </button>
        <div className="text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error Loading Event Decision</h2>
          <p className="text-muted-foreground">{error || 'Event decision not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-12 max-w-6xl">
      {/* Header with back button */}
      <div className="mb-6">
        <button
          onClick={handleBack}
          className="mb-4 flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={16} />
          Back to {sourceType === 'model' ? `model: ${modelName || modelId}` : `event: ${eventTitle || eventId}`}
        </button>

        <h1 className="text-2xl font-bold">
          <a href={`/events/${eventId}`} className="hover:underline">
            {headerTitle.evt}
          </a>
          {headerTitle.modelName ? (
            <>
              {' '}
              — {' '}
              {modelId ? (
                <a href={`/models?selected=${encodeSlashes(decodeSlashes(modelId))}`} className="hover:underline">
                  {headerTitle.modelName}
                </a>
              ) : (
                <span>{headerTitle.modelName}</span>
              )}
            </>
          ) : null}
        </h1>
      </div>

      <div className="space-y-8">
        <div>
          <div className="text-sm text-muted-foreground mb-4">
            Position taken on {formatLongDate(decisionDate || '')}{decisionDatetime ? ` at ${new Date(decisionDatetime).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'UTC', timeZoneName: 'short' })}` : ''}{positionEndDate ? `, ended on ${formatLongDate(positionEndDate)}` : ''}
          </div>

          <div className="overflow-x-auto bg-muted/10 rounded-lg p-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="text-left py-2 px-3">Market</th>
                  <th className="text-center py-2 px-3">Bet ($)</th>
                  <th className="text-center py-2 px-3">Estimated probability</th>
                  <th className="text-center py-2 px-3">Confidence level</th>
                  <th className="text-center py-2 px-3">Current returns</th>
                </tr>
              </thead>
              <tbody>
                {eventDecision.market_investment_decisions.map((md, idx) => (
                  <tr key={idx} className="border-b border-border/50">
                    <td className="py-2 px-3">{md.market_question || `Market ${md.market_id}`}</td>
                    <td className="py-2 px-3 text-center">
                      {md.decision.bet === 0 ? (
                        `${md.decision.bet.toFixed(2)}`
                      ) : (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${md.decision.bet > 0
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                          }`}>
                          {md.decision.bet > 0 ? '+' : '-'}{Math.abs(md.decision.bet).toFixed(2)}
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">{(md.decision.estimated_probability * 100).toFixed(1)}%</td>
                    <td className="py-2 px-3 text-center">{md.decision.confidence}/10</td>
                    <td className="py-2 px-3 text-center">
                      {realizedReturns[md.market_id] !== undefined ? (
                        <ProfitDisplay value={realizedReturns[md.market_id]} />
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}

                {/* Unallocated capital row */}
                <tr className="border-b border-border/50 bg-muted/10">
                  <td className="py-2 px-3 italic text-muted-foreground">Unallocated capital</td>
                  <td className="py-2 px-3 text-center">{eventDecision.unallocated_capital.toFixed(2)}</td>
                  <td className="py-2 px-3"></td>
                  <td className="py-2 px-3"></td>
                  <td className="py-2 px-3"></td>
                </tr>

                {/* Overall returns row */}
                <tr className="border-t-2 border-border bg-muted/20 font-medium">
                  <td className="py-3 px-3" colSpan={4}>Overall returns (from 1$ invested)</td>
                  <td className="py-3 px-3 text-center">
                    <ProfitDisplay
                      value={totalEventPnL}
                      formatValue={(v) => {
                        if (Math.abs(v) < 0.005) return '$0.00'
                        return `${v > 0 ? '+' : ''}$${v.toFixed(2)}`
                      }}
                      className="font-bold"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Consolidated rationales */}
          <div className="mt-3">
            <h4 className="font-medium mb-2">Decision rationale</h4>
            <div className="space-y-3">
              {eventDecision.market_investment_decisions.map((md, idx) => (
                <div key={idx} className="bg-muted/20 p-3 rounded-lg">
                  <div className="text-xs text-muted-foreground mb-2">
                    {md.market_question || `Market ${md.market_id}`}
                  </div>
                  <div className="text-sm text-foreground">
                    ▸ {md.decision.rationale}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Market price evolution since decision */}
        <div>
          <h4 className="font-medium mb-4">Market Prices Since Decision</h4>
          <div className="h-80">
            {pricesLoading ? (
              <div className="h-full bg-muted/10 rounded flex items-center justify-center text-sm text-muted-foreground">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                  <span>Loading market prices...</span>
                </div>
              </div>
            ) : Object.keys(popupPrices).length === 0 ? (
              <div className="h-full bg-muted/10 rounded flex items-center justify-center text-sm text-muted-foreground">
                No price data available for this event.
              </div>
            ) : (
              <VisxLineChart
                height={290}
                margin={{ left: 40, top: 20, bottom: 30, right: 20 }}
                yDomain={[0, 1]}
                series={Object.entries(popupPrices).map(([marketId, points], index) => ({
                  dataKey: `market_${marketId}`,
                  data: points.map(p => ({ date: p.date, value: p.price })),
                  stroke: getChartColor(index),
                  name: (popupMarketNames[marketId] || `Market ${marketId}`).substring(0, 30)
                }))}
              />
            )}
          </div>
        </div>

        {/* Sources used (only for decisions after cutoff date) */}
        {isDecisionAfterCutoff && (eventDecision.sources_google?.length || eventDecision.sources_visit_webpage?.length) && (
          <div>
            <h4 className="font-medium mb-4">Sources used:</h4>
            <div className="space-y-4">
              {eventDecision.sources_google && eventDecision.sources_google.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Search size={16} className="text-blue-700 dark:text-blue-300" />
                    <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                      {eventDecision.sources_google.length} sources seen in Google search
                    </span>
                  </div>
                  <div className="space-y-2 ml-6">
                    {eventDecision.sources_google.map((source, index) => {
                      const displayText = source.replace(/^https?:\/\/(www\.)?/, '')
                      return (
                        <a
                          key={index}
                          href={source}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline bg-gray-50 dark:bg-gray-800 p-2 rounded font-mono break-all"
                        >
                          {displayText}
                        </a>
                      )
                    })}
                  </div>
                </div>
              )}

              {eventDecision.sources_visit_webpage && eventDecision.sources_visit_webpage.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <FileText size={16} className="text-green-700 dark:text-green-300" />
                    <span className="text-sm font-medium text-green-700 dark:text-green-300">
                      {eventDecision.sources_visit_webpage.length} webpages visited
                    </span>
                  </div>
                  <div className="space-y-2 ml-6">
                    {eventDecision.sources_visit_webpage.map((source, index) => {
                      const displayText = source.replace(/^https?:\/\/(www\.)?/, '')
                      return (
                        <a
                          key={index}
                          href={source}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline bg-gray-50 dark:bg-gray-800 p-2 rounded font-mono break-all"
                        >
                          {displayText}
                        </a>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Agent full logs (only for decisions after cutoff date) */}
        {isDecisionAfterCutoff && (
          <div>
            <h4 className="font-medium mb-4">Agent full logs</h4>
            {agentLogsLoading ? (
              <div className="text-sm text-muted-foreground">Loading agent logs…</div>
            ) : (
              <div className="relative">
                <div
                  className={`overflow-hidden transition-all duration-300 ${agentLogsExpanded ? 'max-h-none' : 'max-h-[500px]'
                    }`}
                >
                  <AgentLogsDisplay logs={agentLogs} />
                </div>
                {!agentLogsExpanded && (
                  <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent flex items-end justify-center pb-2">
                    <button
                      onClick={() => setAgentLogsExpanded(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-background border border-border rounded-lg hover:bg-accent transition-colors text-sm"
                    >
                      <span>Show full logs</span>
                      <ChevronDown size={16} />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Giscus Comments */}
        <div>
          <h4 className="font-medium mb-4">Discussion</h4>
          <Giscus
            id="comments"
            repo="clairvoyance-tech/predibench"
            repoId="R_kgDOPTwANQ"
            category="Ideas"
            categoryId="DIC_kwDOPTwANc4Cvk2C"
            mapping="specific"
            term={`Decision: ${modelName}, ${decisionDate}, on ${eventId}`}
            strict="0"
            reactionsEnabled="0"
            emitMetadata="0"
            inputPosition="top"
            theme={theme === 'dark' ? 'dark_tritanopia' : 'light_tritanopia'}
            lang="en"
            loading="lazy"
          />
        </div>
      </div>
    </div>
  )
}