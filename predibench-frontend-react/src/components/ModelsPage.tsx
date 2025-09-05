import * as Select from '@radix-ui/react-select'
import { ChevronDown, ChevronLeft, ChevronRight, X, Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { LeaderboardEntry, ModelInvestmentDecision } from '../api'
import { apiService } from '../api'
import { getChartColor } from './ui/chart-colors'
import { InfoTooltip } from './ui/info-tooltip'
import { VisxLineChart } from './ui/visx-line-chart'

interface ModelsPageProps {
  leaderboard: LeaderboardEntry[]
}


export function ModelsPage({ leaderboard }: ModelsPageProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [selectedModel, setSelectedModel] = useState<string>(leaderboard[0]?.id || '')
  const [modelDecisions, setModelDecisions] = useState<ModelInvestmentDecision[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [showEventPopup, setShowEventPopup] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<{
    eventDecision: any;
    decisionDate: string;
  } | null>(null)
  const [showCalendar, setShowCalendar] = useState(false)
  const [calendarDate, setCalendarDate] = useState(new Date())

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

  useEffect(() => {
    if (selectedModel) {
      setLoading(true)
      apiService.getModelResultsById(selectedModel)
        .then(setModelDecisions)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [selectedModel])

  // Initialize calendar to a month with decisions
  useEffect(() => {
    if (modelDecisions.length > 0) {
      const firstDecisionDate = new Date(modelDecisions[0].target_date)
      setCalendarDate(new Date(firstDecisionDate.getFullYear(), firstDecisionDate.getMonth(), 1))
    }
  }, [modelDecisions])



  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
    navigate(`/models?selected=${modelId}`, { replace: true })
  }

  const handleEventClick = (eventDecision: any, decisionDate: string) => {
    setSelectedEvent({ eventDecision, decisionDate })
    setShowEventPopup(true)
  }

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
      const dateStr = current.toISOString().split('T')[0]
      const hasDecision = modelDecisions.some(d => d.target_date === dateStr)
      const decisionCount = hasDecision ? 
        modelDecisions.find(d => d.target_date === dateStr)?.event_investment_decisions.length || 0 : 0
      
      const isCurrentMonth = current.getMonth() === month
      
      days.push({
        date: new Date(current),
        dateStr,
        hasDecision,
        decisionCount,
        isSelected: selectedDate === dateStr,
        isCurrentMonth
      })
      current.setDate(current.getDate() + 1)
    }
    
    return days
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header with title and model selection */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Inspect model performance</h1>

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
                            Profit: ${model.final_cumulative_pnl.toFixed(1)} | Brier score: {((1 - model.avg_brier_score) * 100).toFixed(1)}%
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
          <div className="p-6 bg-card rounded-xl border border-border">
            {/* Model Info - Always visible */}
            <div className="mb-8 border-b border-border pb-6">
              <h2 className="text-xl font-semibold mb-4">{selectedModelData.model}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Final Profit:
                    <InfoTooltip content="This is the PnL (Profit and Loss), or cumulative profit from all trades made by the model" />
                  </div>
                  <div className="font-medium">{selectedModelData.final_cumulative_pnl.toFixed(1)}</div>
                </div>
                <div>
                  <div className="flex items-center text-muted-foreground">
                    Brier score:
                    <InfoTooltip content="A measure of prediction accuracy. Lower values indicate better calibration - how well the model's confidence matches actual outcomes (0 = perfect, 1 = worst)" />
                  </div>
                  <div className="font-medium">{((1 - selectedModelData.avg_brier_score) * 100).toFixed(1)}%</div>
                </div >
                <div>
                  <span className="text-muted-foreground">Trades:</span>
                  <div className="font-medium">{selectedModelData.trades}</div>
                </div>
              </div >
            </div >

            {/* Event-based Cumulative Profit Chart */}
            {loading ? (
              <div className="mb-8">
                <h3 className="text-lg font-semibold mb-4">Event-based Cumulative Profit</h3>
                <div className="h-[500px] bg-muted/20 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                    <div className="text-sm text-muted-foreground">Loading decision data...</div>
                  </div>
                </div>
              </div>
            ) : modelDecisions.length > 0 ? (
              <div className="mb-8">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  Event-based Cumulative Profit
                  <InfoTooltip content="Each line shows the cumulative profit from a single event decision, starting from 0 when the decision was made" />
                </h3>
                <div className="h-[500px]">
                  <VisxLineChart
                    height={500}
                    margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                    series={modelDecisions.flatMap((decision, decisionIndex) =>
                      decision.event_investment_decisions.map((eventDecision, eventIndex) => ({
                        dataKey: `event_${eventDecision.event_id}_${decision.target_date}`,
                        data: [
                          { x: decision.target_date, y: 0 }, // Start at 0 when decision was made
                          // Here we would need PnL evolution data for each event
                          // For now, showing placeholder data
                          { x: new Date(new Date(decision.target_date).getTime() + 30*24*60*60*1000).toISOString().split('T')[0], y: Math.random() * 0.1 - 0.05 }
                        ],
                        stroke: getChartColor(decisionIndex * decision.event_investment_decisions.length + eventIndex),
                        name: `${eventDecision.event_title.substring(0, 30)}... (${decision.target_date})`
                      }))
                    )}
                  />
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground mb-8">
                No decision data available for this model.
              </div>
            )}

            {/* Decisions Calendar */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Decisions Calendar</h3>
                <button
                  onClick={() => setShowCalendar(!showCalendar)}
                  className="flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-accent"
                >
                  <Calendar size={16} />
                  {showCalendar ? 'Hide Calendar' : 'Show Calendar'}
                </button>
              </div>
              
              {showCalendar && modelDecisions.length > 0 && (
                <div className="mb-6 p-4 bg-card rounded-lg border">
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
                    
                    <button
                      onClick={() => navigateCalendar('next')}
                      className="p-2 rounded-lg hover:bg-accent transition-colors"
                      title="Next month"
                    >
                      <ChevronRight size={16} />
                    </button>
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
                          className={`w-full p-2 text-xs rounded transition-colors relative ${
                            !day.isCurrentMonth 
                              ? 'text-muted-foreground/30 cursor-default'
                              : day.hasDecision
                                ? day.isSelected
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-accent hover:bg-accent/80 cursor-pointer'
                                : 'text-muted-foreground cursor-default'
                          }`}
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
                {modelDecisions.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-4">Decision dates available:</div>
                    <div className="flex flex-wrap gap-2 mb-4">
                      {modelDecisions.map((decision, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedDate(decision.target_date)}
                          className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                            selectedDate === decision.target_date
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'bg-background border-border hover:bg-accent'
                          }`}
                        >
                          {decision.target_date} ({decision.event_investment_decisions.length} events)
                        </button>
                      ))}
                    </div>
                    
                    {selectedDate && (
                      <div className="p-4 bg-card rounded-lg border">
                        <h4 className="font-medium mb-3">Decisions for {selectedDate}:</h4>
                        {modelDecisions
                          .find(d => d.target_date === selectedDate)
                          ?.event_investment_decisions.map((eventDecision, index) => (
                            <button
                              key={index}
                              onClick={() => handleEventClick(eventDecision, selectedDate)}
                              className="w-full mb-3 p-3 bg-muted/20 rounded hover:bg-muted/30 transition-colors text-left"
                            >
                              <div className="font-medium text-sm">{eventDecision.event_title}</div>
                              <div className="text-xs text-muted-foreground mt-1">
                                {eventDecision.market_investment_decisions.length} market decisions • Click to view details
                              </div>
                            </button>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div >
        </div >
      )
      }

      {/* Event Details Popup */}
      {showEventPopup && selectedEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl border border-border max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">
                {selectedEvent.eventDecision.event_title}
              </h3>
              <button
                onClick={() => setShowEventPopup(false)}
                className="p-1 rounded-lg hover:bg-accent"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="mb-6">
                <div className="text-sm text-muted-foreground mb-2">
                  Decision made on: {selectedEvent.decisionDate}
                </div>
                <div className="text-sm text-muted-foreground mb-4">
                  {selectedEvent.eventDecision.event_description || 'No description available'}
                </div>
                <div className="text-sm">
                  <span className="font-medium">Unallocated capital:</span> {(selectedEvent.eventDecision.unallocated_capital * 100).toFixed(1)}%
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left side: Market decisions */}
                <div>
                  <h4 className="font-medium mb-4">Market Decisions ({selectedEvent.eventDecision.market_investment_decisions.length})</h4>
                  <div className="space-y-3">
                    {selectedEvent.eventDecision.market_investment_decisions.map((marketDecision: any, index: number) => (
                      <div key={index} className="p-3 bg-muted/20 rounded-lg">
                        <div className="font-medium text-sm mb-2">
                          {marketDecision.market_question || `Market ${marketDecision.market_id}`}
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground mb-2">
                          <div>
                            <span className="font-medium">Bet:</span> {(marketDecision.model_decision.bet * 100).toFixed(1)}%
                          </div>
                          <div>
                            <span className="font-medium">Odds:</span> {(marketDecision.model_decision.odds * 100).toFixed(1)}%
                          </div>
                          <div>
                            <span className="font-medium">Confidence:</span> {marketDecision.model_decision.confidence}/10
                          </div>
                        </div>
                        <div className="text-xs italic bg-background p-2 rounded">
                          "{marketDecision.model_decision.rationale}"
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right side: Market price evolution chart */}
                <div>
                  <h4 className="font-medium mb-4">Market Price Evolution Since Decision</h4>
                  <div className="h-80 bg-muted/10 rounded-lg flex items-center justify-center">
                    <div className="text-center text-muted-foreground">
                      <div className="text-sm">Interactive price evolution chart</div>
                      <div className="text-xs mt-2">
                        This would show how market prices changed since the decision was made on {selectedEvent.decisionDate}
                      </div>
                      <div className="mt-4 h-64">
                        <VisxLineChart
                          height={240}
                          margin={{ left: 40, top: 20, bottom: 30, right: 20 }}
                          yDomain={[0, 1]}
                          series={selectedEvent.eventDecision.market_investment_decisions.map((marketDecision: any, index: number) => ({
                            dataKey: `market_${marketDecision.market_id}`,
                            data: [
                              { x: selectedEvent.decisionDate, y: marketDecision.model_decision.odds },
                              { x: new Date(new Date(selectedEvent.decisionDate).getTime() + 7*24*60*60*1000).toISOString().split('T')[0], y: marketDecision.model_decision.odds + (Math.random() - 0.5) * 0.2 },
                              { x: new Date(new Date(selectedEvent.decisionDate).getTime() + 14*24*60*60*1000).toISOString().split('T')[0], y: marketDecision.model_decision.odds + (Math.random() - 0.5) * 0.3 }
                            ],
                            stroke: getChartColor(index),
                            name: marketDecision.market_question?.substring(0, 20) + '...' || `Market ${index + 1}`
                          }))}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div >
  )
}