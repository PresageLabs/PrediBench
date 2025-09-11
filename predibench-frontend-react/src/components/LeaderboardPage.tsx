import type { LeaderboardEntry } from '../api'
import { LeaderboardTable } from './LeaderboardTable'
import { getChartColor } from './ui/chart-colors'
import { BrierScoreInfoTooltip, CumulativeProfitInfoTooltip } from './ui/info-tooltip'
import { RedirectButton } from './ui/redirect-button'
import { VisxLineChart } from './ui/visx-line-chart'

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

      {/* Profit Evolution Chart */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8 flex items-center justify-center">
          Profit Evolution
          <CumulativeProfitInfoTooltip />
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
                  dataKey: model.model,
                  data: (model.pnl_history || []).map(point => ({
                    x: point.date,
                    y: point.value
                  })),
                  stroke: getChartColor(index),
                  name: model.model
                }))}
                yDomain={(() => {
                  const allValues = leaderboard.flatMap(model =>
                    (model.pnl_history || []).map(point => point.value)
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

      {/* Methodology Section */}
      <div>
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold">Methodology</h2>
        </div>
        <div className="max-w-4xl mx-auto">
          <div className="bg-card rounded-xl border border-border/30 p-8">
            <div className="prose prose-gray max-w-none">
              <p className="text-muted-foreground mb-4">
                PrediBench evaluates language models through their ability to make profitable predictions in real market scenarios.
                Our comprehensive methodology ensures fair and accurate assessment of model performance across multiple dimensions.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
                <div>
                  <h3 className="text-lg font-semibold mb-3">Evaluation Metrics</h3>
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li className="flex items-center">
                      • <strong>Cumulative Profit</strong>: Cumulative profit/loss from all trades
                      <CumulativeProfitInfoTooltip />
                    </li>
                    <li className="flex items-center">
                      • <strong>Brier Score</strong>: Measure of prediction accuracy
                      <BrierScoreInfoTooltip />
                    </li>
                    <li>• <strong>Risk-adjusted Returns</strong>: Performance relative to volatility</li>
                    <li>• <strong>Calibration</strong>: How well probabilities match outcomes</li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-3">Trading Framework</h3>
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li>• <strong>Market Selection</strong>: Diverse prediction markets</li>
                    <li>• <strong>Position Sizing</strong>: Standardized bet sizing rules</li>
                    <li>• <strong>Time Horizon</strong>: Various prediction timeframes</li>
                    <li>• <strong>Transaction Costs</strong>: Realistic market conditions</li>
                  </ul>
                </div>
              </div>

              <div className="text-center">
                <RedirectButton href="/#intro">
                  More detail on the benchmark
                </RedirectButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
