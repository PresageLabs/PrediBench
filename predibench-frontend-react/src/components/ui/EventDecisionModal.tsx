import { X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { EventInvestmentDecision } from '../../api'
import { apiService } from '../../api'
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
  const [realizedReturns, setRealizedReturns] = useState<Record<string, number>>({})
  const [totalEventPnL, setTotalEventPnL] = useState<number>(0)
  const [positionEndDate, setPositionEndDate] = useState<string | null>(null)
  const [agentLogs, setAgentLogs] = useState<any[] | null>(null)

  const headerTitle = useMemo(() => {
    const evt = eventTitle || eventDecision.event_title
    return { evt, modelName }
  }, [eventTitle, eventDecision.event_title, modelName])

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

  // Fetch full result data for agent logs
  useEffect(() => {
    let cancelled = false
    const loadFullResult = async () => {
      if (!modelId || !isOpen) return
      
      try {
        const result = await apiService.getFullResultByModelAndEvent(modelId, eventDecision.event_id, decisionDate)
        if (cancelled) return
        
        if (result?.full_result_text) {
          try {
            const parsed = JSON.parse(result.full_result_text)
            setAgentLogs(Array.isArray(parsed) ? parsed : [parsed])
          } catch (e) {
            console.error('Failed to parse full_result_text as JSON:', e)
            setAgentLogs(null)
          }
        } else {
          setAgentLogs(null)
        }
      } catch (e) {
        console.error('Failed to load full result:', e)
        if (!cancelled) {
          setAgentLogs(null)
        }
      }
    }
    
    loadFullResult()
    return () => { cancelled = true }
  }, [modelId, eventDecision.event_id, decisionDate, isOpen])

  useEffect(() => {
    let cancelled = false
    const loadPricesAndReturns = async () => {
      try {
        const event = await apiService.getEventDetails(eventDecision.event_id)

        const prices: Record<string, { date: string; price: number }[]> = {}
        const names: Record<string, string> = {}
        const returns: Record<string, number> = {}
        let totalPnL = 0

        const marketIds = new Set(eventDecision.market_investment_decisions.map(md => md.market_id))

        event.markets.forEach(m => {
          if (marketIds.has(m.id)) {
            names[m.id] = m.question
            if (m.prices) {
              // All prices from decision date onwards
              prices[m.id] = m.prices
                .filter(p => p.date >= decisionDate)
                .map(p => ({ date: p.date, price: p.value }))

              // Calculate realized returns if we have an end date
              if (positionEndDate && m.prices.length > 0) {
                const startPrice = m.prices.find(p => p.date >= decisionDate)?.value || 0
                const endPrice = m.prices
                  .filter(p => p.date <= positionEndDate)
                  .sort((a, b) => b.date.localeCompare(a.date))[0]?.value || startPrice

                const marketDecision = eventDecision.market_investment_decisions
                  .find(md => md.market_id === m.id)

                if (marketDecision) {
                  const betAmount = marketDecision.model_decision.bet
                  const priceChange = endPrice - startPrice
                  const realizedReturn = betAmount * priceChange
                  returns[m.id] = realizedReturn
                  totalPnL += realizedReturn
                }
              }
            }
          }
        })

        if (!cancelled) {
          setPopupMarketNames(names)
          setPopupPrices(prices)
          setRealizedReturns(returns)
          setTotalEventPnL(totalPnL)
        }
      } catch (e) {
        console.error('Failed to load event prices and returns', e)
      }
    }
    if (isOpen) loadPricesAndReturns()
    return () => { cancelled = true }
  }, [isOpen, eventDecision, decisionDate, positionEndDate])

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
                  <a href={`/models?selected=${encodeURIComponent(modelId)}`} className="hover:underline">
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
                    <th className="text-right py-2 px-3">Bet ($)</th>
                    <th className="text-right py-2 px-3">Odds</th>
                    <th className="text-right py-2 px-3">Confidence</th>
                    {positionEndDate && <th className="text-right py-2 px-3">Realized Returns</th>}
                  </tr>
                </thead>
                <tbody>
                  {eventDecision.market_investment_decisions.map((md, idx) => (
                    <tr key={idx} className="border-b border-border/50">
                      <td className="py-2 px-3">{md.market_question || `Market ${md.market_id}`}</td>
                      <td className="py-2 px-3 text-right">{md.model_decision.bet < 0 ? `-$${Math.abs(md.model_decision.bet).toFixed(2)}` : `$${md.model_decision.bet.toFixed(2)}`}</td>
                      <td className="py-2 px-3 text-right">{(md.model_decision.odds * 100).toFixed(1)}%</td>
                      <td className="py-2 px-3 text-right">{md.model_decision.confidence}/10</td>
                      {positionEndDate && (
                        <td className="py-2 px-3 text-right">
                          {realizedReturns[md.market_id] !== undefined ? (
                            <ProfitDisplay value={realizedReturns[md.market_id]} />
                          ) : (
                            <span className="text-muted-foreground">N/A</span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}

                  {/* Unallocated capital row */}
                  <tr className="border-b border-border/50 bg-muted/10">
                    <td className="py-2 px-3 italic text-muted-foreground">Unallocated capital</td>
                    <td className="py-2 px-3 text-right">${eventDecision.unallocated_capital.toFixed(2)}</td>
                    <td className="py-2 px-3"></td>
                    <td className="py-2 px-3"></td>
                    {positionEndDate && <td className="py-2 px-3"></td>}
                  </tr>

                  {/* Overall returns row */}
                  {positionEndDate && (
                    <tr className="border-t-2 border-border bg-muted/20 font-medium">
                      <td className="py-3 px-3" colSpan={4}>Overall returns</td>
                      <td className="py-3 px-3 text-right">
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
                  )}
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
                      ▸ {md.model_decision.rationale}
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
              {Object.keys(popupPrices).length === 0 ? (
                <div className="h-full bg-muted/10 rounded flex items-center justify-center text-sm text-muted-foreground">
                  Loading prices or no price data.
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

          {/* Agent full logs */}
          {agentLogs && agentLogs.length > 0 && (
            <div>
              <h4 className="font-medium mb-4">Agent full logs</h4>
              <div className="space-y-4">
                {agentLogs.map((log, index) => (
                  <div key={index} className="bg-muted/10 p-4 rounded-lg border">
                    <div className="overflow-x-auto">
                      <pre className="text-xs text-foreground whitespace-pre-wrap font-mono">
                        {typeof log === 'string' ? log : JSON.stringify(log, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
