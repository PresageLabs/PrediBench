import { useEffect, useMemo, useState } from 'react'
import type { LeaderboardEntry, ModelInvestmentDecision } from '../api'
import { apiService } from '../api'
import { LeaderboardTable } from './LeaderboardTable'
import { getChartColor } from './ui/chart-colors'
import { PnLTooltip } from './ui/info-tooltip'
import { RedirectButton } from './ui/redirect-button'
import { VisxLineChart } from './ui/visx-line-chart'
import { calculatePortfolioFromDecisions } from '../utils/stitching'
import { ErrorBoundary } from './ErrorBoundary'

// Fallback: if prediction dates fail to load, show everything
const DEFAULT_CUTOFF = '0000-01-01'

interface LeaderboardPageProps {
  leaderboard: LeaderboardEntry[]
  loading?: boolean
}

export function LeaderboardPage({ leaderboard, loading = false }: LeaderboardPageProps) {
  const [predictionDates, setPredictionDates] = useState<string[]>([])
  const [allDecisions, setAllDecisions] = useState<ModelInvestmentDecision[] | null>(null)
  const [cutoffIndex, setCutoffIndex] = useState<number>(0)

  useEffect(() => {
    let cancelled = false
    apiService.getPredictionDates()
      .then(dates => { if (!cancelled) setPredictionDates(dates.sort((a, b) => a.localeCompare(b))) })
      .catch(() => setPredictionDates([]))
    apiService.getModelResults()
      .then(res => { if (!cancelled) setAllDecisions(res) })
      .catch(() => setAllDecisions([]))
    return () => { cancelled = true }
  }, [])

  const cutoffDate = useMemo(() => {
    if (!predictionDates.length) return DEFAULT_CUTOFF
    const idx = Math.max(0, Math.min(cutoffIndex, predictionDates.length - 1))
    return predictionDates[idx]
  }, [predictionDates, cutoffIndex])

  const stitchedSeries = useMemo(() => {
    if (!allDecisions) return []

    const byModel: Record<string, ModelInvestmentDecision[]> = {}
    for (const d of allDecisions) {
      (byModel[d.model_id] ||= []).push(d)
    }

    return leaderboard.map((model, index) => {
      const decisions = byModel[model.model_id] || []
      const stitched = calculatePortfolioFromDecisions(decisions, cutoffDate)
      return {
        dataKey: model.model_id,
        data: stitched.map(p => ({ date: p.date, value: p.value })),
        stroke: getChartColor(index),
        name: model.model_name,
      }
    })
  }, [allDecisions, leaderboard, cutoffDate])

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

      {/* Cutoff Slider */}
      <div className="mb-6 max-w-2xl mx-auto">
        <label className="block text-sm text-muted-foreground mb-2">First decision cutoff date</label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={0}
            max={Math.max(0, predictionDates.length - 1)}
            value={Math.min(cutoffIndex, Math.max(0, predictionDates.length - 1))}
            onChange={(e) => setCutoffIndex(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="text-sm tabular-nums min-w-[7ch] text-right">
            {predictionDates.length ? cutoffDate : '—'}
          </div>
        </div>
      </div>

      {/* Portfolio Increase Chart */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8 flex items-center justify-center">
          Portfolio Increase
          <PnLTooltip />
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
              <ErrorBoundary>
                <VisxLineChart
                  height={800}
                  margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                  series={stitchedSeries}
                  xDomain={(() => {
                    try {
                      const allDates = stitchedSeries.flatMap(s => s.data.map(p => new Date(p.date)))
                      if (allDates.length === 0) return undefined
                      const minDate = new Date(cutoffDate)
                      const maxDate = new Date(Math.max(...allDates.map(d => d.getTime())))
                      return [minDate, maxDate]
                    } catch (error) {
                      console.error('Error calculating xDomain:', error)
                      return undefined
                    }
                  })()}
                  yDomain={(() => {
                    try {
                      console.log('Debug: stitchedSeries length:', stitchedSeries.length)
                      console.log('Debug: stitchedSeries sample:', stitchedSeries[0])
                      const allValues = stitchedSeries.flatMap(s => s.data.map(p => p.value))
                      if (allValues.length === 0) return [0, 1]
                      const min = Math.min(...allValues)
                      const max = Math.max(...allValues)
                      const range = max - min
                      const padding = Math.max(range * 0.25, 0.02)
                      return [min - padding, max + padding]
                    } catch (error) {
                      console.error('Error calculating yDomain:', error)
                      return [0, 1]
                    }
                  })()}
                />
              </ErrorBoundary>
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
