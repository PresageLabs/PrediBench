import React from 'react'

interface EventDecisionThumbnailProps {
  title: React.ReactNode
  topMarketName?: string | null
  topBet?: number | null
  decisionsCount: number
  onClick?: () => void
}

export function EventDecisionThumbnail({
  title,
  topMarketName,
  topBet,
  decisionsCount,
  onClick
}: EventDecisionThumbnailProps) {
  const isNumber = typeof topBet === 'number'
  const isPositive = isNumber && (topBet as number) > 0
  const isNegative = isNumber && (topBet as number) < 0
  const betLabel = isNumber
    ? `${isPositive ? '+' : isNegative ? '-' : ''}$${Math.abs(topBet as number).toFixed(2)}`
    : 'N/A'

  return (
    <button
      onClick={onClick}
      className="w-full p-3 bg-muted/20 rounded hover:bg-muted/30 transition-colors text-left h-full border border-transparent hover:border-border"
    >
      <div className="font-medium text-sm mb-1 line-clamp-2">{title}</div>
      <div className="mt-1 text-xs flex items-center justify-between gap-2">
        <div className="text-muted-foreground line-clamp-2 flex-1 min-w-0">{topMarketName || 'N/A'}</div>
        <div>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${isPositive ? 'bg-green-100 text-green-800' : isNegative ? 'bg-red-100 text-red-800' : 'bg-muted text-foreground'
            }`}>
            {betLabel}
          </span>
        </div>
      </div>
      <div className="text-xs text-muted-foreground mt-1 italic pl-4">+{decisionsCount} market decisions</div>
    </button>
  )
}
