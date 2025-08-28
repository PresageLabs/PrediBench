import * as Tooltip from '@radix-ui/react-tooltip'
import { HelpCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

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
              {content}	→ <Link to="/about" className="underline hover:no-underline">
                Read more
              </Link>
            </span>
            <Tooltip.Arrow className="fill-popover" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}