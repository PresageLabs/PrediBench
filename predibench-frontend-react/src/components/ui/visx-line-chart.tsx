import { curveMonotoneX } from '@visx/curve'
import { scaleLinear, scaleTime } from '@visx/scale'
import { AnimatedGlyphSeries, AnimatedGrid, AnimatedLineSeries, Axis, XYChart, buildChartTheme } from '@visx/xychart'
import { extent } from 'd3-array'
import { format } from 'date-fns'
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled from 'styled-components'
// Removed unused decision marker props and annotations integration

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


interface TooltipState {
  x: number
  y: number
  datum: DataPoint
  lineConfig: LineSeriesConfig
}

interface HoverState {
  xPosition: number
  tooltips: TooltipState[]
  customAnnotation?: {
    date: Date
    content: React.ReactNode
    nextDate?: Date | null
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
  additionalAnnotations = {}
}: VisxLineChartProps) {
  // Ensure minimum of 4 ticks for better readability
  const effectiveNumTicks = Math.max(numTicks, 4)
  const containerRef = useRef<HTMLDivElement>(null)
  const [hoverState, setHoverState] = useState<HoverState | null>(null)

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

  const chartTheme = useMemo(() => {
    // Use blue-500 (#3b83f6) when there's only one curve, otherwise use original colors
    const colors = series.length === 1
      ? ['#3b83f6']
      : series.map(s => s.stroke)
    return buildChartTheme({
      backgroundColor: 'transparent',
      colors,
      tickLength: 4,
      gridColor: 'hsl(var(--border))',
      gridColorDark: 'hsl(var(--border))',
      svgLabelSmall: { fill: 'hsl(var(--muted-foreground))' },
      svgLabelBig: { fill: 'hsl(var(--muted-foreground))' },
      gridStyles: { stroke: 'hsl(var(--border))', opacity: 1 }
    })
  }, [series])

  const colorByDataKey = useMemo(() => {
    const colors = (chartTheme.colors || []) as string[]
    const map: Record<string, string> = {}
    series.forEach((s, i) => { map[s.dataKey] = colors[i % colors.length] })
    return map
  }, [series, chartTheme])

  const findAnnotationPeriod = useCallback((date: Date): {
    startDate: Date
    endDate: Date | null
    annotation: (typeof additionalAnnotations)[string]
  } | null => {
    if (!additionalAnnotations || Object.keys(additionalAnnotations).length === 0) return null

    const dateTime = date.getTime()
    const annotationDates = Object.keys(additionalAnnotations).sort()

    for (let i = 0; i < annotationDates.length; i++) {
      const startDate = new Date(annotationDates[i])
      const nextDateKey = i < annotationDates.length - 1 ? annotationDates[i + 1] : null
      const explicitNext = additionalAnnotations[annotationDates[i]].getNextDate?.() || null
      const endDate = explicitNext ? new Date(explicitNext) : (nextDateKey ? new Date(nextDateKey) : null)

      const afterStart = dateTime >= startDate.getTime()
      const beforeEnd = !endDate || dateTime < endDate.getTime()
      if (afterStart && beforeEnd) {
        return { startDate, endDate, annotation: additionalAnnotations[annotationDates[i]] }
      }
    }

    return null
  }, [additionalAnnotations])

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
    <ChartWrapper
      ref={containerRef}
      onMouseMove={(e) => {
        if (!containerRef.current || !scales) return
        const rect = containerRef.current.getBoundingClientRect()
        const mouseX = e.clientX - rect.left

        const hoveredTime = scales.xScale.invert(mouseX)

        // If annotation periods are provided, show annotation overlay instead of standard tooltips
        if (additionalAnnotations && Object.keys(additionalAnnotations).length > 0) {
          const period = findAnnotationPeriod(hoveredTime)
          if (period) {
            const startX = scales.xScale(period.startDate)
            const endX = period.endDate ? scales.xScale(period.endDate) : (containerWidth - margin.right)
            const middleX = (startX + endX) / 2
            setHoverState({
              xPosition: middleX,
              tooltips: [],
              customAnnotation: {
                date: period.startDate,
                content: period.annotation.content,
                nextDate: period.endDate ?? undefined
              }
            })
            return
          }
          // No matching period; clear hover when using annotations
          setHoverState(null)
          return
        }
        const newTooltips: { x: number; y: number; datum: DataPoint; lineConfig: LineSeriesConfig }[] = []

        series.forEach((line) => {
          if (!line.data || line.data.length === 0) return
          const validPoints = line.data.filter((p) => {
            const xd = safeXAccessor(p)
            const yd = safeYAccessor(p)
            return xd instanceof Date && !isNaN(xd.getTime()) && Number.isFinite(yd)
          })
          if (validPoints.length === 0) return

          let closestPoint = validPoints[0]
          let minDistance = Infinity
          for (const point of validPoints) {
            const t = safeXAccessor(point).getTime()
            const distance = Math.abs(t - hoveredTime.getTime())
            if (distance < minDistance) {
              minDistance = distance
              closestPoint = point
            }
          }

          const xPos = scales.xScale(safeXAccessor(closestPoint))
          const yPos = scales.yScale(safeYAccessor(closestPoint))
          if (!Number.isFinite(xPos) || !Number.isFinite(yPos)) return

          newTooltips.push({ x: xPos, y: yPos, datum: closestPoint, lineConfig: line })
        })

        // Filter duplicate 0.00% tooltips
        const filtered: typeof newTooltips = []
        let hasSeenZero = false
        newTooltips.forEach((t) => {
          const val = safeYAccessor(t.datum)
          const isDisplayZero = val.toFixed(2) === '0.00'
          if (isDisplayZero) {
            if (!hasSeenZero) {
              filtered.push(t)
              hasSeenZero = true
            }
          } else {
            filtered.push(t)
          }
        })

        const alignedXPosition = filtered.length > 0 ? filtered[0].x : mouseX
        setHoverState({ xPosition: alignedXPosition, tooltips: filtered })
      }}
      onMouseLeave={() => {
        setHoverState(null)
      }}
    >
      <XYChart
        width={containerWidth}
        height={chartHeight}
        margin={margin}
        theme={chartTheme}
        xScale={{ type: 'time', domain: (scales.xScale as any).domain?.() ?? undefined, nice: false }}
        yScale={{ type: 'linear', domain: scales.yDomain, nice: false, zero: false }}
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


        {/* AnimatedGrid */}
        {showGrid && (
          <AnimatedGrid
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

        {/* Hashed area highlighting for annotation periods when active */}
        {hoverState?.customAnnotation && (
          <rect
            x={scales.xScale(hoverState.customAnnotation.date)}
            y={margin.top}
            width={hoverState.customAnnotation.nextDate
              ? (scales.xScale(hoverState.customAnnotation.nextDate) - scales.xScale(hoverState.customAnnotation.date))
              : ((containerWidth - margin.right) - scales.xScale(hoverState.customAnnotation.date))}
            height={chartHeight - margin.top - margin.bottom}
            fill="url(#annotation-highlight)"
            pointerEvents="none"
          />
        )}


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

            {/* Animated circle markers to match line animation */}
            <AnimatedGlyphSeries
              dataKey={line.dataKey}
              data={line.data}
              xAccessor={safeXAccessor}
              yAccessor={safeYAccessor}
              size={6}
            />
          </g>
        ))}
        {/* Decision point markers removed (unused feature) */}
      </XYChart>

      {/* Custom hover overlay with individual positioned tooltips or annotation card */}
      {hoverState && scales && (() => {
        const sortedTooltips = [...hoverState.tooltips].sort((a, b) => b.y - a.y)
        const tooltipHeight = 24
        const gap = 2
        let lastBottom = chartHeight - margin.bottom

        const repositionedTooltips = sortedTooltips.map(t => {
          const originalTop = t.y - tooltipHeight / 2
          let newTop = Math.min(originalTop, lastBottom - tooltipHeight - gap)
          newTop = Math.max(margin.top, newTop)
          lastBottom = newTop
          return { ...t, adjustedY: newTop + tooltipHeight / 2 }
        })

        const tooltipWidth = 200
        const chartWidth = containerWidth - margin.left - margin.right
        const anchorRight = hoverState.xPosition + tooltipWidth > margin.left + chartWidth

        const hoveredDate = hoverState.customAnnotation ? hoverState.customAnnotation.date : scales.xScale.invert(hoverState.xPosition)

        return (
          <div
            style={{
              position: 'absolute',
              left: hoverState.xPosition,
              top: 0,
              pointerEvents: 'none',
              zIndex: 999,
              transform: anchorRight ? 'translateX(-100%)' : 'translateX(0%)'
            }}
          >
            {/* Vertical guide line(s) */}
            {hoverState.customAnnotation ? (
              <>
                <div
                  style={{
                    position: 'absolute',
                    left: scales.xScale(hoverState.customAnnotation.date) - hoverState.xPosition,
                    top: margin.top,
                    width: '1px',
                    backgroundColor: '#9ca3af',
                    height: chartHeight - margin.top - margin.bottom
                  }}
                />
                {hoverState.customAnnotation.nextDate && (
                  <div
                    style={{
                      position: 'absolute',
                      left: scales.xScale(hoverState.customAnnotation.nextDate) - hoverState.xPosition,
                      top: margin.top,
                      width: '1px',
                      backgroundColor: '#9ca3af',
                      height: chartHeight - margin.top - margin.bottom
                    }}
                  />
                )}
              </>
            ) : (
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: margin.top,
                  width: '1px',
                  backgroundColor: '#9ca3af',
                  height: chartHeight - margin.top - margin.bottom
                }}
              />
            )}

            {/* Date label */}
            <div
              style={{
                position: 'absolute',
                left: hoverState.customAnnotation ? (scales.xScale(hoverState.customAnnotation.date) - hoverState.xPosition) : 0,
                top: margin.top - 20,
                transform: anchorRight ? 'translateX(-100%)' : 'translateX(0%)',
                color: '#9ca3af',
                fontSize: '11px',
                fontWeight: '500',
                whiteSpace: 'nowrap'
              }}
            >
              {formatTooltipX(hoveredDate)}
            </div>

            {hoverState.customAnnotation ? (
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: isMobile ? chartHeight + 8 : (margin.top + 40),
                  transform: 'translateX(-50%)',
                  zIndex: 1001,
                  backgroundColor: 'hsl(var(--popover))',
                  color: 'hsl(var(--foreground))',
                  border: '1px solid hsl(var(--border))',
                  padding: isMobile ? '12px 14px' : '16px 20px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  boxShadow: '0 8px 25px -3px rgba(0, 0, 0, 0.15)',
                  minWidth: isMobile ? `${Math.min(420, containerWidth - 24)}px` : '420px',
                  maxWidth: isMobile ? `${Math.max(420, containerWidth - 24)}px` : '500px',
                  whiteSpace: 'normal',
                  pointerEvents: 'auto'
                }}
              >
                {hoverState.customAnnotation.content}
              </div>
            ) : (
              repositionedTooltips.map((tooltip, index) => (
                <div key={`tooltip-${tooltip.lineConfig.dataKey}-${index}`}>
                  <div
                    style={{
                      position: 'absolute',
                      left: tooltip.x - hoverState.xPosition - 5,
                      top: tooltip.y - 5,
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: colorByDataKey[tooltip.lineConfig.dataKey],
                      border: '2px solid white',
                      zIndex: 1000
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      left: anchorRight ? tooltip.x - hoverState.xPosition - 8 : tooltip.x - hoverState.xPosition + 8,
                      top: tooltip.adjustedY,
                      transform: anchorRight ? 'translate(-100%, -50%)' : 'translateY(-50%)',
                      zIndex: 1001,
                      backgroundColor: colorByDataKey[tooltip.lineConfig.dataKey],
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: '500',
                      whiteSpace: 'nowrap',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}
                  >
                    <strong>{(safeYAccessor(tooltip.datum) * 100).toFixed(1)}%</strong> - {(tooltip.lineConfig.name || tooltip.lineConfig.dataKey).substring(0, 50)}
                  </div>
                </div>
              ))
            )}
          </div>
        )
      })()}

      {/* Debug overlay removed to keep code minimal */}
    </ChartWrapper>
  )
}

const ChartWrapper = styled.div`
  position: relative;
  max-width: 1000px;
  margin: 0 auto;
  
  text {
    font-family: inherit;
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
