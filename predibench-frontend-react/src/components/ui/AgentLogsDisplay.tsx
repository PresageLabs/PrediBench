import { CheckCircle, Clock, Code, Search, XCircle, Zap } from 'lucide-react'

interface AgentStep {
  step_number?: number
  timing?: {
    start_time: number
    end_time: number
    duration: number
  }
  token_usage?: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
  }
  model_output?: string
  code_action?: string
  observations?: string
  error?: {
    type: string
    message: string
  }
  tool_calls?: Array<{
    id: string
    type: string
    function: {
      name: string
      arguments: string
    }
  }>
  action_output?: unknown
  task?: string
}

interface AgentLogsDisplayProps {
  logs: unknown[] | unknown
}

// Helper functions
const formatDuration = (duration: number) => {
  if (duration < 1) return `${Math.round(duration * 1000)}ms`
  if (duration < 60) return `${duration.toFixed(1)}s`
  return `${Math.floor(duration / 60)}m ${Math.floor(duration % 60)}s`
}

const formatTokens = (tokens: number) => {
  if (tokens < 1000) return tokens.toString()
  if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`
  return `${(tokens / 1000000).toFixed(1)}M`
}

// Helper function to detect if logs are in smolagent format (list of step objects)
const isSmolagentFormat = (logs: unknown): logs is unknown[] => {
  if (!Array.isArray(logs)) return false
  if (logs.length === 0) return true

  // Check if the first item looks like a smolagent step
  const firstItem = logs[0]
  if (typeof firstItem !== 'object' || firstItem === null) return false

  const step = firstItem as Record<string, unknown>
  // Look for common smolagent step properties
  return 'step_number' in step || 'timing' in step || 'tool_calls' in step || 'task' in step || 'model_output' in step
}

// Components
const ToolIcon = ({ toolName }: { toolName: string }) => {
  switch (toolName) {
    case 'python_interpreter':
      return <Code size={16} className="text-purple-700 dark:text-purple-300" />
    case 'web_search':
      return <Search size={16} className="text-purple-700 dark:text-purple-300" />
    case 'visit_webpage':
      return <Search size={16} className="text-purple-700 dark:text-purple-300" />
    case 'final_answer':
      return <CheckCircle size={16} className="text-purple-700 dark:text-purple-300" />
    default:
      return <Zap size={16} className="text-purple-700 dark:text-purple-300" />
  }
}

const TaskMessage = ({ task }: { task: string }) => (
  <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg">
    <div className="flex items-center mb-2">
      <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
      <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Task</span>
    </div>
    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{task}</p>
  </div>
)

const StepMetrics = ({ step }: { step: AgentStep }) => (
  <div className="flex items-center gap-4 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-400">
    {step.timing && (
      <div className="flex items-center gap-1">
        <Clock size={12} />
        <span>{formatDuration(step.timing.duration || 0)}</span>
      </div>
    )}
    {step.token_usage && (
      <div className="flex items-center gap-2">
        <span>↗ {formatTokens(step.token_usage.input_tokens || 0)}</span>
        <span>↘ {formatTokens(step.token_usage.output_tokens || 0)}</span>
        <span className="text-gray-500">({formatTokens(step.token_usage.total_tokens || 0)} total)</span>
      </div>
    )}
  </div>
)

const CodeBlock = ({ code }: { code: string }) => (
  <div className="my-3 bg-gray-900 text-green-400 p-3 rounded-lg font-mono text-sm overflow-x-auto">
    <div className="flex items-center mb-2 text-gray-500">
      <div className="flex gap-1 mr-3">
        <div className="w-3 h-3 bg-red-500 rounded-full" />
        <div className="w-3 h-3 bg-yellow-500 rounded-full" />
        <div className="w-3 h-3 bg-green-500 rounded-full" />
      </div>
      <span className="text-xs">Terminal</span>
    </div>
    <pre className="whitespace-pre-wrap">{code}</pre>
  </div>
)

const ToolCall = ({ toolCall }: { toolCall: NonNullable<AgentStep['tool_calls']>[0] }) => {
  if (!toolCall) {
    return (
      <div className="my-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
        <span className="text-sm text-red-700 dark:text-red-300">Missing tool call data</span>
      </div>
    )
  }

  // Handle different tool call formats
  let toolName: string = 'unknown'
  let toolArgs: string = ''

  if (toolCall.function) {
    // Standard format: { function: { name: "...", arguments: "..." or {...} } }
    const { function: func } = toolCall
    toolName = func.name || 'unknown'

    // Handle both string and object arguments
    if (typeof func.arguments === 'string') {
      toolArgs = func.arguments
    } else if (typeof func.arguments === 'object' && func.arguments !== null) {
      toolArgs = JSON.stringify(func.arguments, null, 2)
    } else {
      toolArgs = func.arguments ? String(func.arguments) : ''
    }
  } else if ((toolCall as any).name) {
    // Alternative format: { name: "...", arguments: "..." }
    toolName = (toolCall as any).name
    const args = (toolCall as any).arguments
    toolArgs = typeof args === 'string' ? args : JSON.stringify(args, null, 2)
  } else if ((toolCall as any).tool) {
    // Another format: { tool: "...", input: "..." }
    toolName = (toolCall as any).tool
    const input = (toolCall as any).input
    toolArgs = typeof input === 'string' ? input : JSON.stringify(input, null, 2)
  } else {
    return (
      <div className="my-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
        <span className="text-sm text-red-700 dark:text-red-300">
          Unsupported tool call format: {JSON.stringify(Object.keys(toolCall))}
        </span>
      </div>
    )
  }

  return (
    <div className="my-2 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
      <div className="flex items-center gap-2 mb-2">
        <ToolIcon toolName={toolName} />
        <span className="text-sm font-medium text-purple-700 dark:text-purple-300">{toolName}</span>
      </div>
      {toolName === 'python_interpreter' ? (
        <CodeBlock code={toolArgs} />
      ) : (
        <div className="text-xs text-gray-600 dark:text-gray-400 font-mono bg-gray-100 dark:bg-gray-800 p-2 rounded">
          {toolArgs || 'No arguments'}
        </div>
      )}
    </div>
  )
}

const OutputMessage = ({ content, isError = false }: { content: string, isError?: boolean }) => (
  <div className={`my-2 p-3 rounded-lg border ${isError
    ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
    : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
    }`}>
    <div className="flex items-start gap-2">
      {isError ? (
        <XCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
      ) : (
        <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <pre className="text-sm whitespace-pre-wrap break-words font-mono text-gray-700 dark:text-gray-300">
          {content}
        </pre>
      </div>
    </div>
  </div>
)

const StepMessage = ({ step }: { step: AgentStep }) => (
  <div className="mb-6">
    <div className="space-y-2">
      {step.model_output && !step.error && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">Model Output:</div>
          <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {step.model_output}
          </div>
        </div>
      )}

      {step.tool_calls?.map((toolCall, index) => (
        <ToolCall key={`${toolCall?.id || 'tool'}-${index}`} toolCall={toolCall} />
      ))}

      {step.error && (
        <>
          {step.model_output && (
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-2">Model Output:</div>
              <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {step.model_output}
              </div>
            </div>
          )}
          <OutputMessage
            content={`${step.error.type}: ${step.error.message}`}
            isError={true}
          />
        </>
      )}

      {step.observations && (
        <OutputMessage content={step.observations} />
      )}
    </div>
  </div>
)

// Smolagent display component
const SmolagentDisplay = ({ logs }: { logs: unknown[] }) => {
  // Cast logs to AgentStep[] for processing
  const agentSteps = logs as AgentStep[]

  // Find the task from the first step
  const taskStep = agentSteps.find(step => step.task)
  const actionSteps = agentSteps.filter(step => step.step_number)

  return (
    <div className="space-y-4">
      {taskStep?.task && <TaskMessage task={taskStep.task} />}

      {actionSteps.map((step, index) => (
        <div key={`step-${step.step_number || index}`} className="border-l-2 border-gray-200 dark:border-gray-700 pl-4 ml-2">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gray-400 rounded-full -ml-6 bg-gray-200 dark:bg-gray-700 border-2 border-white dark:border-gray-900" />
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Step {step.step_number}
                {step.timing && step.timing.start_time && (
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                    | {new Date(step.timing.start_time * 1000).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: false,
                      timeZoneName: 'short'
                    })}
                  </span>
                )}
              </span>
            </div>
            <StepMetrics step={step} />
          </div>
          <StepMessage step={step} />
        </div>
      ))}
    </div>
  )
}

// Raw display component
const RawDisplay = ({ data }: { data: unknown }) => {
  if (!data) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        No logs available
      </div>
    )
  }

  return (
    <div className="bg-muted/10 p-4 rounded-lg border">
      <div className="overflow-x-auto">
        <pre className="text-xs text-foreground whitespace-pre-wrap font-mono">
          {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
        </pre>
      </div>
    </div>
  )
}

// Main component
export function AgentLogsDisplay({ logs }: AgentLogsDisplayProps): JSX.Element {
  // Detect format and use appropriate display; parent effect surfaces errors for missing logs
  if (isSmolagentFormat(logs)) {
    return <SmolagentDisplay logs={logs} />
  } else {
    return <RawDisplay data={logs} />
  }
}
