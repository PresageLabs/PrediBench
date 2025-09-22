import React from 'react'
import PlotlyCard from '../components/ui/PlotlyCard'

type Props = {
  content: string
  className?: string
}

// Very lightweight Markdown renderer supporting:
// - Headings (# .. ######)
// - Paragraphs
// - Unordered lists (- ) and ordered lists (1. )
// - Code blocks ```
// - Inline code `code`
// - Bold **text** and italic *text*
// - Links [text](url)
// - Footnotes [^id] and footnote definitions [^id]: content
// This avoids adding a new dependency while keeping content readable.
export function MarkdownRenderer({ content, className }: Props) {
  const lines = content.replace(/\r\n?/g, '\n').split('\n')

  type Block =
    | { type: 'heading'; level: number; text: string }
    | { type: 'paragraph'; text: string }
    | { type: 'blockquote'; text: string }
    | { type: 'ul'; items: ListItem[] }
    | { type: 'ol'; items: ListItem[] }
    | { type: 'code'; text: string }
    | { type: 'plotly'; caption: string; path: string; secondPath?: string }
    | { type: 'footnote'; id: string; text: string }

  type ListItem = {
    text: string
    level: number
    children?: ListItem[]
  }

  const blocks: Block[] = []
  // Pre-scan for footnotes before processing other blocks
  const footnotes: { [id: string]: string } = {}
  lines.forEach(line => {
    const footnoteMatch = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/)
    if (footnoteMatch) {
      footnotes[footnoteMatch[1]] = footnoteMatch[2].trim()
    }
  })

  // Debug: Log found footnotes for about.md
  if (content.includes('consequences_politiques') || content.includes('GPQA')) {
    console.log('About.md footnotes found:', Object.keys(footnotes))
  }

  let i = 0
  let inCode = false
  let codeBuffer: string[] = []
  let paraBuffer: string[] = []
  let listBuffer: ListItem[] = []
  let listType: 'ul' | 'ol' | null = null

  const flushParagraph = () => {
    if (paraBuffer.length) {
      blocks.push({ type: 'paragraph', text: paraBuffer.join(' ') })
      paraBuffer = []
    }
  }
  const buildNestedList = (items: ListItem[]): ListItem[] => {
    const result: ListItem[] = []
    const stack: ListItem[] = []

    for (const item of items) {
      // Pop from stack until we find the correct parent level
      while (stack.length > 0 && stack[stack.length - 1].level >= item.level) {
        stack.pop()
      }

      if (stack.length === 0) {
        // Top level item
        result.push(item)
        stack.push(item)
      } else {
        // Nested item
        const parent = stack[stack.length - 1]
        if (!parent.children) parent.children = []
        parent.children.push(item)
        stack.push(item)
      }
    }

    return result
  }

  const flushList = () => {
    if (listType && listBuffer.length) {
      const nestedItems = buildNestedList(listBuffer)
      blocks.push({ type: listType, items: nestedItems })
    }
    listType = null
    listBuffer = []
  }
  const flushCode = () => {
    if (codeBuffer.length) {
      blocks.push({ type: 'code', text: codeBuffer.join('\n') })
      codeBuffer = []
    }
  }

  while (i < lines.length) {
    const line = lines[i]

    // Toggle code block
    if (line.trim().startsWith('```')) {
      if (!inCode) {
        // entering code: flush others
        flushParagraph()
        flushList()
        inCode = true
      } else {
        // leaving code
        flushCode()
        inCode = false
      }
      i++
      continue
    }

    if (inCode) {
      codeBuffer.push(line)
      i++
      continue
    }

    // Blank line separates paragraphs/lists
    if (line.trim() === '') {
      flushParagraph()
      flushList()
      i++
      continue
    }

    // Custom Plotly embed: {caption="...", path=..., second_path=...}
    const embedMatch = line.trim().match(/^\{([^}]*)\}$/)
    if (embedMatch) {
      flushParagraph()
      flushList()
      const inner = embedMatch[1]
      // capture caption="..."
      const capMatch = inner.match(/caption\s*=\s*"([^"]+)"/)
      // capture path=... (quoted or unquoted, until comma or end)
      const pathMatch = inner.match(/path\s*=\s*("([^"]+)"|[^,\s}]+)/)
      // optional second_path=... (quoted or unquoted, until comma or end)
      const secondPathMatch = inner.match(/second_path\s*=\s*("([^"]+)"|[^,\s}]+)/)
      const caption = capMatch?.[1]?.trim()
      const path = (pathMatch?.[2] || pathMatch?.[1])?.replace(/^"|"$/g, '').trim()
      const secondPath = (secondPathMatch?.[2] || secondPathMatch?.[1])?.replace(/^"|"$/g, '').trim()
      if (caption && path) {
        blocks.push({ type: 'plotly', caption, path, secondPath })
        i++
        continue
      }
      // fall-through if malformed
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = headingMatch[1].length
      const text = headingMatch[2].trim()
      blocks.push({ type: 'heading', level, text })
      i++
      continue
    }

    // Blockquotes
    const blockquoteMatch = line.match(/^\s*>\s+(.*)$/)
    if (blockquoteMatch) {
      flushParagraph()
      flushList()
      const text = blockquoteMatch[1].trim()
      blocks.push({ type: 'blockquote', text })
      i++
      continue
    }

    // Footnote definitions (skip since we already processed them)
    const footnoteMatch = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/)
    if (footnoteMatch) {
      flushParagraph()
      flushList()
      i++
      continue
    }

    // Lists (with indentation support)
    const ulMatch = line.match(/^(\s*)[-*]\s+(.*)$/)
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)$/)
    if (ulMatch || olMatch) {
      flushParagraph()
      const indentation = (ulMatch ? ulMatch[1] : olMatch![1]).length
      const item = (ulMatch ? ulMatch[2] : olMatch![2]).trim()
      const type: 'ul' | 'ol' = ulMatch ? 'ul' : 'ol'
      const level = Math.floor(indentation / 4) // 4 spaces = 1 level

      if (listType && listType !== type) {
        // switch list type
        flushList()
      }
      listType = type
      listBuffer.push({ text: item, level, children: [] })
      i++
      continue
    }

    // Default: treat as paragraph line
    if (line.trim()) {
      paraBuffer.push(line.trim())
      // Immediately flush single-line paragraphs that follow list items
      if (listType && paraBuffer.length === 1) {
        // Check if next line is empty or another list item - if so, flush now
        const nextLine = i + 1 < lines.length ? lines[i + 1] : ''
        if (!nextLine.trim() || nextLine.match(/^\s*[-*]\s+/) || nextLine.match(/^\s*\d+\.\s+/)) {
          flushParagraph()
        }
      }
    } else {
      // Empty line - flush current paragraph
      flushParagraph()
    }
    i++
  }

  // Final flush
  flushParagraph()
  flushList()
  if (inCode) flushCode()

  // Add footnotes as a bibliography section if any exist
  if (Object.keys(footnotes).length > 0) {
    Object.entries(footnotes).forEach(([id, text]) => {
      blocks.push({ type: 'footnote', id, text })
    })
  }

  const renderInline = (text: string, keyPrefix: string) => {
    // Process bold first, then everything else inside it
    const strongRegex = /\*\*(.*?)\*\*/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let strongMatch: RegExpExecArray | null
    let strongCount = 0

    while ((strongMatch = strongRegex.exec(text))) {
      // Add text before the bold
      if (strongMatch.index > lastIndex) {
        const beforeText = text.slice(lastIndex, strongMatch.index)
        parts.push(...processNonBoldText(beforeText, `${keyPrefix}-before-${strongCount}`))
      }

      // Process the bold content
      const boldContent = strongMatch[1]
      const boldProcessed = processNonBoldText(boldContent, `${keyPrefix}-bold-${strongCount}`)
      parts.push(
        <strong key={`${keyPrefix}-strong-${strongCount}`}>{boldProcessed}</strong>
      )

      lastIndex = strongMatch.index + strongMatch[0].length
      strongCount++
    }

    // Add remaining text after the last bold
    if (lastIndex < text.length) {
      const afterText = text.slice(lastIndex)
      parts.push(...processNonBoldText(afterText, `${keyPrefix}-after`))
    }

    return parts.length > 0 ? parts : [text]
  }

  const processNonBoldText = (text: string, keyPrefix: string): React.ReactNode[] => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const footnoteRefRegex = /\[\^([^\]]+)\]/g
    const codeRegex = /`([^`]+)`/g
    const emRegex = /\*([^*]+)\*/g

    // First process footnote references (before links to avoid conflicts)
    let parts: React.ReactNode[] = []
    let lastIndex = 0
    let footnoteMatch: RegExpExecArray | null
    let footnoteCount = 0

    while ((footnoteMatch = footnoteRefRegex.exec(text))) {
      if (footnoteMatch.index > lastIndex) {
        parts.push(text.slice(lastIndex, footnoteMatch.index))
      }
      const refId = footnoteMatch[1]
      // Get the footnote number based on the order of appearance in the footnotes object
      const footnoteKeys = Object.keys(footnotes)
      const footnoteIndex = footnoteKeys.indexOf(refId)
      const footnoteNumber = footnoteIndex >= 0 ? footnoteIndex + 1 : footnoteCount + 1
      parts.push(
        <a key={`${keyPrefix}-footnote-${footnoteCount}`} href={`#footnote-${refId}`} className="text-primary hover:text-primary/80 text-sm align-super no-underline" onClick={(e) => {
          e.preventDefault()
          const element = document.getElementById(`footnote-${refId}`)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        }}>
          [{footnoteNumber}]
        </a>
      )
      lastIndex = footnoteMatch.index + footnoteMatch[0].length
      footnoteCount++
    }
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex))
    }

    // Then process links on the parts
    const linkProcessedParts: React.ReactNode[] = []
    parts.forEach((part, idx) => {
      if (typeof part !== 'string') {
        linkProcessedParts.push(part)
        return
      }

      let linkParts: React.ReactNode[] = []
      let linkLastIndex = 0
      let linkMatch: RegExpExecArray | null
      let linkCount = 0
      linkRegex.lastIndex = 0

      while ((linkMatch = linkRegex.exec(part))) {
        if (linkMatch.index > linkLastIndex) {
          linkParts.push(part.slice(linkLastIndex, linkMatch.index))
        }
        linkParts.push(
          <a key={`${keyPrefix}-link-${idx}-${linkCount}`} href={linkMatch[2]} className="underline hover:no-underline" target={linkMatch[2].startsWith('/') ? undefined : '_blank'} rel="noreferrer">
            {linkMatch[1]}
          </a>
        )
        linkLastIndex = linkMatch.index + linkMatch[0].length
        linkCount++
      }
      if (linkLastIndex < part.length) {
        linkParts.push(part.slice(linkLastIndex))
      }

      linkProcessedParts.push(...linkParts)
    })

    parts = linkProcessedParts

    // Then process code and italic on the string parts
    const finalParts: React.ReactNode[] = []
    parts.forEach((part, idx) => {
      if (typeof part !== 'string') {
        finalParts.push(part)
        return
      }

      // Process code
      const codeProcessed: React.ReactNode[] = []
      let codeLastIndex = 0
      let codeMatch: RegExpExecArray | null
      let codeCount = 0
      codeRegex.lastIndex = 0

      while ((codeMatch = codeRegex.exec(part))) {
        if (codeMatch.index > codeLastIndex) {
          codeProcessed.push(part.slice(codeLastIndex, codeMatch.index))
        }
        codeProcessed.push(
          <code key={`${keyPrefix}-code-${idx}-${codeCount}`} className="bg-muted px-1 py-0.5 rounded text-xs">{codeMatch[1]}</code>
        )
        codeLastIndex = codeMatch.index + codeMatch[0].length
        codeCount++
      }
      if (codeLastIndex < part.length) {
        codeProcessed.push(part.slice(codeLastIndex))
      }

      // Process italic on the results
      codeProcessed.forEach((codePart, codeIdx) => {
        if (typeof codePart !== 'string') {
          finalParts.push(codePart)
          return
        }

        const italicProcessed: React.ReactNode[] = []
        let italicLastIndex = 0
        let italicMatch: RegExpExecArray | null
        let italicCount = 0
        emRegex.lastIndex = 0

        while ((italicMatch = emRegex.exec(codePart))) {
          if (italicMatch.index > italicLastIndex) {
            italicProcessed.push(codePart.slice(italicLastIndex, italicMatch.index))
          }
          italicProcessed.push(
            <em key={`${keyPrefix}-em-${idx}-${codeIdx}-${italicCount}`}>{italicMatch[1]}</em>
          )
          italicLastIndex = italicMatch.index + italicMatch[0].length
          italicCount++
        }
        if (italicLastIndex < codePart.length) {
          italicProcessed.push(codePart.slice(italicLastIndex))
        }

        finalParts.push(...italicProcessed)
      })
    })

    return finalParts.length > 0 ? finalParts : [text]
  }

  const renderListItems = (items: ListItem[], keyPrefix: string): React.ReactNode[] => {
    return items.map((item, idx) => (
      <li key={`${keyPrefix}-${idx}`}>
        {renderInline(item.text, `${keyPrefix}-${idx}`)}
        {item.children && item.children.length > 0 && (
          <ul className="list-disc pl-6 space-y-1 mt-1" style={{ color: 'hsl(var(--content-foreground))' }}>
            {renderListItems(item.children, `${keyPrefix}-${idx}-child`)}
          </ul>
        )}
      </li>
    ))
  }

  return (
    <div className={className}>
      {blocks.map((b, idx) => {
        switch (b.type) {
          case 'heading': {
            const Tag = (`h${Math.min(6, Math.max(1, b.level))}` as unknown) as keyof JSX.IntrinsicElements
            const size = b.level === 1 ? 'text-4xl' : b.level === 2 ? 'text-2xl' : b.level === 3 ? 'text-xl' : 'text-lg'
            const spacing = b.level === 1 ? 'mt-2 mb-6' : 'mt-6 mb-3'
            return (
              <Tag key={idx} className={`${size} font-semibold ${spacing}`}>
                {renderInline(b.text, `h-${idx}`)}
              </Tag>
            )
          }
          case 'paragraph':
            return (
              <p key={idx} className="leading-7 mb-4" style={{ color: 'hsl(var(--content-foreground))' }}>
                {renderInline(b.text, `p-${idx}`)}
              </p>
            )
          case 'blockquote':
            return (
              <blockquote key={idx} className="text-center text-lg italic mb-6 mx-auto max-w-2xl" style={{ color: 'hsl(var(--content-foreground))' }}>
                {renderInline(b.text, `bq-${idx}`)}
              </blockquote>
            )
          case 'ul':
            return (
              <ul key={idx} className="list-disc pl-6 space-y-1 mb-4" style={{ color: 'hsl(var(--content-foreground))' }}>
                {renderListItems(b.items, `ul-${idx}`)}
              </ul>
            )
          case 'ol':
            return (
              <ol key={idx} className="list-decimal pl-6 space-y-1 mb-4" style={{ color: 'hsl(var(--content-foreground))' }}>
                {renderListItems(b.items, `ol-${idx}`)}
              </ol>
            )
          case 'code':
            return (
              <pre key={idx} className="bg-muted rounded-md p-4 overflow-auto text-sm mb-4">
                <code>{b.text}</code>
              </pre>
            )
          case 'plotly':
            return (
              <PlotlyCard key={idx} caption={b.caption} path={b.path} secondPath={b.secondPath} />
            )
          case 'footnote':
            // Calculate footnote number based on position in the footnotes object
            const footnoteKeys = Object.keys(footnotes)
            const footnoteIndex = footnoteKeys.indexOf(b.id)
            const footnoteNumber = footnoteIndex + 1
            return (
              <div key={idx} id={`footnote-${b.id}`} className="mb-3 p-3 bg-muted/30 rounded border-l-4 border-primary">
                <div className="flex items-start gap-2">
                  <span className="text-primary font-medium text-sm mt-0.5">[{footnoteNumber}]</span>
                  <div className="flex-1">
                    <span className="text-sm" style={{ color: 'hsl(var(--content-foreground))' }}>
                      {renderInline(b.text, `footnote-${idx}`)}
                    </span>
                    <button
                      onClick={() => {
                        const referenceElement = document.querySelector(`a[href="#footnote-${b.id}"]`)
                        if (referenceElement) {
                          referenceElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        }
                      }}
                      className="ml-2 text-primary hover:text-primary/80 text-xs underline"
                    >
                      ↑
                    </button>
                  </div>
                </div>
              </div>
            )
          default:
            return null
        }
      })}
    </div>
  )
}

export default MarkdownRenderer
