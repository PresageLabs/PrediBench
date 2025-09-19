import * as Tooltip from '@radix-ui/react-tooltip'
import { HelpCircle } from 'lucide-react'
// Using a regular anchor for hash navigation to ensure scrolling to the section

interface InfoTooltipProps {
  content: string
}

function parseMarkdownLinks(text: string) {
  // Regular expression to match [text](url) markdown links
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match

  while ((match = linkRegex.exec(text)) !== null) {
    // Add text before the link
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index))
    }

    // Add the link element
    const [, linkText, url] = match
    parts.push(
      <a
        key={match.index}
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="underline hover:no-underline text-blue-400"
      >
        {linkText}
      </a>
    )

    lastIndex = linkRegex.lastIndex
  }

  // Add remaining text after the last link
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex))
  }

  return parts.length > 0 ? parts : [text]
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
              {parseMarkdownLinks(content)}
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
    <InfoTooltip content="Daily returns over the lates prediction ; when we run a prediction, we allocate 1$ per event. This graphs track how well each investment did." />
  )
}
