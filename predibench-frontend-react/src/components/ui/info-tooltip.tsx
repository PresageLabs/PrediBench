import * as Tooltip from '@radix-ui/react-tooltip'
import { HelpCircle } from 'lucide-react'
// Using a regular anchor for hash navigation to ensure scrolling to the section

interface InfoTooltipProps {
  content: string
}

export function InfoTooltip({ content }: InfoTooltipProps) {
  return (
    <Tooltip.Provider>
      <Tooltip.Root delayDuration={0}>
        <Tooltip.Trigger asChild>
          <button className="inline-flex items-center justify-center ml-1 text-muted-foreground hover:text-foreground transition-colors">
            <HelpCircle className="h-3.5 w-3.5" />
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="max-w-xs px-3 py-2 text-sm bg-popover text-popover-foreground rounded-lg border border-border shadow-lg z-50"
            side="top"
            sideOffset={4}
          >
            <span>
              {content}	→ <a href="/#intro" className="underline hover:no-underline">
                Read more
              </a>
            </span>
            <Tooltip.Arrow className="fill-popover" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}

export function BrierScoreInfoTooltip() {
  return (
    <InfoTooltip content="How well the model's confidence matches actual outcomes (0 = perfect, 1 = worst). More precisely, it measures model calibration, through the Mean Squared Error between the model's predictions and the actual outcomes." />
  )
}

export function PnLTooltip() {
  return (
    <InfoTooltip content="How much the total invested amount has grown. On every event, each model can allocate $1.0 between markets, and we measure how much comes out, then we sum this across predictions. So +20% means that in total, investments returned 120% of the amount invested." />
  )
}
