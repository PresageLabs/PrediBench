import type { LeaderboardEntry } from '../api'
import { LeaderboardTable } from './LeaderboardTable'
import { getChartColor } from './ui/chart-colors'
import { PortfolioValueToolTip } from './ui/info-tooltip'
import { RedirectButton } from './ui/redirect-button'
import { VisxLineChart } from './ui/visx-line-chart'

const START_DATE = new Date('2025-08-25')

interface LeaderboardPageProps {
  leaderboard: LeaderboardEntry[]
  loading?: boolean
}

export function LeaderboardPage({ leaderboard, loading = false }: LeaderboardPageProps) {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Title and Subtitle */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">🏆 PrediBench Leaderboard</h1>
      </div>

      {/* Leaderboard Table */}
      <div className="mb-16">
        <LeaderboardTable
          leaderboard={leaderboard}
          loading={loading}
        />
      </div>

      {/* Horizontal Separator */}
      <div className="w-full h-px bg-border mb-16"></div>

      {/* Portfolio Value Chart */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8 flex items-center justify-center">
          Portfolio Value
          <PortfolioValueToolTip />
        </h2>
        <div className="bg-card rounded-xl border border-border/30 p-6">
          <div className="h-[800px]">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                  <div className="text-sm text-muted-foreground">Loading Profit chart...</div>
                </div>
              </div>
            ) : (
              <VisxLineChart
                height={800}
                margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                series={leaderboard.map((model, index) => ({
                  dataKey: model.model_name,
                  data: (model.position_values_history || [])
                    .filter(point => new Date(point.date) >= START_DATE)
                    .map(point => ({
                      x: point.date,
                      y: point.value
                    })),
                  stroke: getChartColor(index),
                  name: model.model_name
                }))}
                yDomain={(() => {
                  const allValues = leaderboard.flatMap(model =>
                    (model.position_values_history || [])
                      .filter(point => new Date(point.date) >= START_DATE)
                      .map(point => point.value)
                  )
                  if (allValues.length === 0) return [0, 1]
                  const min = Math.min(...allValues)
                  const max = Math.max(...allValues)
                  const range = max - min
                  const padding = Math.max(range * 0.25, 0.02)
                  return [min - padding, max + padding]
                })()
                }
              />
            )}
          </div>
        </div>
      </div>

      {/* Link to full benchmark details */}
      <div>
        <div className="max-w-4xl mx-auto">
          <div className="bg-card rounded-xl border border-border/30 p-8 relative z-10">
            <div className="text-center">
              <RedirectButton href="/#intro">
                More detail on the benchmark
              </RedirectButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
