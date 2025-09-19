import { useEffect, useState } from 'react'
import type { ModelInvestmentDecision } from '../../api'
import { calculateDecisionReturns, type DecisionAnalysis } from '../../utils/decisionAnalysis'
import { ProfitDisplay } from './profit-display'

// Helper function to format dollar values consistently
const formatDollarValue = (value: number): string => {
  if (Math.abs(value) < 0.005) return '$0.00'
  return `${value >= 0 ? '+' : '-'}$${Math.abs(value).toFixed(2)}`
}

interface DecisionAnnotationProps {
  decision: ModelInvestmentDecision
  nextDecision?: ModelInvestmentDecision
  allDecisions: ModelInvestmentDecision[]
  /** Callback when an event is clicked */
  onEventClick?: (eventDecision: any, decisionDate: string, decisionDatetime: string) => void
}

export function DecisionAnnotation({ decision, nextDecision, onEventClick }: DecisionAnnotationProps) {
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
        const result = await calculateDecisionReturns(decision)
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
    return total + eventDecision.market_investment_decisions.length
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

  const handleEventClick = (eventId: string) => {
    const eventDecision = decision.event_investment_decisions.find(ed => ed.event_id === eventId)
    if (eventDecision && onEventClick) {
      onEventClick(eventDecision, decision.target_date, decision.decision_datetime)
    }
  }


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
            {formattedStartDateTime}: Bet on {decision.event_investment_decisions.length} events
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: '700', fontSize: '14px' }}>
            <ProfitDisplay
              value={analysis?.totalReturn ?? 0}
              formatValue={formatDollarValue}
            />
          </div>
          <div style={{ fontSize: '10px', color: 'hsl(var(--muted-foreground))' }}>
            Returns, in dollars (from ${decision.event_investment_decisions.length} invested)
          </div>
        </div>
      </div>

      {/* Per-market returns list (in dollars) */}
      {isLoading ? (
        <div style={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))', fontStyle: 'italic' }}>
          Calculating returns...
        </div>
      ) : analysis ? (
        <div style={{ fontSize: '12px' }}>
          {(() => {
            const limit = isMobile ? 3 : 5
            const items = analysis.topDrivers.slice(0, limit)
            return items.map((driver, idx) => {
              return (
                <div key={idx} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '6px',
                  padding: '4px 0',
                  opacity: 1
                }}>
                  <div
                    style={{
                      fontWeight: '500',
                      flex: 1,
                      color: 'inherit',
                      cursor: 'pointer',
                      textDecoration: 'underline',
                      transition: 'color 0.2s ease'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'hsl(var(--primary))' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'inherit' }}
                    onClick={() => handleEventClick(driver.eventId)}
                  >
                    {driver.eventTitle}
                  </div>
                  <div style={{ textAlign: 'right', fontWeight: '600', fontSize: '12px' }}>
                    <ProfitDisplay value={driver.returnAmount} formatValue={formatDollarValue} />
                  </div>
                </div>
              )
            })
          })()}
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))' }}>
          No return data available
        </div>
      )}
    </div>
  )
}
