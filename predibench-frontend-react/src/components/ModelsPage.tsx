import * as Select from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { LeaderboardEntry, ModelMarketDetails } from '../api'
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
  const [marketDetails, setMarketDetails] = useState<ModelMarketDetails | null>(null)
  const [loading, setLoading] = useState(false)

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
      apiService.getModelMarketDetails(selectedModel)
        .then(setMarketDetails)
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [selectedModel])


  // Debug logging
  // if (marketDetails && marketDetails.markets.length > 0) {
  //   console.log('Market details:', {
  //     marketCount: marketDetails.markets.length,
  //     pnlCount: marketDetails.market_pnls.length,
  //     priceDataPoints: marketDetails.price_chart_data?.length,
  //     pnlDataPoints: marketDetails.pnl_chart_data?.length,
  //     marketInfo: marketDetails.market_info
  //   })
  // }

  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
    navigate(`/models?selected=${modelId}`, { replace: true })
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
            <Select.Content className="overflow-hidden rounded-lg border border-border bg-popover shadow-lg">
              <Select.Viewport className="p-1">
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
                          <div className="text-xs text-muted-foreground grid grid-cols-2 gap-2 mt-1">
                            <span className="flex items-center">
                              Profit: {model.final_cumulative_pnl.toFixed(1)}
                              <InfoTooltip content="This is the PnL (Profit and Loss), or cumulative profit from all trades made by the model" />
                            </span>
                            <span className="flex items-center">
                              Brier score: {((model.accuracy || 0) * 100).toFixed(0)}%
                              <InfoTooltip content="A measure of prediction accuracy. Lower values indicate better calibration - how well the model's confidence matches actual outcomes (0 = perfect, 1 = worst)" />
                            </span>
                          </div>
                        </div>
                      </div>
                    </Select.ItemText>
                    <Select.ItemIndicator className="absolute right-2">
                      <Check size={14} />
                    </Select.ItemIndicator>
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
                  <div className="font-medium">{((selectedModelData.accuracy || 0) * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Trades:</span>
                  <div className="font-medium">{selectedModelData.trades}</div>
                </div>
              </div>
            </div>

            {/* Charts Section */}
            {loading ? (
              <div className="space-y-8">
                {/* Price Evolution Chart Loading */}
                <div className="mb-8">
                  <h3 className="text-lg font-semibold mb-4">Price Evolution</h3>
                  <div className="h-80 bg-muted/20 rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                      <div className="text-sm text-muted-foreground">Loading price data...</div>
                    </div>
                  </div>
                </div>

                {/* Profit Chart Loading */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">Cumulative Profit</h3>
                  <div className="h-80 bg-muted/20 rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
                      <div className="text-sm text-muted-foreground">Loading profit data...</div>
                    </div>
                  </div>
                </div>
              </div>
            ) : marketDetails && Object.keys(marketDetails).length > 0 ? (
              <div className="space-y-8">
                {/* Price Evolution Chart */}
                <div className="mb-8">
                  <h3 className="text-lg font-semibold mb-4">Price Evolution</h3>
                  <div className="h-80">
                    <VisxLineChart
                      height={320}
                      margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                      yDomain={[0, 1]}
                      series={Object.values(marketDetails).map((market, marketIndex) => ({
                        dataKey: `price_${market.market_id}`,
                        data: (market.prices || []).map(point => ({
                          x: point.date,
                          y: point.price
                        })),
                        stroke: getChartColor(marketIndex),
                        name: market.question
                      }))}
                    />
                  </div>
                </div>

                {/* Profit Chart */}
                {Object.values(marketDetails).some(market => market.pnl_data && market.pnl_data.length > 0) && (
                  <div>
                    <h3 className="text-lg font-semibold mb-4 flex items-center">
                      Cumulative Profit
                      <InfoTooltip content="This is the PnL (Profit and Loss), or cumulative profit from all trades made by the model" />
                    </h3>
                    <div className="h-80">
                      <VisxLineChart
                        height={320}
                        margin={{ left: 60, top: 35, bottom: 38, right: 27 }}
                        series={Object.values(marketDetails)
                          .filter(market => market.pnl_data && market.pnl_data.length > 0)
                          .map((market, marketIndex) => ({
                            dataKey: `pnl_${market.market_id}`,
                            data: (market.pnl_data || []).map(point => {
                              const positionData = market.positions?.find((p: { date: string }) => p.date === point.date)
                              return {
                                x: point.date,
                                y: point.pnl,
                                position: positionData?.position
                              }
                            }),
                            stroke: getChartColor(marketIndex),
                            name: market.question
                          }))}
                      />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No market data available for this model.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}