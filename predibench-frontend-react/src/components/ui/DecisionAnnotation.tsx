import { useEffect, useMemo, useState } from 'react'
import type { ModelInvestmentDecision } from '../../api'
import { calculateDecisionReturns, type DecisionAnalysis } from '../../utils/decisionAnalysis'
import { ProfitDisplay } from './profit-display'

interface DecisionAnnotationProps {
  decision: ModelInvestmentDecision
  nextDecision?: ModelInvestmentDecision
  allDecisions: ModelInvestmentDecision[]
  /** Cumulative PnL data to calculate period profit */
  cumulativeData: { x: string; y: number }[]
}

export function DecisionAnnotation({ decision, nextDecision, cumulativeData }: DecisionAnnotationProps) {
  const [analysis, setAnalysis] = useState<DecisionAnalysis | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window !== 'undefined') return window.innerWidth <= 768
    return false
  })

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    let cancelled = false

    const calculateReturns = async () => {
      try {
        setIsLoading(true)
        const result = await calculateDecisionReturns(decision, nextDecision)
        if (!cancelled) {
          setAnalysis(result)
        }
      } catch (error) {
        console.error('Failed to calculate decision returns:', error)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    calculateReturns()
    return () => { cancelled = true }
  }, [decision, nextDecision])

  const totalBets = decision.event_investment_decisions.reduce((total, eventDecision) => {
    return total + eventDecision.market_investment_decisions.filter(md => md.decision.bet !== 0).length
  }, 0)

  const formattedStartDate = new Date(decision.target_date).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric'
  })

  const formattedStartDateTime = new Date(decision.decision_datetime).toLocaleString('en-US', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'UTC',
    timeZoneName: 'short'
  })

  const formattedEndDate = nextDecision ? new Date(nextDecision.target_date).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric'
  }) : null

  // Calculate cumulative profit for this period
  const periodProfitChange = useMemo(() => {
    if (!cumulativeData || cumulativeData.length === 0) return 0

    const startPoint = cumulativeData.find(point => point.x === decision.target_date)
    const endPoint = nextDecision
      ? cumulativeData.find(point => point.x === nextDecision.target_date)
      : cumulativeData[cumulativeData.length - 1] // Use last point if no next decision

    if (startPoint && endPoint) {
      return endPoint.y - startPoint.y
    }

    return 0
  }, [cumulativeData, decision.target_date, nextDecision])

  return (
    <div>
      {/* Header with period dates and profit change */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        paddingBottom: '8px',
        borderBottom: '1px solid hsl(var(--border))'
      }}>
        <div>
          <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '2px' }}>
            {formattedStartDate}{formattedEndDate && ` → ${formattedEndDate}`}
          </div>
          <div style={{ fontSize: '11px', color: 'hsl(var(--muted-foreground))' }}>
            {totalBets} bets taken at {formattedStartDateTime}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: '700', fontSize: '14px' }}>
            <ProfitDisplay
              value={periodProfitChange}
              formatValue={(v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`}
            />
          </div>
          <div style={{ fontSize: '10px', color: 'hsl(var(--muted-foreground))' }}>
            Period Portfolio Increase
          </div>
        </div>
      </div>

      {/* Simplified event list */}
      {isLoading ? (
        <div style={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))', fontStyle: 'italic' }}>
          Calculating returns...
        </div>
      ) : analysis ? (
        <div style={{ fontSize: '12px' }}>
          {(isMobile ? analysis.topDrivers.slice(0, 3) : analysis.topDrivers).map((driver, idx) => {
            const hasNoBets = driver.betAmount === 0
            return (
              <div key={idx} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '6px',
                padding: '4px 0',
                opacity: hasNoBets ? 0.5 : 1
              }}>
                <div style={{
                  fontWeight: '500',
                  flex: 1,
                  color: hasNoBets ? 'hsl(var(--muted-foreground))' : 'inherit'
                }}>
                  {driver.eventTitle}
                </div>
                <div style={{ textAlign: 'right', fontWeight: '600', fontSize: '12px' }}>
                  {hasNoBets ? (
                    <span style={{ color: 'hsl(var(--muted-foreground))', fontStyle: 'italic' }}>
                      No bets
                    </span>
                  ) : (
                    <ProfitDisplay
                      value={driver.returnAmount}
                      formatValue={(v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))' }}>
          No return data available
        </div>
      )}
    </div>
  )
}
