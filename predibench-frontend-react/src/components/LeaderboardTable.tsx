import { ArrowDown, ChevronDown } from 'lucide-react'
import { useMemo, useState, useEffect, useRef } from 'react'
import type { DecisionReturns, DecisionSharpe, LeaderboardEntry } from '../api'
import { encodeSlashes } from '../lib/utils'
import { CompanyDisplay } from './ui/company-display'
import { BrierScoreInfoTooltip, InfoTooltip } from './ui/info-tooltip'
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
  const [sortKey, setSortKey] = useState<SortKey>('average_returns')
  const [leaderboardExpanded, setLeaderboardExpanded] = useState<boolean>(false)
  const [returnsTimeHorizon, setReturnsTimeHorizon] = useState<TimeHorizon>('seven_day')
  const [sharpeTimeHorizon, setSharpeTimeHorizon] = useState<'one_day' | 'two_day' | 'seven_day'>('seven_day')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [returnsDropdownOpen, setReturnsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const returnsDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
      if (returnsDropdownRef.current && !returnsDropdownRef.current.contains(event.target as Node)) {
        setReturnsDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const getReturnForHorizon = (returns: DecisionReturns, horizon: TimeHorizon): number => {
    switch (horizon) {
      case 'one_day': return returns.one_day_return
      case 'two_day': return returns.two_day_return
      case 'seven_day': return returns.seven_day_return
      case 'all_time': return returns.all_time_return
    }
  }

  const getSharpeForHorizon = (sharpe: DecisionSharpe, horizon: 'one_day' | 'two_day' | 'seven_day'): number => {
    switch (horizon) {
      case 'one_day': return sharpe.one_day_annualized_sharpe
      case 'two_day': return sharpe.two_day_annualized_sharpe
      case 'seven_day': return sharpe.seven_day_annualized_sharpe
    }
  }

  const getSharpeSignificance = (sharpe: number, tradesCount: number): 'significant' | 'insignificant' => {
    // Calculate t-statistic: t ≈ Sharpe * sqrt(T) where T = number of independent observations
    const tStatistic = Math.abs(sharpe) * Math.sqrt(tradesCount)

    // Significant if t >= 1.96 (5% level, two-sided) and Sharpe is positive
    return sharpe > 0 && tStatistic >= 1.96 ? 'significant' : 'insignificant'
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
          const aReturn = getReturnForHorizon(a.average_returns, returnsTimeHorizon)
          const bReturn = getReturnForHorizon(b.average_returns, returnsTimeHorizon)

          // Primary sort by returns (higher first - descending)
          if (bReturn !== aReturn) {
            return bReturn - aReturn
          }

          // Tie-breaker: use Brier score
          return a.final_brier_score - b.final_brier_score
        }

        case 'sharpe': {
          const aSharpe = getSharpeForHorizon(a.sharpe, sharpeTimeHorizon)
          const bSharpe = getSharpeForHorizon(b.sharpe, sharpeTimeHorizon)

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
  }, [leaderboard, sortKey, returnsTimeHorizon, sharpeTimeHorizon])


  const handleSort = (key: SortKey) => {
    setSortKey(key)
  }

  // Ranges for Average Returns and Sharpe (used for consistent coloring)
  const returnsRange = useMemo(() => {
    if (leaderboard.length === 0) return { min: 0, max: 0 }
    const vals = leaderboard.map(model => getReturnForHorizon(model.average_returns, returnsTimeHorizon))
    return {
      min: Math.min(...vals),
      max: Math.max(...vals)
    }
  }, [leaderboard, returnsTimeHorizon])

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
                      <div className="flex flex-col items-center space-y-1 w-full">
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => handleSort('average_returns')}
                            className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                          >
                            <ArrowDown className={`h-4 w-4 ${sortKey === 'average_returns' ? 'text-primary' : 'opacity-40'}`} />
                            <span>Average Returns</span>
                          </button>
                          <InfoTooltip content="Average return per prediction across all bet. Each bet's return is calculated at the selected time horizon." />
                        </div>
                        <div className="relative" ref={returnsDropdownRef}>
                          <button
                            onClick={() => setReturnsDropdownOpen(!returnsDropdownOpen)}
                            className="text-xs font-medium border border-border rounded-md px-2 py-1 bg-background text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors cursor-pointer flex items-center gap-1 min-w-[70px]"
                          >
                            <span>
                              {returnsTimeHorizon === 'one_day' ? '1 Day' :
                               returnsTimeHorizon === 'two_day' ? '2 Days' :
                               returnsTimeHorizon === 'seven_day' ? '7 Days' : 'All Time'}
                            </span>
                            <ChevronDown className={`h-3 w-3 transition-transform ${returnsDropdownOpen ? 'rotate-180' : ''}`} />
                          </button>
                          {returnsDropdownOpen && (
                            <div className="absolute top-full left-0 mt-1 w-full bg-background border border-border rounded-md overflow-hidden z-50">
                              <button
                                onClick={() => {
                                  setReturnsTimeHorizon('one_day')
                                  setReturnsDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                1 Day
                              </button>
                              <button
                                onClick={() => {
                                  setReturnsTimeHorizon('two_day')
                                  setReturnsDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                2 Days
                              </button>
                              <button
                                onClick={() => {
                                  setReturnsTimeHorizon('seven_day')
                                  setReturnsDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                7 Days
                              </button>
                              <button
                                onClick={() => {
                                  setReturnsTimeHorizon('all_time')
                                  setReturnsDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                All Time
                              </button>
                            </div>
                          )}
                        </div>
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
                    <th className="hidden md:table-cell text-center py-3 px-4 font-semibold">
                      <div className="flex flex-col items-center space-y-1 w-full">
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => handleSort('sharpe')}
                            className="flex items-center space-x-1 hover:text-primary transition-colors whitespace-nowrap"
                          >
                            <ArrowDown className={`h-4 w-4 ${sortKey === 'sharpe' ? 'text-primary' : 'opacity-40'}`} />
                            <span>Annualized Sharpe</span>
                          </button>
                          <InfoTooltip content="Risk-adjusted return metric : Sharpe ratio is the ratio of the average return to the standard deviation of the returns. Read more [here](https://en.wikipedia.org/wiki/Sharpe_ratio). Green indicates statistically significant positive performance, computed using 5% significance t-statistic using the number of bets placed." />
                        </div>
                        <div className="relative" ref={dropdownRef}>
                          <button
                            onClick={() => setDropdownOpen(!dropdownOpen)}
                            className="text-xs font-medium border border-border rounded-md px-2 py-1 bg-background text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors cursor-pointer flex items-center gap-1 min-w-[60px]"
                          >
                            <span>
                              {sharpeTimeHorizon === 'one_day' ? '1 Day' :
                               sharpeTimeHorizon === 'two_day' ? '2 Days' : '7 Days'}
                            </span>
                            <ChevronDown className={`h-3 w-3 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
                          </button>
                          {dropdownOpen && (
                            <div className="absolute top-full left-0 mt-1 w-full bg-background border border-border rounded-md overflow-hidden z-50">
                              <button
                                onClick={() => {
                                  setSharpeTimeHorizon('one_day')
                                  setDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                1 Day
                              </button>
                              <button
                                onClick={() => {
                                  setSharpeTimeHorizon('two_day')
                                  setDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                2 Days
                              </button>
                              <button
                                onClick={() => {
                                  setSharpeTimeHorizon('seven_day')
                                  setDropdownOpen(false)
                                }}
                                className="w-full text-left text-xs font-medium px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                              >
                                7 Days
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </th>
                    <th className="hidden md:table-cell text-center py-3 px-2 text-sm font-medium">
                      <span>Bets placed</span>
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
                        <td className="hidden md:table-cell py-4 px-4 text-center">
                          <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                        </td>
                        <td className="hidden md:table-cell py-4 px-2 text-center">
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-8 mx-auto"></div>
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
                              value={getReturnForHorizon(model.average_returns, returnsTimeHorizon)}
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
                        <td className="hidden md:table-cell py-4 px-4 text-center font-medium">
                          <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                            <span
                              className={
                                getSharpeSignificance(
                                  getSharpeForHorizon(model.sharpe, sharpeTimeHorizon),
                                  model.trades_count
                                ) === 'significant'
                                  ? 'text-green-600'
                                  : 'text-gray-500'
                              }
                            >
                              {`${getSharpeForHorizon(model.sharpe, sharpeTimeHorizon) >= 0 ? '+' : ''}${getSharpeForHorizon(model.sharpe, sharpeTimeHorizon).toFixed(3)}`}
                            </span>
                          </a>
                        </td>
                        <td className="hidden md:table-cell py-4 px-2 text-center text-sm text-muted-foreground">
                          <a href={`/models?selected=${encodeSlashes(model.model_id)}`} className="block">
                            {model.trades_count}
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
