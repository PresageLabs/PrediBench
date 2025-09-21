interface ProfitDisplayProps {
  value: number
  minValue?: number
  maxValue?: number
  formatValue?: (value: number) => string
  className?: string
}

const getProfitColor = (value: number, minValue: number, maxValue: number, isDarkMode: boolean): string => {
  if (value === 0) {
    // Yellow for zero - darker in light mode
    return isDarkMode ? 'rgb(255, 255, 0)' : 'rgb(180, 150, 0)'
  }

  if (value < 0) {
    // Negative values: Yellow to Deep Orange/Red
    // Normalize between 0 (at zero) and 1 (at most negative)
    const intensity = Math.abs(minValue) === 0 ? 0 : Math.abs(value) / Math.abs(minValue)

    if (isDarkMode) {
      const red = 255
      const green = Math.round(255 - (90 * intensity)) // 255 (yellow) to 165 (orange)
      return `rgb(${red}, ${green}, 0)`
    } else {
      // Light mode: darker colors
      const red = Math.round(180 + (40 * intensity)) // 180 to 220
      const green = Math.round(150 - (100 * intensity)) // 150 (yellowish) to 50 (red)
      return `rgb(${red}, ${green}, 0)`
    }
  } else {
    // Positive values: Yellow to Green
    // Normalize between 0 (at zero) and 1 (at most positive)
    const intensity = maxValue === 0 ? 0 : value / maxValue

    if (isDarkMode) {
      const red = Math.round(255 * (1 - intensity)) // 255 (yellow) to 0 (green)
      const green = 255
      return `rgb(${red}, ${green}, 0)`
    } else {
      // Light mode: darker colors
      const red = Math.round(150 * (1 - intensity)) // 150 (yellowish) to 0 (green)
      const green = Math.round(150 + (30 * intensity)) // 150 to 180 (darker green)
      return `rgb(${red}, ${green}, 0)`
    }
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

  // Detect dark mode
  const isDarkMode = document.documentElement.classList.contains('dark')

  const color = getProfitColor(value, effectiveMinValue, effectiveMaxValue, isDarkMode)

  return (
    <span
      style={{ color }}
      className={className}
    >
      {formatValue(value)}
    </span>
  )
}

// Export with a wrapper that auto-detects dark mode
const getProfitColorWrapper = (value: number, minValue: number, maxValue: number): string => {
  const isDarkMode = document.documentElement.classList.contains('dark')
  return getProfitColor(value, minValue, maxValue, isDarkMode)
}

export { getProfitColorWrapper as getProfitColor }