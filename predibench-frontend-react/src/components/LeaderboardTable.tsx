import { ArrowDown, ChevronDown } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { LeaderboardEntry } from '../api'
import { encodeSlashes } from '../lib/utils'
import { CompanyDisplay } from './ui/company-display'
import { BrierScoreInfoTooltip, PnLTooltip } from './ui/info-tooltip'
import { ProfitDisplay } from './ui/profit-display'

type SortKey = 'cumulative_profit' | 'brier_score' | 'average_returns'
type ReturnHorizon = 'one_day' | 'two_day' | 'seven_day' | 'all_time'

interface LeaderboardTableProps {
  leaderboard: LeaderboardEntry[]
  loading?: boolean
  initialVisibleModels?: number
}

export function LeaderboardTable({
  leaderboard,
  loading = false,
  initialVisibleModels = 10
}: LeaderboardTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('brier_score')
  const [leaderboardExpanded, setLeaderboardExpanded] = useState<boolean>(false)
  const [returnHorizon, setReturnHorizon] = useState<ReturnHorizon>('one_day')

  // Helper function to get return value for a specific horizon
  const getReturnValue = (entry: LeaderboardEntry, horizon: ReturnHorizon): number => {
    switch (horizon) {
      case 'one_day':
        return entry.average_returns.one_day_return
      case 'two_day':
        return entry.average_returns.two_day_return
      case 'seven_day':
        return entry.average_returns.seven_day_return
      case 'all_time':
        return entry.average_returns.all_time_return
      default:
        return 0
    }
  }

  // Helper function to get horizon display name
  const getHorizonDisplayName = (horizon: ReturnHorizon): string => {
    switch (horizon) {
      case 'one_day':
        return '1 Day'
      case 'two_day':
        return '2 Days'
      case 'seven_day':
        return '7 Days'
      case 'all_time':
        return 'All Time'
      default:
        return ''
    }
  }

  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      switch (sortKey) {
        case 'cumulative_profit': {
          // Calculate display scores (rounded to 1 decimal place)
          const aDisplayScore = parseFloat((a.final_profit * 100).toFixed(1))
          const bDisplayScore = parseFloat((b.final_profit * 100).toFixed(1))

          // Primary sort by display score (higher first)
          if (bDisplayScore !== aDisplayScore) {
            return bDisplayScore - aDisplayScore
          }

          // Tie-breaker: if display scores are identical, use Brier score (lower is better)
          return a.final_brier_score - b.final_brier_score
        }

        case 'brier_score': {
          // Calculate display scores for Brier (rounded to 3 decimal places)
          const aBrierDisplay = parseFloat(a.final_brier_score.toFixed(3))
          const bBrierDisplay = parseFloat(b.final_brier_score.toFixed(3))

          // Primary sort by Brier display score (lower first - ascending)
          if (aBrierDisplay !== bBrierDisplay) {
            return aBrierDisplay - bBrierDisplay
          }

          // Tie-breaker: if display scores are identical, use PnL
          return b.final_profit - a.final_profit
        }

        case 'average_returns': {
          // Get return values for the current horizon
          const aReturn = getReturnValue(a, returnHorizon)
          const bReturn = getReturnValue(b, returnHorizon)

          // Sort by return value (higher first - descending)
          if (bReturn !== aReturn) {
            return bReturn - aReturn
          }

          // Tie-breaker: use Brier score (lower is better)
          return a.final_brier_score - b.final_brier_score
        }

        default:
          return 0
      }
    })
  }, [leaderboard, sortKey, returnHorizon])


  const handleSort = (key: SortKey) => {
    setSortKey(key)
  }

  // Calculate min and max profit values for color scaling
  const profitRange = useMemo(() => {
    if (leaderboard.length === 0) return { min: 0, max: 0 }
    const profits = leaderboard.map(model => model.final_profit)
    return {
      min: Math.min(...profits),
      max: Math.max(...profits)
    }
  }, [leaderboard])


  return (
    <div>
      {/* Loading Spinner when initially loading */}
      {loading && leaderboard.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
            <div className="text-sm text-muted-foreground">Loading leaderboard...</div>
          </div>
        </div>
      )}

      <div className="relative">
        <div
          className={`overflow-hidden transition-all duration-300 ${
            leaderboardExpanded ? 'max-h-none' : 'max-h-[500px]'
          }`}
        >
          <div className="bg-card rounded-xl border border-border/30 overflow-hidden max-w-3xl mx-auto">
            <div className="overflow-x-auto">
              <table className="w-full table-fixed">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="text-center py-4 px-3 font-semibold w-12"></th>
                    <th className="text-left py-4 px-4 font-semibold w-28">Model Name</th>
                    <th className="text-center py-3 px-4 font-semibold w-24">
                      <div className="flex items-center justify-center space-x-1 w-full">
                        <button
                          onClick={() => handleSort('brier_score')}
                          className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                          title="Brier Score - Lower values indicate better prediction accuracy (0 = perfect, 1 = worst)"
                        >
                          <ArrowDown className={`h-4 w-4 ${sortKey === 'brier_score' ? 'text-primary' : 'opacity-40'}`} />
                          <span>Brier Score</span>
                        </button>
                        <BrierScoreInfoTooltip />
                      </div>
                    </th>
                    <th className="text-center py-3 px-4 font-semibold w-24">
                      <div className="flex items-center justify-center space-x-1 w-full">
                        <button
                          onClick={() => handleSort('cumulative_profit')}
                          className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                        >
                          <ArrowDown className={`h-4 w-4 ${sortKey === 'cumulative_profit' ? 'text-primary' : 'opacity-40'}`} />
                          <span>Portfolio Increase</span>
                        </button>
                        <PnLTooltip />
                      </div>
                    </th>
                    <th className="text-center py-3 px-4 font-semibold w-32">
                      <div className="flex flex-col items-center space-y-1 w-full">
                        <button
                          onClick={() => handleSort('average_returns')}
                          className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                        >
                          <ArrowDown className={`h-4 w-4 ${sortKey === 'average_returns' ? 'text-primary' : 'opacity-40'}`} />
                          <span>Average Returns</span>
                        </button>
                        <select
                          value={returnHorizon}
                          onChange={(e) => setReturnHorizon(e.target.value as ReturnHorizon)}
                          className="text-xs bg-background border border-border rounded px-1 py-0.5"
                        >
                          <option value="one_day">1 Day</option>
                          <option value="two_day">2 Days</option>
                          <option value="seven_day">7 Days</option>
                          <option value="all_time">All Time</option>
                        </select>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loading && leaderboard.length === 0 ? (
                    Array.from({ length: 5 }).map((_, index) => (
                      <tr key={index} className="border-t border-border/20">
                        <td className="py-2 px-3 text-center">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-8 mx-auto"></div>
                        </td>
                        <td className="py-2 px-4">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-32 mb-2"></div>
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-20 ml-2"></div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    sortedLeaderboard.map((model, index) => (
                      <tr key={model.model_id} className="border-t border-border/20 hover:bg-muted/20 transition-colors">
                        <td className="py-2 px-3 text-center">
                          <span className={index <= 2 ? "text-2xl" : "text-md font-medium text-muted-foreground"}>
                            {index === 0 ? '🥇' :
                              index === 1 ? '🥈' :
                                index === 2 ? '🥉' :
                                  `#${index + 1}`}
                          </span>
                        </td>
                        <td className="py-2 px-4">
                          <div>
                            <a
                              href={`/models?selected=${encodeSlashes(model.model_id)}`}
                              className="font-medium hover:text-primary transition-colors block"
                            >
                              {model.model_name}
                            </a>
                            <div className="ml-2 mt-1">
                              <CompanyDisplay modelName={model.model_name} />
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-center font-medium">
                          <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                            {model.final_brier_score ? model.final_brier_score.toFixed(3) : 'N/A'}
                          </a>
                        </td>
                        <td className="py-4 px-4 text-center font-medium">
                          <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                            <ProfitDisplay
                              value={model.final_profit}
                              minValue={profitRange.min}
                              maxValue={profitRange.max}
                              formatValue={(v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`}
                            />
                          </a>
                        </td>
                        <td className="py-4 px-4 text-center font-medium">
                          <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                            <ProfitDisplay
                              value={getReturnValue(model, returnHorizon)}
                              minValue={Math.min(...leaderboard.map(m => getReturnValue(m, returnHorizon)))}
                              maxValue={Math.max(...leaderboard.map(m => getReturnValue(m, returnHorizon)))}
                              formatValue={(v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`}
                            />
                          </a>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        {!leaderboardExpanded && sortedLeaderboard.length > initialVisibleModels && (
          <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent flex items-end justify-center pb-2">
            <button
              onClick={() => setLeaderboardExpanded(true)}
              className="flex items-center gap-2 px-4 py-2 bg-background border border-border rounded-lg hover:bg-accent transition-colors text-sm"
            >
              <span>Show all</span>
              <ChevronDown size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}