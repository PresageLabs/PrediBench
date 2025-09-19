import { ArrowDown, ChevronDown } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { DecisionReturns, DecisionSharpe, LeaderboardEntry } from '../api'
import { encodeSlashes } from '../lib/utils'
import { CompanyDisplay } from './ui/company-display'
import { BrierScoreInfoTooltip } from './ui/info-tooltip'
import { ProfitDisplay } from './ui/profit-display'

type SortKey = 'brier_score' | 'average_returns' | 'sharpe'
type TimeHorizon = 'one_day' | 'two_day' | 'seven_day' | 'all_time'

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
  const [timeHorizon, setTimeHorizon] = useState<TimeHorizon>('seven_day')

  const getReturnForHorizon = (returns: DecisionReturns, horizon: TimeHorizon): number => {
    switch (horizon) {
      case 'one_day': return returns.one_day_return
      case 'two_day': return returns.two_day_return
      case 'seven_day': return returns.seven_day_return
      case 'all_time': return returns.all_time_return
    }
  }

  const getSharpeForHorizon = (sharpe: DecisionSharpe, horizon: TimeHorizon): number => {
    switch (horizon) {
      case 'one_day': return sharpe.one_day_annualized_sharpe
      case 'two_day': return sharpe.two_day_annualized_sharpe
      case 'seven_day': return sharpe.seven_day_annualized_sharpe
      case 'all_time': return sharpe.seven_day_annualized_sharpe // Use 7-day as fallback since all_time_annualized_sharpe doesn't exist
    }
  }

  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      switch (sortKey) {
        case 'brier_score': {
          // Calculate display scores for Brier using time horizon (rounded to 3 decimal places)
          const aBrierDisplay = parseFloat((a.final_brier_score).toFixed(3))
          const bBrierDisplay = parseFloat((b.final_brier_score).toFixed(3))

          // Primary sort by Brier display score (lower first - ascending)
          if (aBrierDisplay !== bBrierDisplay) {
            return aBrierDisplay - bBrierDisplay
          }

          // Tie-breaker: if display scores are identical, use PnL
          return b.final_profit - a.final_profit
        }

        case 'average_returns': {
          const aReturn = getReturnForHorizon(a.average_returns, timeHorizon)
          const bReturn = getReturnForHorizon(b.average_returns, timeHorizon)

          // Primary sort by returns (higher first - descending)
          if (bReturn !== aReturn) {
            return bReturn - aReturn
          }

          // Tie-breaker: use Brier score
          return a.final_brier_score - b.final_brier_score
        }

        case 'sharpe': {
          const aSharpe = getSharpeForHorizon(a.sharpe, timeHorizon)
          const bSharpe = getSharpeForHorizon(b.sharpe, timeHorizon)

          // Primary sort by Sharpe (higher first - descending)
          if (bSharpe !== aSharpe) {
            return bSharpe - aSharpe
          }

          // Tie-breaker: use Brier score
          return a.final_brier_score - b.final_brier_score
        }

        default:
          return 0
      }
    })
  }, [leaderboard, sortKey, timeHorizon])


  const handleSort = (key: SortKey) => {
    setSortKey(key)
  }

  // Ranges for Avg Returns and Sharpe (used for consistent coloring)
  const returnsRange = useMemo(() => {
    if (leaderboard.length === 0) return { min: 0, max: 0 }
    const vals = leaderboard.map(model => getReturnForHorizon(model.average_returns, timeHorizon))
    return {
      min: Math.min(...vals),
      max: Math.max(...vals)
    }
  }, [leaderboard, timeHorizon])
  const sharpeRange = useMemo(() => {
    if (leaderboard.length === 0) return { min: 0, max: 0 }
    const vals = leaderboard.map(model => getSharpeForHorizon(model.sharpe, timeHorizon))
    return {
      min: Math.min(...vals),
      max: Math.max(...vals)
    }
  }, [leaderboard, timeHorizon])


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


      <div className="relative flex gap-4">
        <div className="flex-1">
          <div
            className={`overflow-hidden transition-all duration-300 ${leaderboardExpanded ? 'max-h-none' : 'max-h-[500px]'
              }`}
          >
            <div className="bg-card rounded-xl border border-border/30 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full table-auto">
                  <thead className="bg-muted/30">
                    <tr>
                      <th className="text-center py-4 px-3 font-semibold"></th>
                      <th className="text-left py-4 px-4 font-semibold">Model Name</th>
                      <th className="text-center py-3 px-4 font-semibold">
                        <div className="flex items-center justify-center space-x-1 w-full">
                          <button
                            onClick={() => handleSort('average_returns')}
                            className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                          >
                            <ArrowDown className={`h-4 w-4 ${sortKey === 'average_returns' ? 'text-primary' : 'opacity-40'}`} />
                            <span>Avg Returns</span>
                          </button>
                        </div>
                      </th>
                      <th className="text-center py-3 px-4 font-semibold">
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
                      <th className="text-center py-3 px-4 font-semibold">
                        <div className="flex items-center justify-center space-x-1 w-full">
                          <button
                            onClick={() => handleSort('sharpe')}
                            className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                          >
                            <ArrowDown className={`h-4 w-4 ${sortKey === 'sharpe' ? 'text-primary' : 'opacity-40'}`} />
                            <span>Sharpe</span>
                          </button>
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
                              <ProfitDisplay
                                value={getReturnForHorizon(model.average_returns, timeHorizon)}
                                minValue={returnsRange.min}
                                maxValue={returnsRange.max}
                                formatValue={(v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`}
                              />
                            </a>
                          </td>
                          <td className="py-4 px-4 text-center font-medium">
                            <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                              {model.final_brier_score.toFixed(3)}
                            </a>
                          </td>
                          <td className="py-4 px-4 text-center font-medium">
                            <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                              <ProfitDisplay
                                value={getSharpeForHorizon(model.sharpe, timeHorizon)}
                                minValue={sharpeRange.min}
                                maxValue={sharpeRange.max}
                                formatValue={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(3)}`}
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

        {/* Time Horizon Selector */}
        {!loading && leaderboard.length > 0 && (
          <div className="w-48 pt-8">
            <div className="p-3 bg-card rounded-lg border border-border/30">
              <div className="mb-2">
                <span className="text-xs font-medium text-muted-foreground">Time Horizon:</span>
              </div>
              <select
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(e.target.value as TimeHorizon)}
                className="w-full text-xs border border-border rounded px-2 py-1 bg-background"
              >
                <option value="one_day">1 Day</option>
                <option value="two_day">2 Days</option>
                <option value="seven_day">7 Days</option>
                <option value="all_time">All Time</option>
              </select>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
