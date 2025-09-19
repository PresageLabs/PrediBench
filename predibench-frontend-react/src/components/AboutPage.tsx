import { Info, TrendingUp, Users, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { useTheme } from '../contexts/ThemeContext'

interface PlotlyFigure {
  data: any[]
  layout: any
}

export function AboutPage() {
  const { theme } = useTheme()
  const [consistencyRates, setConsistencyRates] = useState<PlotlyFigure | null>(null)
  const [calibrationTrends, setCalibrationTrends] = useState<PlotlyFigure | null>(null)
  const [correlationMatrix, setCorrelationMatrix] = useState<PlotlyFigure | null>(null)
  const [betAmountGpt5, setBetAmountGpt5] = useState<PlotlyFigure | null>(null)
  const [betAmountGpt5Mini, setBetAmountGpt5Mini] = useState<PlotlyFigure | null>(null)
  const [probabilityGpt5, setProbabilityGpt5] = useState<PlotlyFigure | null>(null)
  const [probabilityGptOss120b, setProbabilityGptOss120b] = useState<PlotlyFigure | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Theme-aware chart colors
  const getChartTheme = () => {
    const isDark = theme === 'dark'
    return {
      bgcolor: isDark ? '#000000' : '#ffffff',
      textColor: isDark ? 'white' : 'black',
      gridColor: isDark ? '#404040' : '#e5e7eb',
      lineColor: isDark ? '#ffffff' : '#374151'
    }
  }


  useEffect(() => {
    const loadFigures = async () => {
      try {
        const [
          consistencyRes,
          calibrationRes,
          correlationRes,
          betAmountGpt5Res,
          betAmountGpt5MiniRes,
          probGpt5Res,
          probGptOss120bRes
        ] = await Promise.all([
          fetch('/market_dynamics/consistency_rates.json'),
          fetch('/market_dynamics/calibration_trends.json'),
          fetch('/market_dynamics/decision_correlation_matrix.json'),
          fetch('/market_dynamics/bet_amount_vs_confidence_gpt5.json'),
          fetch('/market_dynamics/bet_amount_vs_confidence_gpt5_mini.json'),
          fetch('/market_dynamics/probability_calibration_gpt5.json'),
          fetch('/market_dynamics/probability_calibration_gpt_oss_120b.json')
        ])

        if (!consistencyRes.ok || !calibrationRes.ok || !correlationRes.ok ||
            !betAmountGpt5Res.ok || !betAmountGpt5MiniRes.ok ||
            !probGpt5Res.ok || !probGptOss120bRes.ok) {
          throw new Error('Failed to load analytics data')
        }

        const [
          consistency,
          calibration,
          correlation,
          betAmountGpt5,
          betAmountGpt5Mini,
          probGpt5,
          probGptOss120b
        ] = await Promise.all([
          consistencyRes.json(),
          calibrationRes.json(),
          correlationRes.json(),
          betAmountGpt5Res.json(),
          betAmountGpt5MiniRes.json(),
          probGpt5Res.json(),
          probGptOss120bRes.json()
        ])

        setConsistencyRates(consistency)
        setCalibrationTrends(calibration)
        setCorrelationMatrix(correlation)
        setBetAmountGpt5(betAmountGpt5)
        setBetAmountGpt5Mini(betAmountGpt5Mini)
        setProbabilityGpt5(probGpt5)
        setProbabilityGptOss120b(probGptOss120b)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      } finally {
        setLoading(false)
      }
    }

    loadFigures()
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-12">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading analytics...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-6 py-12">
        <div className="text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error Loading Analytics</h2>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-4xl font-bold tracking-tight mb-6">
          About PrediBench
        </h1>
        <p className="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
          PrediBench is a cutting-edge platform for evaluating and benchmarking large language models
          through real-world prediction markets. We assess how AI models perform when making predictions
          about future events with real stakes and measurable outcomes.
        </p>
      </div>

      {/* Mission Statement */}
      <div className="grid md:grid-cols-3 gap-8 mb-16">
        <div className="text-center p-6 rounded-lg bg-card border">
          <TrendingUp className="h-12 w-12 text-primary mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Predictive Intelligence</h3>
          <p className="text-muted-foreground">
            We measure how well AI models can forecast real-world events, from market movements
            to technological breakthroughs, providing insights into their practical reasoning capabilities.
          </p>
        </div>
        <div className="text-center p-6 rounded-lg bg-card border">
          <Users className="h-12 w-12 text-primary mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Fair Evaluation</h3>
          <p className="text-muted-foreground">
            Our benchmarking methodology ensures objective, standardized testing across different
            model architectures, sizes, and training approaches to identify true performance differences.
          </p>
        </div>
        <div className="text-center p-6 rounded-lg bg-card border">
          <Zap className="h-12 w-12 text-primary mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Real-Time Insights</h3>
          <p className="text-muted-foreground">
            Track model performance in real-time as predictions are made and outcomes are determined,
            providing immediate feedback on predictive accuracy and calibration.
          </p>
        </div>
      </div>

      {/* Analytics Section */}
      <div className="mb-16">
        <div className="flex items-center gap-3 mb-8">
          <Info className="h-6 w-6 text-primary" />
          <h2 className="text-2xl font-bold">Market Dynamics Analytics</h2>
        </div>
        <p className="text-muted-foreground mb-8 text-lg">
          Our platform generates comprehensive analytics on how different AI models behave in
          prediction markets, including consistency rates, calibration accuracy, and decision correlations.
        </p>

        {/* Consistency Rates Chart */}
        {consistencyRates && (
          <div className="mb-12 p-6 rounded-lg bg-card border">
            <h3 className="text-xl font-semibold mb-4">Model Consistency Rates</h3>
            <p className="text-muted-foreground mb-6">
              This chart shows how consistently each model aligns its betting decisions with edge calculations.
              Higher consistency indicates better internal coherence in decision-making.
            </p>
            <div className="w-full overflow-x-auto">
              <Plot
                data={consistencyRates.data}
                layout={{
                  ...consistencyRates.layout,
                  paper_bgcolor: getChartTheme().bgcolor,
                  plot_bgcolor: getChartTheme().bgcolor,
                  font: { color: getChartTheme().textColor },
                  title: {
                    ...consistencyRates.layout.title,
                    font: { color: getChartTheme().textColor }
                  },
                  xaxis: {
                    ...consistencyRates.layout.xaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...consistencyRates.layout.xaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  },
                  yaxis: {
                    ...consistencyRates.layout.yaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...consistencyRates.layout.yaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  }
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '600px' }}
              />
            </div>
          </div>
        )}

        {/* Calibration Trends Chart */}
        {calibrationTrends && (
          <div className="mb-12 p-6 rounded-lg bg-card border">
            <h3 className="text-xl font-semibold mb-4">Calibration Trends Over Time</h3>
            <p className="text-muted-foreground mb-6">
              This visualization tracks how model prediction calibration changes over time,
              helping identify learning patterns and adaptation capabilities.
            </p>
            <div className="w-full overflow-x-auto">
              <Plot
                data={calibrationTrends.data}
                layout={{
                  ...calibrationTrends.layout,
                  paper_bgcolor: getChartTheme().bgcolor,
                  plot_bgcolor: getChartTheme().bgcolor,
                  font: { color: getChartTheme().textColor },
                  title: {
                    ...calibrationTrends.layout.title,
                    font: { color: getChartTheme().textColor }
                  },
                  xaxis: {
                    ...calibrationTrends.layout.xaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...calibrationTrends.layout.xaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  },
                  yaxis: {
                    ...calibrationTrends.layout.yaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...calibrationTrends.layout.yaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  }
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '500px' }}
              />
            </div>
          </div>
        )}

        {/* Correlation Matrix */}
        {correlationMatrix && (
          <div className="mb-12 p-6 rounded-lg bg-card border">
            <h3 className="text-xl font-semibold mb-4">Decision Correlation Matrix</h3>
            <p className="text-muted-foreground mb-6">
              This heatmap reveals how similarly different models make decisions across various market scenarios,
              highlighting potential clustering of decision-making strategies.
            </p>
            <div className="w-full overflow-x-auto">
              <Plot
                data={correlationMatrix.data}
                layout={{
                  ...correlationMatrix.layout,
                  paper_bgcolor: getChartTheme().bgcolor,
                  plot_bgcolor: getChartTheme().bgcolor,
                  font: { color: getChartTheme().textColor },
                  title: {
                    ...correlationMatrix.layout.title,
                    font: { color: getChartTheme().textColor }
                  },
                  xaxis: {
                    ...correlationMatrix.layout.xaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...correlationMatrix.layout.xaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  },
                  yaxis: {
                    ...correlationMatrix.layout.yaxis,
                    gridcolor: getChartTheme().gridColor,
                    linecolor: getChartTheme().lineColor,
                    tickcolor: getChartTheme().lineColor,
                    tickfont: { color: getChartTheme().textColor },
                    title: {
                      ...correlationMatrix.layout.yaxis?.title,
                      font: { color: getChartTheme().textColor }
                    }
                  }
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '600px' }}
              />
            </div>
          </div>
        )}

        {/* Bet Amount vs Confidence - GPT-5 vs GPT-5 Mini Side by Side */}
        {betAmountGpt5 && betAmountGpt5Mini && (
          <div className="mb-12 p-6 rounded-lg bg-card border">
            <h3 className="text-xl font-semibold mb-4">Bet Amount vs Confidence: GPT-5 vs GPT-5 Mini</h3>
            <p className="text-muted-foreground mb-6">
              This comparison shows how GPT-5 and GPT-5 Mini correlate their bet amounts with confidence levels.
              Higher correlation indicates better calibration between internal confidence and betting behavior.
            </p>
            <div className="grid md:grid-cols-2 gap-6">
              {/* GPT-5 Chart */}
              <div className="w-full overflow-x-auto">
                <h4 className="text-lg font-medium mb-3 text-center">GPT-5</h4>
                <Plot
                  data={betAmountGpt5.data}
                  layout={{
                    ...betAmountGpt5.layout,
                    paper_bgcolor: getChartTheme().bgcolor,
                    plot_bgcolor: getChartTheme().bgcolor,
                    font: { color: getChartTheme().textColor },
                    title: {
                      text: '',
                      font: { color: getChartTheme().textColor }
                    },
                    legend: {
                      orientation: 'h',
                      x: 0.5,
                      xanchor: 'center',
                      y: 1.02,
                      yanchor: 'bottom'
                    },
                    width: 600,
                    height: 500,
                    xaxis: {
                      ...betAmountGpt5.layout.xaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...betAmountGpt5.layout.xaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    },
                    yaxis: {
                      ...betAmountGpt5.layout.yaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...betAmountGpt5.layout.yaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '500px' }}
                />
              </div>

              {/* GPT-5 Mini Chart */}
              <div className="w-full overflow-x-auto">
                <h4 className="text-lg font-medium mb-3 text-center">GPT-5 Mini</h4>
                <Plot
                  data={betAmountGpt5Mini.data}
                  layout={{
                    ...betAmountGpt5Mini.layout,
                    paper_bgcolor: getChartTheme().bgcolor,
                    plot_bgcolor: getChartTheme().bgcolor,
                    font: { color: getChartTheme().textColor },
                    title: {
                      text: '',
                      font: { color: getChartTheme().textColor }
                    },
                    legend: {
                      orientation: 'h',
                      x: 0.5,
                      xanchor: 'center',
                      y: 1.02,
                      yanchor: 'bottom'
                    },
                    width: 600,
                    height: 500,
                    xaxis: {
                      ...betAmountGpt5Mini.layout.xaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...betAmountGpt5Mini.layout.xaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    },
                    yaxis: {
                      ...betAmountGpt5Mini.layout.yaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...betAmountGpt5Mini.layout.yaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '500px' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Probability Calibration - GPT-5 vs GPT-OSS 120B Side by Side */}
        {probabilityGpt5 && probabilityGptOss120b && (
          <div className="mb-12 p-6 rounded-lg bg-card border">
            <h3 className="text-xl font-semibold mb-4">Model Probability Estimates vs Market Prices: GPT-5 vs GPT-OSS 120B</h3>
            <p className="text-muted-foreground mb-6">
              This comparison shows how well GPT-5 and GPT-OSS 120B calibrate their probability estimates
              against actual market prices. Points closer to the diagonal line indicate better calibration.
            </p>
            <div className="grid md:grid-cols-2 gap-6">
              {/* GPT-5 Chart */}
              <div className="w-full overflow-x-auto">
                <h4 className="text-lg font-medium mb-3 text-center">GPT-5</h4>
                <Plot
                  data={probabilityGpt5.data}
                  layout={{
                    ...probabilityGpt5.layout,
                    paper_bgcolor: getChartTheme().bgcolor,
                    plot_bgcolor: getChartTheme().bgcolor,
                    font: { color: getChartTheme().textColor },
                    title: {
                      text: '',
                      font: { color: getChartTheme().textColor }
                    },
                    legend: {
                      orientation: 'h',
                      x: 0.5,
                      xanchor: 'center',
                      y: 1.02,
                      yanchor: 'bottom'
                    },
                    width: 600,
                    height: 500,
                    xaxis: {
                      ...probabilityGpt5.layout.xaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...probabilityGpt5.layout.xaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    },
                    yaxis: {
                      ...probabilityGpt5.layout.yaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...probabilityGpt5.layout.yaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '500px' }}
                />
              </div>

              {/* GPT-OSS 120B Chart */}
              <div className="w-full overflow-x-auto">
                <h4 className="text-lg font-medium mb-3 text-center">GPT-OSS 120B</h4>
                <Plot
                  data={probabilityGptOss120b.data}
                  layout={{
                    ...probabilityGptOss120b.layout,
                    paper_bgcolor: getChartTheme().bgcolor,
                    plot_bgcolor: getChartTheme().bgcolor,
                    font: { color: getChartTheme().textColor },
                    title: {
                      text: '',
                      font: { color: getChartTheme().textColor }
                    },
                    legend: {
                      orientation: 'h',
                      x: 0.5,
                      xanchor: 'center',
                      y: 1.02,
                      yanchor: 'bottom'
                    },
                    width: 600,
                    height: 500,
                    xaxis: {
                      ...probabilityGptOss120b.layout.xaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...probabilityGptOss120b.layout.xaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    },
                    yaxis: {
                      ...probabilityGptOss120b.layout.yaxis,
                      gridcolor: getChartTheme().gridColor,
                      linecolor: getChartTheme().lineColor,
                      tickcolor: getChartTheme().lineColor,
                      tickfont: { color: getChartTheme().textColor },
                      title: {
                        ...probabilityGptOss120b.layout.yaxis?.title,
                        font: { color: getChartTheme().textColor }
                      }
                    }
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '500px' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* How It Works */}
      <div className="mb-16">
        <h2 className="text-2xl font-bold mb-8">How PrediBench Works</h2>
        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">1. Event Creation</h3>
              <p className="text-muted-foreground">
                We curate a diverse set of real-world events across domains like technology,
                economics, politics, and science with clear resolution criteria.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">2. Model Prediction</h3>
              <p className="text-muted-foreground">
                Each participating AI model analyzes available information and makes predictions
                with confidence estimates and betting strategies.
              </p>
            </div>
          </div>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">3. Market Simulation</h3>
              <p className="text-muted-foreground">
                Models participate in simulated prediction markets where they can place bets
                based on their confidence and risk assessment.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">4. Performance Evaluation</h3>
              <p className="text-muted-foreground">
                We measure accuracy, calibration, profitability, and consistency to provide
                comprehensive performance metrics.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Future Vision */}
      <div className="text-center bg-card p-8 rounded-lg border">
        <h2 className="text-2xl font-bold mb-4">Our Vision</h2>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
          As AI systems become more integrated into decision-making processes, PrediBench aims to be
          the definitive platform for evaluating their real-world predictive capabilities. We believe
          that rigorous benchmarking in prediction markets will drive improvements in AI reasoning,
          calibration, and practical utility.
        </p>
      </div>
    </div>
  )
}