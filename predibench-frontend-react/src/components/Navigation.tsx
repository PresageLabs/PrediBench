import { Trophy, CircleHelp } from 'lucide-react'
import { useAnalytics } from '../hooks/useAnalytics'

interface NavigationProps {
  currentPage: string
  onPageChange: (page: string) => void
}

interface Page {
  id: string
  name: string
  icon: any
  isExternal?: boolean
  href?: string
}

export function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const { trackUserAction } = useAnalytics()
  
  const pages: Page[] = [
    { id: 'about', name: 'About', icon: CircleHelp, isExternal: true, href: '/#predibench-testing-ai-models-on-prediction-markets' },
    { id: 'leaderboard', name: 'Leaderboard', icon: Trophy },
    { id: 'models', name: 'Models', icon: null },
    { id: 'events', name: 'Events', icon: null }
  ]

  const handlePageChange = (pageId: string, isExternal?: boolean, href?: string) => {
    trackUserAction('navigation_click', 'navigation', pageId)
    if (isExternal && href) {
      window.location.href = href
    } else {
      onPageChange(pageId)
    }
  }

  return (
    <nav className="flex items-center space-x-1">
      {pages.map((page) => (
        <button
          key={page.id}
          onClick={() => handlePageChange(page.id, page.isExternal, page.href)}
          className={`
            px-4 py-2 font-medium text-sm transition-colors duration-200
            ${currentPage === page.id
              ? 'text-foreground'
              : 'text-muted-foreground hover:text-foreground'
            }
          `}
        >
          <div className="flex items-center space-x-2">
            {page.icon && <page.icon size={16} />}
            <span>{page.name}</span>
          </div>
        </button>
      ))}
    </nav>
  )
}