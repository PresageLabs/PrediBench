import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { LeaderboardEntry } from '../api'

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

  const showMore = () => {
    setVisibleModels(prev => prev + 10)
  }

  return (
    <div>
      <div className="bg-card rounded-xl border border-border/30 overflow-hidden max-w-4xl mx-auto">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/30">
              <tr>
                <th className="text-left py-4 px-6 font-semibold">Model Name</th>
                <th className="text-right py-4 px-6 font-semibold">Total PnL</th>
                <th className="text-right py-4 px-6 font-semibold">Brier Score</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={index} className="border-t border-border/20">
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-4">
                        <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
                        <div className="h-4 bg-gray-200 rounded animate-pulse w-32"></div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16 ml-auto"></div>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16 ml-auto"></div>
                    </td>
                  </tr>
                ))
              ) : (
                leaderboard.slice(0, visibleModels).map((model, index) => (
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
                    <td className="py-4 px-6 text-right font-medium">
                      <a href={`/models?selected=${model.id}`} className="block">
                        <span className={model.final_cumulative_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          ${model.final_cumulative_pnl.toFixed(1)}
                        </span>
                      </a>
                    </td>
                    <td className="py-4 px-6 text-right font-medium">
                      <a href={`/models?selected=${model.id}`} className="block">
                        {model.accuracy ? (1 - model.accuracy).toFixed(3) : 'N/A'}
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
      {leaderboard.length > visibleModels && (
        <div className="text-center mt-6">
          <button
            onClick={showMore}
            className="inline-flex items-center space-x-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            <ChevronDown className="h-4 w-4" />
            <span>Show more</span>
          </button>
        </div>
      )}
    </div>
  )
}