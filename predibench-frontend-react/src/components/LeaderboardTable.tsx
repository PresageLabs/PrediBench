import { ArrowDown, ChevronDown } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { LeaderboardEntry } from '../api'
import { InfoTooltip } from './ui/info-tooltip'
import { RedirectButton } from './ui/redirect-button'

type SortKey = 'cumulative_profit' | 'brier_score'

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
  const [visibleModels, setVisibleModels] = useState(initialVisibleModels)
  const [sortKey, setSortKey] = useState<SortKey>('cumulative_profit')

  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      switch (sortKey) {
        case 'cumulative_profit':
          // Primary sort by PnL (higher first)
          const pnlDiff = b.final_cumulative_pnl - a.final_cumulative_pnl
          // If PnL is very close (within 0.01), use Brier score as tie-breaker
          if (Math.abs(pnlDiff) < 0.01) {
            return (1 - b.avg_brier_score) - (1 - a.avg_brier_score) // Higher Brier score wins tie
          }
          return pnlDiff
        case 'brier_score':
          // Primary sort by Brier score (higher transformed score first)
          const brierDiff = (1 - b.avg_brier_score) - (1 - a.avg_brier_score)
          // If Brier scores are very close (within 0.001), use PnL as tie-breaker
          if (Math.abs(brierDiff) < 0.001) {
            return b.final_cumulative_pnl - a.final_cumulative_pnl // Higher PnL wins tie
          }
          return brierDiff
        default:
          return 0
      }
    })
  }, [leaderboard, sortKey])

  const handleSort = (key: SortKey) => {
    setSortKey(key)
  }


  const showMore = () => {
    setVisibleModels(prev => prev + 10)
  }

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

      <div className="bg-card rounded-xl border border-border/30 overflow-hidden max-w-4xl mx-auto">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/30">
              <tr>
                <th className="text-left py-4 px-6 font-semibold">Model Name</th>
                <th className="text-center py-4 px-6 font-semibold">
                  <button
                    onClick={() => handleSort('cumulative_profit')}
                    className="flex items-center justify-center space-x-1 w-full hover:text-primary transition-colors"
                  >
                    <ArrowDown className={`h-4 w-4 ${sortKey === 'cumulative_profit' ? 'text-primary' : 'opacity-40'}`} />
                    <span>Cumulative Profit</span>
                    <InfoTooltip content="This is the PnL (Profit and Loss), or cumulative profit from all trades made by the model" />
                  </button>
                </th>
                <th className="text-center py-4 px-6 font-semibold">
                  <button
                    onClick={() => handleSort('brier_score')}
                    className="flex items-center justify-center space-x-1 w-full hover:text-primary transition-colors"
                    title="Brier Score - Higher values indicate better prediction accuracy (1 - original Brier score)"
                  >
                    <ArrowDown className={`h-4 w-4 ${sortKey === 'brier_score' ? 'text-primary' : 'opacity-40'}`} />
                    <span>Brier Score</span>
                    <InfoTooltip content="A measure of prediction accuracy. Lower values indicate better calibration - how well the model's confidence matches actual outcomes (0 = perfect, 1 = worst)" />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && leaderboard.length === 0 ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index} className="border-t border-border/20">
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-4">
                        <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
                        <div className="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-center">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                    </td>
                    <td className="py-4 px-6 text-center">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16 mx-auto"></div>
                    </td>
                  </tr>
                ))
              ) : (
                sortedLeaderboard.slice(0, visibleModels).map((model, index) => (
                  <tr key={model.id} className="border-t border-border/20 hover:bg-muted/20 transition-colors">
                    <td className="py-4 px-6">
                      <a
                        href={`/models?selected=${model.id}`}
                        className="flex items-center space-x-4"
                      >
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${index === 0 ? 'bg-gradient-to-br from-yellow-100 to-yellow-50 text-yellow-800 shadow-md shadow-yellow-200/50' :
                          index === 1 ? 'bg-gradient-to-br from-slate-100 to-slate-50 text-slate-800 shadow-md shadow-slate-200/50' :
                            index === 2 ? 'bg-gradient-to-br from-amber-100 to-amber-50 text-amber-800 shadow-md shadow-amber-200/50' :
                              'bg-gradient-to-br from-muted to-muted/70 text-muted-foreground shadow-sm'
                          }`}>
                          {index + 1}
                        </div>
                        <span className="font-medium">
                          {model.model}
                        </span>
                      </a>
                    </td>
                    <td className="py-4 px-6 text-center font-medium">
                      <a href={`/models?selected=${model.id}`} className="block">
                        <span className={model.final_cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          ${model.final_cumulative_pnl.toFixed(1)}
                        </span>
                      </a>
                    </td>
                    <td className="py-4 px-6 text-center font-medium">
                      <a href={`/models?selected=${model.id}`} className="block">
                        {model.avg_brier_score ? `${((1 - model.avg_brier_score) * 100).toFixed(1)}%` : 'N/A'}
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Show More Button */}
      {sortedLeaderboard.length > visibleModels && (
        <div className="text-center mt-6">
          <RedirectButton
            onClick={showMore}
            icon={<ChevronDown className="h-4 w-4" />}
          >
            Show more
          </RedirectButton>
        </div>
      )}
    </div>
  )
}