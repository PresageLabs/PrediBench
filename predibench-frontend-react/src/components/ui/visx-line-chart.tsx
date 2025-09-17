import { curveMonotoneX } from '@visx/curve'
import { scaleLinear, scaleTime } from '@visx/scale'
import { AnimatedLineSeries, Axis, GlyphSeries, Grid, Tooltip, XYChart } from '@visx/xychart'
import { extent } from 'd3-array'
import { format } from 'date-fns'
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled from 'styled-components'
import type { ModelInvestmentDecision } from '../../api'
import { MarkerAnnotations } from './MarkerAnnotations'

const tickLabelOffset = 2

interface DataPoint {
  date: string | Date
  value: number
  [key: string]: unknown
}

interface LineSeriesConfig {
  dataKey: string
  data: DataPoint[]
  stroke: string
  name?: string
}

interface VisxLineChartProps {
  height?: number
  margin?: { left: number; top: number; bottom: number; right: number }
  series: LineSeriesConfig[]
  xAccessor?: (d: DataPoint) => Date
  yAccessor?: (d: DataPoint) => number
  yDomain?: [number, number]
  xDomain?: [Date, Date]
  formatTooltipX?: (value: Date) => string
  showGrid?: boolean
  numTicks?: number
  /** Optional: Show decision point markers with hover annotations */
  showDecisionMarkers?: boolean
  /** Optional: Investment decisions data for markers (required if showDecisionMarkers is true) */
  modelDecisions?: ModelInvestmentDecision[]
  /** Optional: Custom annotations indexed by date string (YYYY-MM-DD) */
  additionalAnnotations?: Record<string, {
    content: React.ReactNode
    /** Function to calculate the next annotation date for area highlighting */
    getNextDate?: () => string | null
  }>
}

const defaultAccessors = {
  // Be tolerant to null/undefined values to support discontinuities.
  xAccessor: (d: DataPoint) => {
    if (!d || d.date == null) return new Date(NaN)
    const val = d.date
    const date = val instanceof Date ? val : new Date(val as string)
    return isNaN(date.getTime()) ? new Date(NaN) : date
  },
  yAccessor: (d: DataPoint) => {
    if (!d || d.value == null) return NaN
    const num = Number(d.value)
    return Number.isFinite(num) ? num : NaN
  }
}


