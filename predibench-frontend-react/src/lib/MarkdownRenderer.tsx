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
// This avoids adding a new dependency while keeping content readable.
export function MarkdownRenderer({ content, className }: Props) {
  const lines = content.replace(/\r\n?/g, '\n').split('\n')

  type Block =
    | { type: 'heading'; level: number; text: string }
    | { type: 'paragraph'; text: string }
    | { type: 'ul'; items: string[] }
    | { type: 'ol'; items: string[] }
    | { type: 'code'; text: string }
    | { type: 'plotly'; caption: string; path: string }

  const blocks: Block[] = []
  let i = 0
  let inCode = false
  let codeBuffer: string[] = []
  let paraBuffer: string[] = []
  let listBuffer: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const flushParagraph = () => {
    if (paraBuffer.length) {
      blocks.push({ type: 'paragraph', text: paraBuffer.join(' ') })
      paraBuffer = []
    }
  }
  const flushList = () => {
    if (listType && listBuffer.length) {
      blocks.push({ type: listType, items: listBuffer })
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

    // Custom Plotly embed: {caption="...", path=...}
    const embedMatch = line.trim().match(/^\{([^}]*)\}$/)
    if (embedMatch) {
      flushParagraph()
      flushList()
      const inner = embedMatch[1]
      // capture caption="..."
      const capMatch = inner.match(/caption\s*=\s*"([^"]+)"/)
      // capture path=... (quoted or unquoted, until comma or end)
      const pathMatch = inner.match(/path\s*=\s*("([^"]+)"|[^,\s}]+)/)
      const caption = capMatch?.[1]?.trim()
      const path = (pathMatch?.[2] || pathMatch?.[1])?.replace(/^"|"$/g, '').trim()
      if (caption && path) {
        blocks.push({ type: 'plotly', caption, path })
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

    // Lists
    const ulMatch = line.match(/^\s*[-*]\s+(.*)$/)
    const olMatch = line.match(/^\s*\d+\.\s+(.*)$/)
    if (ulMatch || olMatch) {
      flushParagraph()
      const item = (ulMatch ? ulMatch[1] : olMatch![1]).trim()
      const type: 'ul' | 'ol' = ulMatch ? 'ul' : 'ol'
      if (listType && listType !== type) {
        // switch list type
        flushList()
      }
      listType = type
      listBuffer.push(item)
      i++
      continue
    }

    // Default: accumulate paragraph
    paraBuffer.push(line.trim())
    i++
  }

  // Final flush
  flushParagraph()
  flushList()
  if (inCode) flushCode()

  const renderInline = (text: string, keyPrefix: string) => {
    // Links
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const codeRegex = /`([^`]+)`/g
    const strongRegex = /\*\*([^*]+)\*\*/g
    const emRegex = /\*([^*]+)\*/g

    // Process progressively to avoid nesting conflicts. We'll split into tokens.
    // Start with links
    let parts: React.ReactNode[] = []
    let lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = linkRegex.exec(text))) {
      if (m.index > lastIndex) parts.push(text.slice(lastIndex, m.index))
      parts.push(
        <a key={`${keyPrefix}-link-${parts.length}`} href={m[2]} className="underline hover:no-underline" target={m[2].startsWith('/') ? undefined : '_blank'} rel="noreferrer">
          {m[1]}
        </a>
      )
      lastIndex = m.index + m[0].length
    }
    if (lastIndex < text.length) parts.push(text.slice(lastIndex))

    const applyRegex = (nodes: React.ReactNode[], regex: RegExp, render: (match: string, i: number) => React.ReactNode) => {
      const out: React.ReactNode[] = []
      nodes.forEach((node) => {
        if (typeof node !== 'string') {
          out.push(node)
          return
        }
        let last = 0
        let mm: RegExpExecArray | null
        let count = 0
        while ((mm = regex.exec(node))) {
          if (mm.index > last) out.push(node.slice(last, mm.index))
          out.push(render(mm[1], count++))
          last = mm.index + mm[0].length
        }
        if (last < node.length) out.push(node.slice(last))
      })
      return out
    }

    // Inline code, bold, italic
    parts = applyRegex(parts, codeRegex, (match, i) => (
      <code key={`${keyPrefix}-code-${i}`} className="bg-muted px-1 py-0.5 rounded text-xs">{match}</code>
    ))
    parts = applyRegex(parts, strongRegex, (match, i) => (
      <strong key={`${keyPrefix}-strong-${i}`}>{match}</strong>
    ))
    parts = applyRegex(parts, emRegex, (match, i) => (
      <em key={`${keyPrefix}-em-${i}`}>{match}</em>
    ))

    return parts
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
              <p key={idx} className="text-muted-foreground leading-7 mb-4">
                {renderInline(b.text, `p-${idx}`)}
              </p>
            )
          case 'ul':
            return (
              <ul key={idx} className="list-disc pl-6 space-y-1 mb-4">
                {b.items.map((it, i2) => (
                  <li key={i2}>{renderInline(it, `ul-${idx}-${i2}`)}</li>
                ))}
              </ul>
            )
          case 'ol':
            return (
              <ol key={idx} className="list-decimal pl-6 space-y-1 mb-4">
                {b.items.map((it, i2) => (
                  <li key={i2}>{renderInline(it, `ol-${idx}-${i2}`)}</li>
                ))}
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
              <PlotlyCard key={idx} caption={b.caption} path={b.path} />
            )
          default:
            return null
        }
      })}
    </div>
  )
}

export default MarkdownRenderer
