import Giscus from '@giscus/react'
import * as Select from '@radix-ui/react-select'
import { format as formatDate } from 'date-fns'
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { LeaderboardEntry, ModelInvestmentDecision, ModelPerformance } from '../api'
import { apiService } from '../api'
import { useTheme } from '../contexts/ThemeContext'
import { decodeSlashes, encodeSlashes } from '../lib/utils'
import { getChartColor } from './ui/chart-colors'
import { DecisionAnnotation } from './ui/DecisionAnnotation'
import { EventDecisionThumbnail } from './ui/EventDecisionThumbnail'
import { BrierScoreInfoTooltip, PnLTooltip } from './ui/info-tooltip'
// import { ProfitDisplay } from './ui/profit-display'
import { VisxLineChart } from './ui/visx-line-chart'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}


export function ModelsPage({ leaderboard }: ModelsPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme } = useTheme()
  const [selectedModelId, setSelectedModelId] = useState<string>('')
  const [modelDecisions, setModelDecisions] = useState<ModelInvestmentDecision[]>([])
  // const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [calendarDate, setCalendarDate] = useState(new Date())
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance>()
  const [predictionDates, setPredictionDates] = useState<string[]>([])
  const [cutoffIndex, setCutoffIndex] = useState<number>(0)

  // Event details modal state is managed within EventDecisionModal now

  // formatLongDate moved into EventDecisionModal

  const selectedModelData = leaderboard.find(m => m.model_id === selectedModelId)

  // Sort models by descending Average Return (7 days) for dropdown ordering and default selection
  const sortedByAverageReturns = useMemo(() => {
    return [...leaderboard].sort((a, b) => b.average_returns.seven_day_return - a.average_returns.seven_day_return)
  }, [leaderboard])

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search)
    const selectedFromUrl = urlParams.get('selected')
    const decodedSelectedFromUrl = selectedFromUrl ? decodeSlashes(selectedFromUrl) : null

    if (decodedSelectedFromUrl && leaderboard.find(m => m.model_id === decodedSelectedFromUrl)) {
      setSelectedModelId(decodedSelectedFromUrl)
    } else if (!selectedModelId && sortedByAverageReturns.length > 0) {
      setSelectedModelId(sortedByAverageReturns[0].model_id)
    }
  }, [leaderboard, sortedByAverageReturns, selectedModelId, location.search])

  // selectedModel is already the canonical model_id from the leaderboard

  useEffect(() => {
    if (selectedModelId) {
      apiService.getModelResultsById(selectedModelId)
        .then(setModelDecisions)
        .catch(console.error)
    }
  }, [selectedModelId])

  // Auto-select the latest decision date when modelDecisions are loaded
  useEffect(() => {
    if (modelDecisions.length > 0 && !selectedDate) {
      const sortedDates = modelDecisions
        .map(decision => decision.target_date)
        .sort((a, b) => b.localeCompare(a)) // Sort descending to get latest first

      if (sortedDates.length > 0) {
        setSelectedDate(sortedDates[0])
      }
    }
  }, [modelDecisions, selectedDate])

  // Always show calendar at current month - no override



  const handleModelSelect = (modelId: string) => {
    setSelectedModelId(modelId)
    navigate(`/models?selected=${encodeSlashes(modelId)}`, { replace: true })
  }

  const handleEventClick = (eventDecision: any, decisionDate: string, decisionDatetime: string) => {
    const searchParams = new URLSearchParams({
      source: 'model',
      decisionDatetime: decisionDatetime,
      modelName: selectedModelData?.model_name || selectedModelId,
      eventTitle: eventDecision.event_title,
      decisionDatesForEvent: modelDecisions
        .filter(md => md.event_investment_decisions.some(ed => ed.event_id === eventDecision.event_id))
        .map(md => md.target_date)
        .sort()
        .join(',')
    })
    navigate(`/decision/${encodeSlashes(selectedModelId)}/${eventDecision.event_id}/${decisionDate}?${searchParams.toString()}`)
  }

  // EventDecisionModal computes prices/returns internally

  const navigateCalendar = (direction: 'prev' | 'next') => {
    const newDate = new Date(calendarDate)
    if (direction === 'prev') {
      newDate.setMonth(newDate.getMonth() - 1)
    } else {
      newDate.setMonth(newDate.getMonth() + 1)
    }
    setCalendarDate(newDate)
  }

  const generateCalendarDays = () => {
    // Format a Date to YYYY-MM-DD using LOCAL time to avoid timezone shifts
    const formatLocalYMD = (d: Date) => {
      const y = d.getFullYear()
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${y}-${m}-${day}`
    }

    const year = calendarDate.getFullYear()
    const month = calendarDate.getMonth()

    // First day of the month and last day of the month
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)

    // Start from the first Sunday of the week containing the first day
    const startDate = new Date(firstDay)
    startDate.setDate(startDate.getDate() - startDate.getDay())

    // End at the last Saturday of the week containing the last day
    const endDate = new Date(lastDay)
    endDate.setDate(endDate.getDate() + (6 - endDate.getDay()))

    const days = []
    const current = new Date(startDate)

    while (current <= endDate) {
      const dateStr = formatLocalYMD(current)
      const hasDecision = modelDecisions.some(d => d.target_date === dateStr)
      const decisionCount = hasDecision ?
        modelDecisions.find(d => d.target_date === dateStr)?.event_investment_decisions.length || 0 : 0

      const isCurrentMonth = current.getMonth() === month
      const isToday = formatLocalYMD(current) === formatLocalYMD(new Date())

      days.push({
        date: new Date(current),
        dateStr,
        hasDecision,
        decisionCount,
        isSelected: selectedDate === dateStr,
        isCurrentMonth,
        isToday
      })
      current.setDate(current.getDate() + 1)
    }

    return days
  }

  // Fetch model performance
  useEffect(() => {
    let cancelled = false
    if (selectedModelId) {
      apiService.getPerformanceByModel(selectedModelId)
        .then(perf => { if (!cancelled) setModelPerformance(perf) })
        .catch(console.error)
    }
    return () => { cancelled = true }
  }, [selectedModelId])

  // Fetch prediction dates for cutoff slider from modelPerformance
  useEffect(() => {
    if (modelPerformance?.trades_dates) {
      setPredictionDates(modelPerformance.trades_dates.sort((a, b) => a.localeCompare(b)))
    }
  }, [modelPerformance])

  // Removed event-based series metadata; cumulative series is used instead

  const cutoffDate = useMemo(() => {
    if (!predictionDates.length) return '0000-01-01'
    const maxIndex = Math.max(0, predictionDates.length - 2)
    const idx = Math.max(0, Math.min(cutoffIndex, maxIndex))
    return predictionDates[idx]
  }, [predictionDates, cutoffIndex])

  // Daily returns series using daily_returns from ModelPerformance
  const profitSeries = useMemo(() => {
    if (!modelPerformance || !modelPerformance.daily_returns) return []

    const dailyReturns = modelPerformance.daily_returns
    console.log('Daily returns data:', dailyReturns, 'cutoffDate:', cutoffDate)

    // Filter daily returns from cutoff date onwards
    const filteredReturns = dailyReturns
      .filter(point => point.date >= cutoffDate)
      .sort((a, b) => a.date.localeCompare(b.date))

    console.log('Filtered returns:', filteredReturns)

    return [{
      dataKey: `model_${selectedModelId}_daily_returns`,
      data: filteredReturns.map(p => ({ date: p.date, value: p.value })), // Use actual dollar returns
      stroke: getChartColor(0),
      name: 'Daily Returns'
    }]
  }, [modelPerformance, cutoffDate, selectedModelId])

  // Generate additional annotations for decision points
  const additionalAnnotations = useMemo(() => {
    if (!modelDecisions.length || !modelPerformance) return {}

    const annotations: Record<string, { content: React.ReactNode }> = {}

    // Sort decisions by date to calculate returns properly
    const sortedDecisions = [...modelDecisions].sort((a, b) => a.target_date.localeCompare(b.target_date))

    sortedDecisions.forEach((decision, index) => {
      const nextDecision = index < sortedDecisions.length - 1 ? sortedDecisions[index + 1] : undefined

      annotations[decision.target_date] = {
        content: (
          <DecisionAnnotation
            decision={decision}
            nextDecision={nextDecision}
            allDecisions={sortedDecisions}
            onEventClick={handleEventClick}
          />
        )
      }
    })

    return annotations
  }, [modelDecisions, modelPerformance])

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header with title and model selection */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Model performance</h1>

        <Select.Root value={selectedModelId} onValueChange={handleModelSelect}>
          <Select.Trigger className="inline-flex items-center justify-between gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 min-w-[100px]">
            <Select.Value placeholder="Select a model">
              {selectedModelData?.model_name || 'Select a model'}
            </Select.Value>
            <Select.Icon>
              <ChevronDown size={16} />
            </Select.Icon>
          </Select.Trigger>

          <Select.Portal>
            <Select.Content
              className="overflow-hidden rounded-lg border border-border bg-popover shadow-lg z-50"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1 max-h-[70vh] overflow-y-auto">
                {sortedByAverageReturns.map((model, index) => (
                  <Select.Item
                    key={model.model_id}
                    value={model.model_id}
                    className="relative flex cursor-pointer items-center rounded-md px-3 py-2 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none data-[state=checked]:bg-accent data-[state=checked]:text-accent-foreground"
                  >
                    <Select.ItemText>
                      <div className="flex items-center space-x-3">
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${index === 0 ? 'bg-gradient-to-br from-yellow-100 to-yellow-50 text-yellow-800 dark:from-yellow-900/20 dark:to-yellow-800/20 dark:text-yellow-300' :
                          index === 1 ? 'bg-gradient-to-br from-slate-100 to-slate-50 text-slate-800 dark:from-slate-900/20 dark:to-slate-800/20 dark:text-slate-300' :
                            index === 2 ? 'bg-gradient-to-br from-amber-100 to-amber-50 text-amber-800 dark:from-amber-900/20 dark:to-amber-800/20 dark:text-amber-300' :
                              'bg-gradient-to-br from-gray-100 to-gray-50 text-gray-800 dark:from-gray-900/20 dark:to-gray-800/20 dark:text-gray-300'
                          }`}>
                          {index + 1}
                        </div>
                        <div>
                          <div className="font-medium">{model.model_name}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            Avg Return (7d): {(model.average_returns.seven_day_return * 100).toFixed(1)}% | Brier score: {model.final_brier_score.toFixed(3)}
                          </div>
                        </div>
                      </div>
                    </Select.ItemText>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
      </div>

      {/* Model Card Display */}
      {selectedModelData && (
        <div className="space-y-8">
          <div className="md:p-6 md:bg-card md:rounded-xl md:border md:border-border">
            {/* Model Info - Always visible */}
            <div className="mb-8 border-b border-border pb-6">
              <h2 className="text-xl font-semibold mb-4">{selectedModelData.model_name}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Final Profit:
                    <PnLTooltip />
                  </div>
                  <div className="font-medium">{(selectedModelData.final_profit * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Brier score:
                    <BrierScoreInfoTooltip />
                  </div>
                  <div className="font-medium">{selectedModelData.final_brier_score.toFixed(3)}</div>
                </div >
                <div>
                  <span className="text-muted-foreground">Bets taken:</span>
                  <div className="font-medium">{selectedModelData.trades_count}</div>
                </div>
              </div >
            </div >

            {/* Daily Returns Chart */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                Daily Returns
                <PnLTooltip />
              </h3>
              {/* Cutoff Slider (below title, above graph) */}
              <div className="mb-0 flex items-center justify-start gap-3">
                <label className="text-xs text-muted-foreground leading-none self-center">First decision cutoff date:</label>
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, predictionDates.length - 2)}
                  value={Math.min(cutoffIndex, Math.max(0, predictionDates.length - 2))}
                  onChange={(e) => setCutoffIndex(parseInt(e.target.value))}
                  className="w-[100px] h-1 accent-primary"
                />
                <div className="text-xs tabular-nums whitespace-nowrap min-w-[9ch] leading-none self-center">
                  {predictionDates.length ? formatDate(new Date(cutoffDate), 'd MMMM') : '—'}
                </div>
              </div>
              <div className="h-auto sm:h-[500px]">
                <VisxLineChart
                  height={500}
                  margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                  series={profitSeries}
                  xDomain={(() => {
                    const allDates = profitSeries.flatMap(s => s.data.map(p => new Date(p.date)))
                    if (allDates.length === 0) return undefined
                    const minDate = new Date(cutoffDate)
                    const maxDate = new Date(Math.max(...allDates.map(d => d.getTime())))
                    return [minDate, maxDate]
                  })()}
                  yDomain={(() => {
                    const values = profitSeries.flatMap(s => s.data.map(p => p.value))
                    if (values.length === 0) return [0, 1]
                    const min = Math.min(...values)
                    const max = Math.max(...values)
                    if (!isFinite(min) || !isFinite(max)) return [0, 1]
                    const range = max - min
                    const padding = Math.max(range * 0.25, 0.02)
                    return [min - padding, max + padding]
                  })()}
                  additionalAnnotations={additionalAnnotations}
                />
              </div>
            </div>

            {/* Decisions through time */}
            <div className="pt-6 border-t border-border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Decisions through time</h3>
              </div>
              {modelDecisions.length > 0 && (
                <div className="mb-6 p-4 bg-card rounded-lg border max-w-xl mx-auto">
                  {/* Calendar Navigation */}
                  <div className="flex items-center justify-between mb-4">
                    <button
                      onClick={() => navigateCalendar('prev')}
                      className="p-2 rounded-lg hover:bg-accent transition-colors"
                      title="Previous month"
                    >
                      <ChevronLeft size={16} />
                    </button>

                    <h4 className="font-medium text-lg">
                      {calendarDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                    </h4>

                    {(() => {
                      const today = new Date()
                      const isAtCurrentMonth =
                        calendarDate.getFullYear() === today.getFullYear() &&
                        calendarDate.getMonth() === today.getMonth()
                      return (
                        <button
                          onClick={() => !isAtCurrentMonth && navigateCalendar('next')}
                          className={`p-2 rounded-lg transition-colors ${isAtCurrentMonth ? 'opacity-50 cursor-not-allowed' : 'hover:bg-accent'
                            }`}
                          title="Next month"
                          disabled={isAtCurrentMonth}
                        >
                          <ChevronRight size={16} />
                        </button>
                      )
                    })()}
                  </div>

                  {/* Calendar Grid */}
                  <div className="grid grid-cols-7 gap-1 text-center">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                      <div key={day} className="p-2 text-xs font-medium text-muted-foreground">
                        {day}
                      </div>
                    ))}
                    {generateCalendarDays().map((day, index) => (
                      <div key={index} className="relative">
                        <button
                          onClick={() => day.hasDecision && setSelectedDate(day.dateStr)}
                          className={`w-full p-2 text-xs rounded transition-colors relative ${!day.isCurrentMonth
                            ? 'text-muted-foreground/30 cursor-default'
                            : day.hasDecision
                              ? day.isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-accent hover:bg-accent/80 cursor-pointer'
                              : 'text-muted-foreground cursor-default'
                            } ${day.isToday ? 'ring-2 ring-white' : ''}`}
                          disabled={!day.hasDecision || !day.isCurrentMonth}
                        >
                          {day.date.getDate()}
                          {day.hasDecision && day.isCurrentMonth && (
                            <div className="absolute -top-1 -right-1 w-4 h-4 bg-primary text-primary-foreground text-xs rounded-full flex items-center justify-center">
                              {day.decisionCount}
                            </div>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {modelDecisions.length > 0 && selectedDate && (
                <div className="md:p-4 md:bg-card md:rounded-lg md:border md:max-w-2xl md:mx-auto">
                  <h4 className="font-medium mb-3">Decisions for {selectedDate}:</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {modelDecisions
                      .find(d => d.target_date === selectedDate)
                      ?.event_investment_decisions.map((eventDecision, index) => {
                        const top = [...eventDecision.market_investment_decisions].sort((a, b) => Math.abs(b.decision.bet) - Math.abs(a.decision.bet))[0]
                        const topBet = top?.decision.bet ?? null
                        const topQuestion = top?.market_question || 'Top market'
                        return (
                          <EventDecisionThumbnail
                            key={index}
                            title={eventDecision.event_title}
                            topMarketName={topQuestion}
                            topBet={topBet}
                            decisionsCount={eventDecision.market_investment_decisions.length}
                            onClick={() => {
                              const decision = modelDecisions.find(d => d.target_date === selectedDate)
                              handleEventClick(eventDecision, selectedDate, decision?.decision_datetime || '')
                            }}
                          />
                        )
                      })}
                  </div>
                </div>
              )}
            </div>
          </div >
        </div >
      )
      }

      {/* Model Discussion - only show when a model is selected */}
      {selectedModelId && selectedModelData && (
        <div className="mt-12">
          <h3 className="text-xl font-semibold mb-6">Leave feedback for {selectedModelData.model_name}</h3>
          <Giscus
            id="model-comments"
            repo="clairvoyance-tech/predibench"
            repoId="R_kgDOPTwANQ"
            category="Ideas"
            categoryId="DIC_kwDOPTwANc4Cvk2C"
            mapping="specific"
            term={`Model: ${selectedModelData.model_name}`}
            strict="0"
            reactionsEnabled="0"
            emitMetadata="0"
            inputPosition="top"
            theme={theme === 'dark' ? 'dark_tritanopia' : 'light_tritanopia'}
            lang="en"
            loading="lazy"
          />
        </div>
      )}

    </div >
  )
}