export function VisxLineChart({
  height = 270,
  margin = { left: 60, top: 35, bottom: 38, right: 27 },
  series,
  xAccessor = defaultAccessors.xAccessor,
  yAccessor = defaultAccessors.yAccessor,
  yDomain,
  xDomain,
  formatTooltipX = (value: Date) => format(value, 'MMM d, yyyy'),
  showGrid = true,
  numTicks = 4,
  showDecisionMarkers = false,
  modelDecisions = [],
  additionalAnnotations = {}
}: VisxLineChartProps) {
  // Ensure minimum of 4 ticks for better readability
  const effectiveNumTicks = Math.max(numTicks, 4)
  const containerRef = useRef<HTMLDivElement>(null)

  const [containerWidth, setContainerWidth] = useState(800)
  const isAnnotated = Object.keys(additionalAnnotations).length > 0
  const isMobile = containerWidth <= 768
  const chartHeight = isMobile && isAnnotated ? Math.round(height * 0.67) : height

  // Safe wrappers to guard against bad data points provided by callers
  const safeXAccessor = useCallback(
    (d: DataPoint) => {
      try {
        const v = xAccessor(d)
        return v instanceof Date ? v : new Date(v as any)
      } catch {
        return new Date(NaN)
      }
    },
    [xAccessor]
  )

  const safeYAccessor = useCallback(
    (d: DataPoint) => {
      try {
        const v = yAccessor(d)
        const num = Number(v as any)
        return Number.isFinite(num) ? num : NaN
      } catch {
        return NaN
      }
    },
    [yAccessor]
  )

  // Update container width when component mounts/resizes
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const width = rect.width || containerRef.current.offsetWidth || containerRef.current.clientWidth
        // Ensure minimum width to prevent zero-width chart
        const finalWidth = Math.max(width, 400)
        setContainerWidth(finalWidth)
      }
    }

    // Try multiple times to catch when DOM is ready
    updateWidth()
    setTimeout(updateWidth, 0)
    setTimeout(updateWidth, 100)

    // Also listen for resize events
    const resizeObserver = new ResizeObserver(updateWidth)
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    return () => resizeObserver.disconnect()
  }, [])

  // Create scales for proper coordinate conversion
  const scales = useMemo(() => {
    const allData = series.flatMap(s => s.data).filter(d => d != null)
    if (allData.length === 0) return null

    const xExtent = xDomain || (extent(allData, safeXAccessor) as [Date, Date])

    let yExtent: [number, number]
    if (yDomain) {
      yExtent = yDomain
    } else {
      // Filter out NaN values and compute extent manually
      const validYValues = allData.map(safeYAccessor).filter(v => Number.isFinite(v))
      if (validYValues.length === 0) {
        yExtent = [0, 1] // fallback
      } else {
        const minY = Math.min(...validYValues)
        const maxY = Math.max(...validYValues)
        yExtent = [minY, maxY]
      }
    }

    const xScale = scaleTime({
      domain: xExtent,
      range: [margin.left, containerWidth - margin.right]
    })

    const yScale = scaleLinear({
      domain: yExtent,
      range: [chartHeight - margin.bottom, margin.top]
    })

    return { xScale, yScale, yDomain: yExtent }
  }, [series, safeXAccessor, safeYAccessor, yDomain, xDomain, margin, chartHeight, containerWidth])



  // Don't render chart until we have valid dimensions
  if (!scales || containerWidth < 100) {
    return (
      <ChartWrapper ref={containerRef}>
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
          Loading chart...
        </div>
      </ChartWrapper>
    )
  }

  return (
    <ChartWrapper ref={containerRef}>
      <XYChart
        width={containerWidth}
        height={chartHeight}
        margin={margin}
        xScale={{ type: 'time', ...(xDomain && { domain: xDomain }) }}
        yScale={{ type: 'linear', ...(yDomain && { domain: yDomain }) }}
      >
        <defs>
          <clipPath id="reveal-clip">
            <rect
              x={margin.left}
              y={0}
              width="0"
              height={chartHeight}
              style={{
                animation: 'expandWidth 0.8s ease-out forwards'
              }}
            />
          </clipPath>

          <clipPath id="chart-bounds-clip">
            <rect
              x={margin.left}
              y={margin.top}
              width={containerWidth - margin.left - margin.right}
              height={chartHeight - margin.top - margin.bottom}
            />
          </clipPath>

          {/* Hashed pattern for annotation period highlighting */}
          <pattern
            id="annotation-highlight"
            patternUnits="userSpaceOnUse"
            width="4"
            height="4"
            patternTransform="rotate(45)"
          >
            <rect
              width="4"
              height="4"
              fill="transparent"
            />
            <rect
              x="0"
              y="0"
              width="1"
              height="4"
              fill="hsl(var(--muted-foreground))"
              opacity="0.3"
            />
          </pattern>
        </defs>


        {/* Grid */}
        {showGrid && (
          <Grid
            rows={true}
            columns={false}
            numTicks={effectiveNumTicks}
            lineStyle={{
              stroke: "hsl(var(--border))",
              strokeWidth: 1,
              opacity: 0.5
            }}
          />
        )}

        <Axis
          hideAxisLine
          hideTicks
          orientation="bottom"
          tickFormat={(d: any) => {
            try {
              const dt = d instanceof Date ? d : new Date(d)
              return format(dt, 'd MMMM')
            } catch {
              return ''
            }
          }}
          tickLabelProps={() => ({ dy: tickLabelOffset })}
          numTicks={effectiveNumTicks}
        />
        <Axis
          hideAxisLine={false}
          hideTicks
          orientation="left"
          numTicks={effectiveNumTicks}
          tickFormat={(val: any) => {
            const v = typeof val === 'number' ? val : Number(val)
            if (!Number.isFinite(v)) return ''
            return `${Math.round(v * 100)}%`
          }}
          tickLabelProps={() => ({ dx: -10 })}
        />


        {series.map((line) => (
          <g key={line.dataKey} clipPath="url(#chart-bounds-clip)">
            {/* Smooth spline line */}
            <AnimatedLineSeries
              dataKey={line.dataKey}
              data={line.data}
              xAccessor={safeXAccessor}
              yAccessor={safeYAccessor}
              curve={curveMonotoneX}
            />

            {/* Circle markers */}
            <GlyphSeries
              dataKey={line.dataKey}
              data={line.data}
              xAccessor={safeXAccessor}
              yAccessor={safeYAccessor}
              size={6}
            />
          </g>
        ))}

        {/* Decision point markers with hover annotations */}
        {showDecisionMarkers && modelDecisions.length > 0 && (
          <MarkerAnnotations
            xScale={scales.xScale}
            yScale={scales.yScale}
            cumulativeData={series.length > 0 ? series[0].data.map(d => ({ date: d.date as string, value: d.value as number })) : []}
            modelDecisions={modelDecisions}
          />
        )}

        {/* Visx Tooltip */}
        <Tooltip
          snapTooltipToDatumX
          showVerticalCrosshair
          showSeriesGlyphs
          renderTooltip={({ tooltipData, colorScale }) => {
            if (!tooltipData?.nearestDatum) return null

            // Get all series data at this X position
            const hoveredDate = safeXAccessor(tooltipData.nearestDatum.datum as DataPoint)
            const allSeriesData = series.map(line => {
              // Find closest point in this series to the hovered X position
              const validPoints = line.data.filter(p => {
                const xd = safeXAccessor(p)
                const yd = safeYAccessor(p)
                return xd instanceof Date && !isNaN(xd.getTime()) && Number.isFinite(yd)
              })

              if (validPoints.length === 0) return null

              let closestPoint = validPoints[0]
              let minDistance = Infinity

              for (const point of validPoints) {
                const distance = Math.abs(safeXAccessor(point).getTime() - hoveredDate.getTime())
                if (distance < minDistance) {
                  minDistance = distance
                  closestPoint = point
                }
              }

              return {
                dataKey: line.dataKey,
                name: line.name || line.dataKey,
                value: safeYAccessor(closestPoint),
                color: colorScale?.(line.dataKey) || line.stroke
              }
            }).filter(Boolean)

            return (
              <div style={{
                backgroundColor: 'hsl(var(--popover))',
                color: 'hsl(var(--foreground))',
                border: '1px solid hsl(var(--border))',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
              }}>
                <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                  {formatTooltipX(hoveredDate)}
                </div>
                {allSeriesData.map((seriesItem, index) => (
                  <div key={seriesItem.dataKey} style={{
                    color: seriesItem.color,
                    marginBottom: index < allSeriesData.length - 1 ? '2px' : 0
                  }}>
                    <strong>{(seriesItem.value * 100).toFixed(1)}%</strong>
                    {' - '}
                    {seriesItem.name}
                  </div>
                ))}
              </div>
            )
          }}
        />
      </XYChart>

      {/* Debug overlay removed to keep code minimal */}
    </ChartWrapper>
  )
}

const ChartWrapper = styled.div`
  position: relative;
  max-width: 1000px;
  margin: 0 auto;
  
  text {
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  }

  .visx-axis-tick {
    text {
      font-size: 12px;
      font-weight: 400;
      fill: hsl(var(--muted-foreground));
    }
  }
  
  @keyframes expandWidth {
    from {
      width: 0;
    }
    to {
      width: 100%;
    }
  }

  /* Responsive margins for mobile */
  @media (max-width: 768px) {
    margin-left: -1rem;
    margin-right: -1rem;
    /* Add space for annotation card below chart on mobile */
    padding-bottom: 170px;
  }
`
