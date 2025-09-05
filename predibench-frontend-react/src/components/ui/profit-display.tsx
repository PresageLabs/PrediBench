interface ProfitDisplayProps {
  value: number
  minValue?: number
  maxValue?: number
  formatValue?: (value: number) => string
  className?: string
}

const getProfitColor = (value: number, minValue: number, maxValue: number): string => {
  if (value === 0) {
    return 'rgb(255, 255, 0)' // Pure yellow for zero
  }
  
  if (value < 0) {
    // Negative values: Yellow to Deep Orange
    // Normalize between 0 (at zero) and 1 (at most negative)
    const intensity = Math.abs(value) / Math.abs(minValue)
    const red = 255
    const green = Math.round(255 - (90 * intensity)) // 255 (yellow) to 165 (orange)
    return `rgb(${red}, ${green}, 0)`
  } else {
    // Positive values: Yellow to Green
    // Normalize between 0 (at zero) and 1 (at most positive)
    const intensity = value / maxValue
    const red = Math.round(255 * (1 - intensity)) // 255 (yellow) to 0 (green)
    const green = 255
    return `rgb(${red}, ${green}, 0)`
  }
}

export function ProfitDisplay({ 
  value, 
  minValue, 
  maxValue, 
  formatValue = (v) => {
    // Check if value rounds to zero at 2 decimal places
    if (Math.abs(v) < 0.005) return '$0.00'
    return `${v > 0 ? '+' : ''}$${v.toFixed(2)}`
  },
  className = ""
}: ProfitDisplayProps) {
  // Use consistent global bounds if none provided
  const effectiveMinValue = minValue !== undefined ? minValue : -0.3
  const effectiveMaxValue = maxValue !== undefined ? maxValue : 0.3
  
  const color = getProfitColor(value, effectiveMinValue, effectiveMaxValue)
  
  return (
    <span 
      style={{ color }}
      className={className}
    >
      {formatValue(value)}
    </span>
  )
}

export { getProfitColor }