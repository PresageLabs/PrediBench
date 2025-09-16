import { useMemo } from 'react'
import type { ModelInvestmentDecision } from '../../api'

interface MarkerData {
  x: number
  y: number
  date: string
  decisions: ModelInvestmentDecision[]
}

interface MarkerAnnotationsProps {
  /** Scale functions from the chart */
  xScale: (date: Date) => number
  yScale: (value: number) => number
  
  /** Data for markers - cumulative PnL data points */
  cumulativeData: { date: string; value: number }[]
  
  /** Investment decisions data to show on hover */
  modelDecisions: ModelInvestmentDecision[]
}

export function MarkerAnnotations({
  xScale,
  yScale,
  cumulativeData,
  modelDecisions
}: MarkerAnnotationsProps) {
  
  // Create marker data by matching cumulative PnL points with decision dates
  const markerData = useMemo((): MarkerData[] => {
    const markers: MarkerData[] = []
    
    // Group decisions by target_date for efficient lookup
    const decisionsByDate = new Map<string, ModelInvestmentDecision[]>()
    modelDecisions.forEach(decision => {
      const existing = decisionsByDate.get(decision.target_date) || []
      decisionsByDate.set(decision.target_date, [...existing, decision])
    })
    
    // Find cumulative PnL points that have corresponding decisions
    cumulativeData.forEach(point => {
      const decisionsOnDate = decisionsByDate.get(point.date)
      if (decisionsOnDate && decisionsOnDate.length > 0) {
        const x = xScale(new Date(point.date))
        const y = yScale(point.value)

        // Only add marker if coordinates are valid
        if (Number.isFinite(x) && Number.isFinite(y)) {
          markers.push({
            x,
            y,
            date: point.date,
            decisions: decisionsOnDate
          })
        }
      }
    })
    
    return markers
  }, [cumulativeData, modelDecisions, xScale, yScale])

  return (
    <g>
      {/* Render grey markers at decision points */}
      {markerData.map((marker, index) => (
        <circle
          key={`decision-marker-${marker.date}-${index}`}
          cx={marker.x}
          cy={marker.y}
          r={4}
          fill="hsl(var(--muted-foreground))"
          stroke="white"
          strokeWidth={1}
          style={{
            opacity: 0.7,
            pointerEvents: 'none' // Let the main chart handle hover events
          }}
        />
      ))}
    </g>
  )
}