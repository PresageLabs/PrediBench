import React, { useState, useEffect, useCallback } from 'react'

interface TocItem {
  id: string
  title: string
  level: number
}

interface TableOfContentsProps {
  content: string
  className?: string
}

export function TableOfContents({ content, className }: TableOfContentsProps) {
  const [tocItems, setTocItems] = useState<TocItem[]>([])
  const [activeId, setActiveId] = useState<string>('')

  useEffect(() => {
    const lines = content.replace(/\r\n?/g, '\n').split('\n')
    const items: TocItem[] = []

    lines.forEach((line) => {
      const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
      if (headingMatch) {
        const level = headingMatch[1].length
        const title = headingMatch[2].trim()
        const id = title
          .toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '')
          .replace(/\s+/g, '-')
          .replace(/-+/g, '-')
          .replace(/^-|-$/g, '')

        items.push({ id, title, level })
      }
    })

    setTocItems(items)
  }, [content])

  useEffect(() => {
    const handleScroll = () => {
      const headingElements = tocItems.map(item => ({
        id: item.id,
        element: document.getElementById(item.id)
      })).filter(item => item.element !== null)

      const scrollPosition = window.scrollY + 100

      let currentActiveId = ''

      for (let i = headingElements.length - 1; i >= 0; i--) {
        const heading = headingElements[i]
        if (heading.element) {
          const { top } = heading.element.getBoundingClientRect()
          const absoluteTop = top + window.scrollY

          if (scrollPosition >= absoluteTop) {
            currentActiveId = heading.id
            break
          }
        }
      }

      if (!currentActiveId && headingElements.length > 0) {
        currentActiveId = headingElements[0].id
      }

      if (currentActiveId !== activeId) {
        setActiveId(currentActiveId)
      }
    }

    handleScroll()

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [tocItems, activeId])

  const scrollToSection = useCallback((id: string) => {
    const element = document.getElementById(id)
    if (element) {
      const offsetTop = element.getBoundingClientRect().top + window.scrollY - 80

      window.scrollTo({
        top: offsetTop,
        behavior: 'smooth'
      })

      setTimeout(() => {
        setActiveId(id)
      }, 100)
    }
  }, [])

  if (tocItems.length === 0) {
    return null
  }

  return (
    <nav className={`${className} sticky top-4`}>
      <div className="bg-background border border-border rounded-lg p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground mb-3">Table of Contents</h3>
        <ul className="space-y-1 text-sm">
          {tocItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => scrollToSection(item.id)}
                className={`
                  block w-full text-left transition-colors duration-200 rounded px-2 py-1
                  ${item.level === 2 ? 'pl-0' : item.level === 3 ? 'pl-4' : item.level === 4 ? 'pl-8' : 'pl-12'}
                  ${activeId === item.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }
                `}
              >
                {item.title}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}