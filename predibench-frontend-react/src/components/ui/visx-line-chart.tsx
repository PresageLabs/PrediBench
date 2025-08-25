import { scaleLinear, scaleTime } from '@visx/scale'
import {
  AnimatedLineSeries,
  Axis,
  Grid,
  XYChart
} from '@visx/xychart'
import { extent } from 'd3-array'
import { format } from 'date-fns'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled from 'styled-components'

const tickLabelOffset = 10

interface DataPoint {
  x: string | Date
  y: number
  position?: number
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
  formatTooltipX?: (value: Date) => string
  showGrid?: boolean
  numTicks?: number
}

const defaultAccessors = {
  xAccessor: (d: DataPoint) => new Date(d.x as string),
  yAccessor: (d: DataPoint) => d.y
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
}

export function VisxLineChart({
  height = 270,
  margin = { left: 60, top: 35, bottom: 38, right: 27 },
  series,
  xAccessor = defaultAccessors.xAccessor,
  yAccessor = defaultAccessors.yAccessor,
  yDomain,
  formatTooltipX = (value: Date) => format(value, 'MMM d, yyyy'),
  showGrid = true,
  numTicks = 4
}: VisxLineChartProps) {
  // Ensure minimum of 4 ticks for better readability
  const effectiveNumTicks = Math.max(numTicks, 4)
  const containerRef = useRef<HTMLDivElement>(null)
  const [hoverState, setHoverState] = useState<HoverState | null>(null)
  const calculationQueueRef = useRef<{ x: number; timestamp: number }[]>([])
  const isProcessingRef = useRef<boolean>(false)

  const [containerWidth, setContainerWidth] = useState(800)

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
    const allData = series.flatMap(s => s.data)
    if (allData.length === 0) return null

    const xExtent = extent(allData, xAccessor) as [Date, Date]
    let yExtent = yDomain || extent(allData, yAccessor) as [number, number]

    // Ensure Y domain supports at least 4 meaningful ticks (apply to both provided and calculated domains)
    const shouldAdjustDomain = true // Always adjust for better tick count
    if (shouldAdjustDomain) {
      const [dataMin, dataMax] = yExtent

      // Nice intervals in ascending order
      const niceIntervals = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]

      // Function to count how many ticks an interval would produce
      const countTicks = (interval: number, min: number, max: number) => {
        const minTick = Math.floor(min / interval) * interval
        const maxTick = Math.ceil(max / interval) * interval
        return Math.round((maxTick - minTick) / interval) + 1
      }

      // Find the largest interval that still gives us at least effectiveNumTicks
      let bestInterval = niceIntervals[0]
      for (let i = niceIntervals.length - 1; i >= 0; i--) {
        const interval = niceIntervals[i]
        if (countTicks(interval, dataMin, dataMax) >= effectiveNumTicks) {
          bestInterval = interval
          break
        }
      }

      // Calculate final domain
      const minTick = Math.floor(dataMin / bestInterval) * bestInterval
      const maxTick = Math.ceil(dataMax / bestInterval) * bestInterval

      yExtent = [minTick, maxTick]

    }

    const xScale = scaleTime({
      domain: xExtent,
      range: [margin.left, containerWidth - margin.right]
    })

    const yScale = scaleLinear({
      domain: yExtent,
      range: [height - margin.bottom, margin.top]
    })

    return { xScale, yScale, yDomain: yExtent }
  }, [series, xAccessor, yAccessor, yDomain, margin, height, containerWidth, effectiveNumTicks])

  const processCalculationQueue = useCallback((targetX: number) => {
    if (!containerRef.current || !scales) return

    const hoveredTime = scales.xScale.invert(targetX)
    const newTooltips: TooltipState[] = []

    series.forEach((line) => {
      if (line.data.length === 0) return

      // Find closest data point by time
      let closestPoint = line.data[0]
      let minDistance = Infinity

      line.data.forEach((point) => {
        const distance = Math.abs(xAccessor(point).getTime() - hoveredTime.getTime())
        if (distance < minDistance) {
          minDistance = distance
          closestPoint = point
        }
      })

      // Use scales to get exact screen coordinates
      const xPos = scales.xScale(xAccessor(closestPoint))
      const yPos = scales.yScale(yAccessor(closestPoint))

      newTooltips.push({
        x: xPos,
        y: yPos,
        datum: closestPoint,
        lineConfig: line
      })
    })

    // Filter out duplicate y=0 tooltips before setting state
    const filteredTooltips: TooltipState[] = []
    let hasSeenZero = false

    newTooltips.forEach(tooltip => {
      const yValue = yAccessor(tooltip.datum)
      // Check if the value would display as "0.00" when formatted with .toFixed(2)
      const displayValue = yValue.toFixed(2)
      const isDisplayZero = displayValue === '0.00'

      if (isDisplayZero) {
        if (!hasSeenZero) {
          filteredTooltips.push(tooltip)
          hasSeenZero = true
        }
        // Skip subsequent tooltips that display as 0.00
      } else {
        filteredTooltips.push(tooltip)
      }
    })

    // Use the x position from the first tooltip for the vertical line
    const alignedXPosition = filteredTooltips.length > 0 ? filteredTooltips[0].x : targetX

    setHoverState({
      xPosition: alignedXPosition,
      tooltips: filteredTooltips
    })
  }, [series, xAccessor, yAccessor, scales, containerRef])

  const handlePointerMove = useCallback((params: { event?: React.PointerEvent<Element> | React.FocusEvent<Element, Element>; svgPoint?: { x: number; y: number } }) => {
    if (!params.event || !containerRef.current || !scales) return

    const containerRect = containerRef.current.getBoundingClientRect()
    const mouseX = (params.event as React.PointerEvent<Element>).clientX - containerRect.left
    const now = Date.now()

    // Add to queue
    calculationQueueRef.current.push({ x: mouseX, timestamp: now })

    // Prune queue if it gets too large (keep only quantiles)
    const pruneThreshold = 5
    const quantiles = 4 // Can be adjusted: 4=quartiles, 10=deciles, etc.
    
    if (calculationQueueRef.current.length > pruneThreshold) {
      const queue = calculationQueueRef.current
      const prunedQueue: { x: number; timestamp: number }[] = []
      
      // Keep quantiles of the queue
      const step = Math.floor(queue.length / quantiles)
      for (let i = step - 1; i < queue.length; i += step) {
        prunedQueue.push(queue[i])
      }
      
      // Always keep the last item (most recent)
      if (prunedQueue[prunedQueue.length - 1] !== queue[queue.length - 1]) {
        prunedQueue.push(queue[queue.length - 1])
      }
      
      calculationQueueRef.current = prunedQueue
    }

    // Process queue if not already processing
    if (!isProcessingRef.current && calculationQueueRef.current.length > 0) {
      isProcessingRef.current = true
      
      const processNext = () => {
        if (calculationQueueRef.current.length === 0) {
          isProcessingRef.current = false
          return
        }
        
        // Take the most recent item from queue
        const item = calculationQueueRef.current.pop()!
        processCalculationQueue(item.x)
        
        // Continue processing if there are more items
        if (calculationQueueRef.current.length > 0) {
          setTimeout(processNext, 0) // Use setTimeout to avoid blocking
        } else {
          isProcessingRef.current = false
        }
      }
      
      processNext()
    }
  }, [processCalculationQueue])

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
      onMouseLeave={() => {
        // Clear queue and state when mouse leaves
        calculationQueueRef.current = []
        isProcessingRef.current = false
        setHoverState(null)
      }}
    >
      <XYChart
        width={containerWidth}
        height={height}
        margin={margin}
        xScale={{ type: 'time' }}
        yScale={{ type: 'linear', domain: scales?.yDomain }}
        onPointerMove={handlePointerMove}
      >
        <defs>
          <clipPath id="reveal-clip">
            <rect
              x={margin.left}
              y={margin.top}
              width="0"
              height={height - margin.top - margin.bottom}
              style={{
                animation: 'expandWidth 0.8s ease-out forwards'
              }}
            />
          </clipPath>

          {/* Dynamic hover clip paths for colored lines */}
          {hoverState && series.map((_, index) => (
            <clipPath key={index} id={`hover-clip-${index}`}>
              <rect
                x={margin.left}
                y={margin.top}
                width={Math.max(0, hoverState.xPosition - margin.left)}
                height={height - margin.top - margin.bottom}
              />
            </clipPath>
          ))}
        </defs>
        {/* Horizontal grid lines for each Y tick */}
        {showGrid && (
          <Grid
            columns={false}
            rows={true}
            numTicks={effectiveNumTicks}
            lineStyle={{
              stroke: 'hsl(var(--border))',
              strokeLinecap: 'round',
              strokeWidth: 1,
              strokeOpacity: 0.5
            }}
          />
        )}

        <Axis
          hideAxisLine
          hideTicks
          orientation="bottom"
          tickLabelProps={() => ({ dy: tickLabelOffset })}
          numTicks={effectiveNumTicks}
        />
        <Axis
          hideAxisLine
          hideTicks
          orientation="left"
          numTicks={effectiveNumTicks}
          tickLabelProps={() => ({ dx: -10 })}
        />

        {series.map((line, index) => (
          <g key={line.dataKey}>
            {/* Gray background line */}
            <AnimatedLineSeries
              stroke="hsl(var(--muted-foreground))"
              dataKey={`${line.dataKey}-gray`}
              data={line.data}
              xAccessor={xAccessor}
              yAccessor={yAccessor}
              style={{
                clipPath: 'url(#reveal-clip)'
              }}
            />

            {/* Colored line clipped to hover position */}
            <AnimatedLineSeries
              stroke={line.stroke}
              dataKey={`${line.dataKey}-colored`}
              data={line.data}
              xAccessor={xAccessor}
              yAccessor={yAccessor}
              style={{
                clipPath: hoverState ? `url(#hover-clip-${index})` : 'url(#reveal-clip)'
              }}
            />
          </g>
        ))}
      </XYChart>

      {/* Hover state: single sliding container */}
      {hoverState && (() => {
        // Calculate anchoring once for the entire hover container
        const tooltipWidth = 150
        const chartWidth = containerWidth - margin.left - margin.right
        const anchorRight = hoverState.xPosition + tooltipWidth > margin.left + chartWidth

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
            {/* Vertical hover line */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: margin.top,
                width: '1px',
                backgroundColor: '#9ca3af',
                height: height - margin.top - margin.bottom
              }}
            />

            {/* Date label */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: margin.top - 20,
                transform: anchorRight ? 'translateX(-100%)' : 'translateX(0%)',
                color: '#9ca3af',
                fontSize: '11px',
                fontWeight: '500',
                whiteSpace: 'nowrap'
              }}
            >
              {hoverState.tooltips.length > 0 && formatTooltipX(xAccessor(hoverState.tooltips[0].datum))}
            </div>

            {/* Tooltips and hover points - positioned relative to container */}
            {(() => {
              // Sort from bottom to top (filtering is now done earlier)
              const sortedTooltips = [...hoverState.tooltips].sort((a, b) => b.y - a.y)

              // Position tooltips with overlap prevention
              const tooltipHeight = 24
              const gap = 2
              let lastBottom = height

              const repositionedTooltips = sortedTooltips.map(tooltip => {
                const originalTop = tooltip.y - tooltipHeight / 2
                let newTop = Math.min(originalTop, lastBottom - tooltipHeight - gap)
                newTop = Math.max(margin.top, newTop)
                lastBottom = newTop

                return {
                  ...tooltip,
                  adjustedY: newTop + tooltipHeight / 2,
                  // Convert absolute positions to relative positions within container
                  relativeX: tooltip.x - hoverState.xPosition
                }
              })

              return repositionedTooltips.map((tooltip, index) => (
                <div key={`tooltip-${tooltip.lineConfig.dataKey}-${index}`}>
                  {/* Hover point - positioned relative to container */}
                  <div
                    style={{
                      position: 'absolute',
                      left: tooltip.relativeX - 5,
                      top: tooltip.y - 5,
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: tooltip.lineConfig.stroke,
                      border: '2px solid white',
                      zIndex: 1000
                    }}
                  />

                  {/* Tooltip - positioned relative to container */}
                  <div
                    style={{
                      position: 'absolute',
                      left: anchorRight ? tooltip.relativeX - 8 : tooltip.relativeX + 8,
                      top: tooltip.adjustedY,
                      transform: anchorRight ? 'translate(-100%, -50%)' : 'translateY(-50%)',
                      zIndex: 1001,
                      backgroundColor: tooltip.lineConfig.stroke,
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: '500',
                      whiteSpace: 'nowrap',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}
                  >
                    <strong>{yAccessor(tooltip.datum).toFixed(2)}</strong> - {(tooltip.lineConfig.name || tooltip.lineConfig.dataKey).substring(0, 20)}
                  </div>
                </div>
              ))
            })()}
          </div>
        )
      })()}
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
`
