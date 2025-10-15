import { CheckCircle, Clock, Globe, Search } from 'lucide-react'

interface AgentExampleProps {
  steps: Array<{
    title: string
    timing?: string
    tokens?: string
    modelOutput?: string
    tool?: string
    toolArgs?: string
    output?: string
    isError?: boolean
  }>
}

export function AgentExample({ steps }: AgentExampleProps) {
  return (
    <div className="space-y-4 my-6">
      {/* Task Box */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg">
        <div className="flex items-center mb-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Task</span>
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300 space-y-3">
          <p>
            <strong>You are an expert prediction-market analyst.</strong> You have been given an amount of USD $1.0 to allocate on the following event from the prediction market Polymarket.
          </p>

          <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded font-mono text-xs space-y-2">
            <div><strong>Event Details:</strong></div>
            <div>• Date: September 17, 2025</div>
            <div>• Title: Nobel Peace Prize Winner 2025</div>
            <div>• Description: This market will resolve according to the winner of the 2025 Nobel Peace Prize, as announced by the Norwegian Nobel Committee.</div>
            <div className="mt-2 text-gray-600 dark:text-gray-400">
              Resolution Rules: If Trump, Zelensky, Musk, Pope Leo XIII, or Navalnaya are among recipients, resolve to highest-ranked. If joint award between individual and organization, favor individual. Alphabetical ordering for same types.
            </div>
            <div>• Available Markets: 19 markets</div>
          </div>

          <div className="bg-blue-100 dark:bg-blue-800/20 p-3 rounded text-xs space-y-1">
            <div><strong>Sample Market Data:</strong></div>
            <div>📊 <strong>Trump:</strong> 0.043 (down from 0.095 in August)</div>
            <div>📊 <strong>Sudan's Emergency Response Rooms:</strong> 0.175 (up from 0.070)</div>
            <div>📊 <strong>Yulia Navalnaya:</strong> 0.070</div>
            <div>📊 <strong>UNRWA:</strong> 0.065</div>
            <div>📊 <strong>Doctors Without Borders:</strong> 0.055</div>
            <div className="text-gray-500">... plus 14 other markets with price histories</div>
          </div>

          <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded text-xs space-y-1">
            <div><strong>Analysis Guidelines:</strong></div>
            <div>• Use web search to gather up-to-date information about this event</div>
            <div>• Be critical of any sources, and be cautious of sensationalized headlines</div>
            <div>• If results appear to indicate the event's outcome directly, double-check they don't refer to another event</div>
            <div>• Only place a bet when you estimate that the market is mispriced</div>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded text-xs space-y-1">
            <div><strong>Capital Allocation Rules:</strong></div>
            <div>• You have exactly 1.0 dollars to allocate</div>
            <div>• For EACH market, specify: market_id, rationale, estimated_probability (0-1), confidence (0-10), bet (-1 to 1)</div>
            <div>• Negative bet = buy second outcome ("No"), positive = first outcome ("Yes")</div>
            <div>• Sum of |bets| + unallocated_capital must equal 1.0</div>
          </div>
        </div>
      </div>

      {/* Steps */}
      {steps.map((step, index) => (
        <div key={index} className="border-l-2 border-gray-200 dark:border-gray-700 pl-4 ml-2">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gray-400 rounded-full -ml-6 bg-gray-200 dark:bg-gray-700 border-2 border-white dark:border-gray-900" />
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                {step.title}
              </span>
            </div>
            {(step.timing || step.tokens) && (
              <div className="flex items-center gap-4 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-400">
                {step.timing && (
                  <div className="flex items-center gap-1">
                    <Clock size={12} />
                    <span>{step.timing}</span>
                  </div>
                )}
                {step.tokens && <span>{step.tokens}</span>}
              </div>
            )}
          </div>

          <div className="space-y-2 mb-6">
            {step.modelOutput && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">Model Output:</div>
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  {step.modelOutput}
                </div>
              </div>
            )}

            {step.tool && (
              <div className="my-2 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <div className="flex items-center gap-2 mb-2">
                  {step.tool === 'web_search' ? (
                    <Search size={16} className="text-purple-700 dark:text-purple-300" />
                  ) : (
                    <Globe size={16} className="text-purple-700 dark:text-purple-300" />
                  )}
                  <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                    {step.tool}
                  </span>
                </div>
                {step.toolArgs && (
                  <div className="text-xs text-gray-600 dark:text-gray-400 font-mono bg-gray-100 dark:bg-gray-800 p-2 rounded">
                    {step.toolArgs}
                  </div>
                )}
              </div>
            )}

            {step.output && (
              <div className={`my-2 p-3 rounded-lg border ${step.isError
                ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                }`}>
                <div className="flex items-start gap-2">
                  <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <pre className="text-sm whitespace-pre-wrap break-words font-mono text-gray-700 dark:text-gray-300">
                      {step.output}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}