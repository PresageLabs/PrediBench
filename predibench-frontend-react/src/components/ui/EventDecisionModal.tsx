import { X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { EventInvestmentDecision } from '../../api'
import { apiService } from '../../api'
import { encodeSlashes } from '../../lib/utils'
import { AgentLogsDisplay } from './AgentLogsDisplay'
import { getChartColor } from './chart-colors'
import { ProfitDisplay } from './profit-display'
import { VisxLineChart } from './visx-line-chart'

interface EventDecisionModalProps {
  isOpen: boolean
  onClose: () => void
  eventDecision: EventInvestmentDecision
  decisionDate: string
  decisionDatetime?: string
  /** Optional: model pretty name to show in header */
  modelName?: string
  /** Optional: model id for header link */
  modelId?: string
  /** Optional: event pretty name override (defaults to decision.event_title) */
  eventTitle?: string
  /** Optional: sorted decision dates for the same event and model to determine end date */
  decisionDatesForEvent?: string[]
}

export function EventDecisionModal({
  isOpen,
  onClose,
  eventDecision,
  decisionDate,
  decisionDatetime,
  modelName,
  modelId,
  eventTitle,
  decisionDatesForEvent = []
}: EventDecisionModalProps) {
  const [popupPrices, setPopupPrices] = useState<Record<string, { date: string; price: number }[]>>({})
  const [popupMarketNames, setPopupMarketNames] = useState<Record<string, string>>({})
  // Per-market realized returns (only when positionEndDate exists)
  const [realizedReturns, setRealizedReturns] = useState<Record<string, number>>({})
  // Event-level realized PnL (sum of per-market realized returns)
  const [totalEventPnL, setTotalEventPnL] = useState<number>(0)
  const [positionEndDate, setPositionEndDate] = useState<string | null>(null)
  const [pricesLoading, setPricesLoading] = useState<boolean>(false)
  const [agentLogs, setAgentLogs] = useState<unknown[] | unknown | null>(null)
  const [agentLogsLoading, setAgentLogsLoading] = useState<boolean>(false)

  // Only show agent logs for decisions strictly after this date (YYYY-MM-DD)
  const AGENT_LOGS_CUTOFF_DATE = '2025-09-09'
  const isDecisionAfterCutoff = useMemo(() => {
    // decisionDate format is YYYY-MM-DD, string compare works lexicographically
    return decisionDate > AGENT_LOGS_CUTOFF_DATE
  }, [decisionDate])

  const headerTitle = useMemo(() => {
    const evt = eventTitle || eventDecision.event_title
    return { evt, modelName }
  }, [eventTitle, eventDecision.event_title, modelName])

  // modelId prop must be the canonical model_id (caller ensures this)

  useEffect(() => {
    // Compute end date as the next date after decisionDate in the provided sequence
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
      if (!isOpen || !isDecisionAfterCutoff) return

      // Start loading and reset logs
      setAgentLogs(null)
      setAgentLogsLoading(true)
      try {
        const result = await apiService.getFullResultByModelAndEvent(modelId!, eventDecision.event_id, decisionDate);
        console.log('Loaded agent logs', result);
        if (cancelled) return
        if (!result) {
          throw new Error(`Full result missing for model=${modelId} event=${eventDecision.event_id} date=${decisionDate}`)
        }
        // For post-cutoff dates, backend returns the proper format (array or object) in full_result_listdict
        setAgentLogs(result.full_result_listdict)
        // Optional debug for development
        // console.debug('Loaded agent logs', { modelId, eventId: eventDecision.event_id, decisionDate, logsType: Array.isArray(result.full_result_listdict) ? 'array' : typeof result.full_result_listdict })
      } finally {
        if (!cancelled) setAgentLogsLoading(false)
      }
    }

    // Reset logs state when modal opens or dependencies change
    if (isOpen) {
      if (isDecisionAfterCutoff) {
        loadFullResult()
      } else {
        // Ensure we don't display any loading or logs for older decisions
        setAgentLogs(null)
        setAgentLogsLoading(false)
      }
    } else {
      // Modal closed: reset loading state
      setAgentLogsLoading(false)
    }
    return () => { cancelled = true }
  }, [modelId, eventDecision.event_id, decisionDate, isOpen, isDecisionAfterCutoff])

  // Load market prices and names for the chart (returns now come from backend field)
  useEffect(() => {
    let cancelled = false
    const loadPrices = async () => {
      if (!isOpen) return
      setPricesLoading(true)
      try {
        const event = await apiService.getEventDetails(eventDecision.event_id)
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
  }, [isOpen, eventDecision, decisionDate, positionEndDate])

  // Compute per-market returns from backend-provided net_gains_at_decision_end, and sum for overall
  useEffect(() => {
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

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-card rounded-xl border border-border max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            <a href={`/events/${eventDecision.event_id}`} className="hover:underline">
              {headerTitle.evt}
            </a>
            {headerTitle.modelName ? (
              <>
                {' '}
                — {' '}
                {modelId ? (
                  <a href={`/models?selected=${encodeSlashes(modelId)}`} className="hover:underline">
                    {headerTitle.modelName}
                  </a>
                ) : (
                  <span>{headerTitle.modelName}</span>
                )}
              </>
            ) : null}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-accent"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <div className="text-sm text-muted-foreground mb-4">
              Position taken on {formatLongDate(decisionDate)}{decisionDatetime ? ` at ${new Date(decisionDatetime).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'UTC', timeZoneName: 'short' })}` : ''}{positionEndDate ? `, ended on ${formatLongDate(positionEndDate)}` : ''}
            </div>

            <div className="overflow-x-auto bg-muted/10 rounded-lg p-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="text-left py-2 px-3">Market</th>
                    <th className="text-center py-2 px-3">Bet ($)</th>
                    <th className="text-center py-2 px-3">Estimated odds</th>
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
                      <td className="py-2 px-3 text-center">{(md.decision.odds * 100).toFixed(1)}%</td>
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
                    <td className="py-3 px-3" colSpan={4}>Overall returns</td>
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
          <div className="mb-8">
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
                    data: points.map(p => ({ x: p.date, y: p.price })),
                    stroke: getChartColor(index),
                    name: (popupMarketNames[marketId] || `Market ${marketId}`).substring(0, 30)
                  }))}
                />
              )}
            </div>
          </div>

          {/* Agent full logs (only for decisions after cutoff date) */}
          {isDecisionAfterCutoff && (
            <div>
              <h4 className="font-medium mb-4">Agent full logs</h4>
              {agentLogsLoading ? (
                <div className="text-sm text-muted-foreground">Loading agent logs…</div>
              ) : (
                <AgentLogsDisplay logs={agentLogs} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
