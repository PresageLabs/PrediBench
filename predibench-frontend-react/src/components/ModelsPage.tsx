import * as Select from '@radix-ui/react-select'
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { LeaderboardEntry, ModelInvestmentDecision, ModelPerformance } from '../api'
import { apiService } from '../api'
import { getChartColor } from './ui/chart-colors'
import { DecisionAnnotation } from './ui/DecisionAnnotation'
import { EventDecisionModal } from './ui/EventDecisionModal'
import { EventDecisionThumbnail } from './ui/EventDecisionThumbnail'
import { BrierScoreInfoTooltip, CumulativeProfitInfoTooltip } from './ui/info-tooltip'
// import { ProfitDisplay } from './ui/profit-display'
import { VisxLineChart } from './ui/visx-line-chart'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}


export function ModelsPage({ leaderboard }: ModelsPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [selectedModel, setSelectedModel] = useState<string>(leaderboard[0]?.id || '')
  const [modelDecisions, setModelDecisions] = useState<ModelInvestmentDecision[]>([])
  // const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [showEventPopup, setShowEventPopup] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<{
    eventDecision: any;
    decisionDate: string;
    decisionDatetime: string;
  } | null>(null)
  const [calendarDate, setCalendarDate] = useState(new Date())
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance | null>(null)

  // Event details modal state is managed within EventDecisionModal now

  // formatLongDate moved into EventDecisionModal

  const selectedModelData = leaderboard.find(m => m.id === selectedModel)

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search)
    const selectedFromUrl = urlParams.get('selected')

    if (selectedFromUrl && leaderboard.find(m => m.id === selectedFromUrl)) {
      setSelectedModel(selectedFromUrl)
    } else if (!selectedModel && leaderboard.length > 0) {
      setSelectedModel(leaderboard[0].id)
    }
  }, [leaderboard, selectedModel, location.search])

  // Map model_name -> model_id using performance endpoint once
  const [nameToIdMap, setNameToIdMap] = useState<Record<string, string>>({})
  useEffect(() => {
    let cancelled = false
    apiService.getPerformance('day')
      .then(perfs => {
        if (cancelled) return
        const map: Record<string, string> = {}
        perfs.forEach(p => {
          map[p.model_name] = p.model_id
          map[p.model_id] = p.model_id // allow id passthrough
        })
        setNameToIdMap(map)
      })
      .catch(console.error)
    return () => { cancelled = true }
  }, [])

  // Resolve the backend model_id to query
  const resolvedModelId = useMemo(() => nameToIdMap[selectedModel] || selectedModel, [nameToIdMap, selectedModel])
  const mapReady = useMemo(() => Object.keys(nameToIdMap).length > 0, [nameToIdMap])

  useEffect(() => {
    if (resolvedModelId && mapReady) {
      apiService.getModelResultsById(resolvedModelId)
        .then(setModelDecisions)
        .catch(console.error)
    }
  }, [resolvedModelId, mapReady])

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
    setSelectedModel(modelId)
    navigate(`/models?selected=${modelId}`, { replace: true })
  }

  const handleEventClick = (eventDecision: any, decisionDate: string, decisionDatetime: string) => {
    setSelectedEvent({ eventDecision, decisionDate, decisionDatetime })
    setShowEventPopup(true)
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

  // Fetch model performance for event-level PnL series
  useEffect(() => {
    let cancelled = false
    if (resolvedModelId && mapReady) {
      apiService.getPerformanceByModel(resolvedModelId, 'day')
        .then(perf => { if (!cancelled) setModelPerformance(perf) })
        .catch(console.error)
    }
    return () => { cancelled = true }
  }, [resolvedModelId, mapReady])

  // Removed event-based series metadata; cumulative series is used instead

  // Cumulative Profit series since the beginning for the selected model
  const cumulativeSeries = useMemo(() => {
    if (!modelPerformance) return [] as { dataKey: string; data: { x: string; y: number }[]; stroke: string; name?: string }[]
    const data = (modelPerformance.cummulative_pnl || []).map(pt => ({ x: pt.date, y: pt.value }))
    return [
      {
        dataKey: `model_${modelPerformance.model_id}_cum`,
        data,
        stroke: getChartColor(0),
        name: 'Cumulative Profit'
      }
    ]
  }, [modelPerformance])

  // Generate additional annotations for decision points
  const additionalAnnotations = useMemo(() => {
    if (!modelDecisions.length || !modelPerformance) return {}

    const annotations: Record<string, { content: React.ReactNode }> = {}

    // Sort decisions by date to calculate returns properly
    const sortedDecisions = [...modelDecisions].sort((a, b) => a.target_date.localeCompare(b.target_date))

    // Get cumulative data for period profit calculations
    const cumulativeData = (modelPerformance.cummulative_pnl || []).map(pt => ({ x: pt.date, y: pt.value }))

    sortedDecisions.forEach((decision, index) => {
      const nextDecision = index < sortedDecisions.length - 1 ? sortedDecisions[index + 1] : undefined

      annotations[decision.target_date] = {
        content: (
          <DecisionAnnotation
            decision={decision}
            nextDecision={nextDecision}
            allDecisions={sortedDecisions}
            cumulativeData={cumulativeData}
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

        <Select.Root value={selectedModel} onValueChange={handleModelSelect}>
          <Select.Trigger className="inline-flex items-center justify-between gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 min-w-[300px]">
            <Select.Value placeholder="Select a model">
              {selectedModelData?.model || 'Select a model'}
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
                {leaderboard.map((model, index) => (
                  <Select.Item
                    key={model.id}
                    value={model.id}
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
                          <div className="font-medium">{model.model}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            Profit: {(model.final_cumulative_pnl * 100).toFixed(1)}% | Brier score: {model.avg_brier_score.toFixed(3)}
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
              <h2 className="text-xl font-semibold mb-4">{selectedModelData.model}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Final Profit:
                    <CumulativeProfitInfoTooltip />
                  </div>
                  <div className="font-medium">{selectedModelData.final_cumulative_pnl.toFixed(1)}</div>
                </div>
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Brier score:
                    <BrierScoreInfoTooltip />
                  </div>
                  <div className="font-medium">{selectedModelData.avg_brier_score.toFixed(3)}</div>
                </div >
                <div>
                  <span className="text-muted-foreground">Bets taken:</span>
                  <div className="font-medium">{selectedModelData.trades}</div>
                </div>
              </div >
            </div >

            {/* Cumulative Profit Chart */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                Cumulative Profit
                <CumulativeProfitInfoTooltip />
              </h3>
              <div className="h-[500px]">
                {cumulativeSeries.length === 0 ? (
                  <div className="h-full bg-muted/20 rounded-lg flex items-center justify-center">
                    <div className="text-sm text-muted-foreground">No event profit data available.</div>
                  </div>
                ) : (
                  <VisxLineChart
                    height={500}
                    margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                    series={cumulativeSeries}
                    additionalAnnotations={additionalAnnotations}
                  />
                )}
              </div>
            </div>

            {/* Decisions through time */}
            <div>
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

              <div className="bg-muted/10 rounded-lg p-6">
                {modelDecisions.length > 0 && selectedDate && (
                  <div className="p-4 bg-card rounded-lg border max-w-2xl mx-auto">
                    <h4 className="font-medium mb-3">Decisions for {selectedDate}:</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {modelDecisions
                        .find(d => d.target_date === selectedDate)
                        ?.event_investment_decisions.map((eventDecision, index) => {
                          const top = [...eventDecision.market_investment_decisions].sort((a, b) => Math.abs(b.model_decision.bet) - Math.abs(a.model_decision.bet))[0]
                          const topBet = top?.model_decision.bet ?? null
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
            </div>
          </div >
        </div >
      )
      }

      {/* Event Details Popup - unified modal */}
      {showEventPopup && selectedEvent && (
        <EventDecisionModal
          isOpen={showEventPopup}
          onClose={() => setShowEventPopup(false)}
          eventDecision={selectedEvent.eventDecision}
          decisionDate={selectedEvent.decisionDate}
          decisionDatetime={selectedEvent.decisionDatetime}
          modelName={selectedModelData?.model}
          modelId={selectedModelData?.id}
          eventTitle={selectedEvent.eventDecision?.event_title}
          decisionDatesForEvent={modelDecisions
            .filter(d => d.event_investment_decisions.some(ed => ed.event_id === selectedEvent.eventDecision.event_id))
            .map(d => d.target_date)
            .sort((a, b) => a.localeCompare(b))}
        />
      )}
    </div >
  )
}
