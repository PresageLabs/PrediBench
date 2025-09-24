import { BarChart3, Mail, Menu, Newspaper, TrendingUpDown, Trophy, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { ContactModal } from './ContactModal'
import { Footer } from './Footer'
import { ThemeToggle } from './ui/ThemeToggle'

interface LayoutProps {
  children: ReactNode
  currentPage?: string
}

export function Layout({ children, currentPage }: LayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isContactModalOpen, setIsContactModalOpen] = useState(false)

  // Make the contact modal handler globally available
  useEffect(() => {
    (window as any).openContactModal = () => setIsContactModalOpen(true)
    return () => {
      delete (window as any).openContactModal
    }
  }, [])

  const pages = [
    { id: 'leaderboard', name: 'Leaderboard', href: '/leaderboard', icon: Trophy },
    { id: 'models', name: 'Models', href: '/models', icon: BarChart3 },
    { id: 'events', name: 'Events', href: '/events', icon: Newspaper }
  ]

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header and Navigation */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <a href="/" className="text-2xl font-bold tracking-tight hover:text-muted-foreground transition-colors flex items-center gap-2">
                PrediBench
                <TrendingUpDown size={24} />
              </a>
              <p className="text-sm text-muted-foreground hidden md:block">
                LLMs bet on the future
              </p>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-3">
              <nav className="flex items-center space-x-1">
                {pages.map((page) => (
                  <a
                    key={page.id}
                    href={page.href}
                    className={`
                      px-3 py-2 font-medium text-sm transition-colors duration-200
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
                  </a>
                ))}
                <button
                  onClick={() => setIsContactModalOpen(true)}
                  className="px-3 py-2 font-medium text-sm transition-colors duration-200 text-blue-500 hover:text-blue-600"
                >
                  <div className="flex items-center space-x-2">
                    <Mail size={16} />
                    <span>Contact</span>
                  </div>
                </button>
              </nav>
              <ThemeToggle />
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-md hover:bg-accent transition-colors"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>

          {/* Mobile Navigation Menu */}
          {isMobileMenuOpen && (
            <div className="md:hidden mt-4 border-t border-border pt-4">
              <nav className="flex flex-col space-y-2">
                {pages.map((page) => (
                  <a
                    key={page.id}
                    href={page.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`
                      px-3 py-2 font-medium text-sm transition-colors duration-200 rounded-md
                      ${currentPage === page.id
                        ? 'text-foreground bg-accent'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                      }
                    `}
                  >
                    <div className="flex items-center space-x-2">
                      {page.icon && <page.icon size={16} />}
                      <span>{page.name}</span>
                    </div>
                  </a>
                ))}
                <button
                  onClick={() => {
                    setIsContactModalOpen(true)
                    setIsMobileMenuOpen(false)
                  }}
                  className="px-3 py-2 font-medium text-sm transition-colors duration-200 rounded-md text-blue-500 hover:text-blue-600 hover:bg-accent text-left"
                >
                  <div className="flex items-center space-x-2">
                    <Mail size={16} />
                    <span>Contact</span>
                  </div>
                </button>
                <div className="px-3 py-2">
                  <ThemeToggle />
                </div>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Page Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <Footer onContactClick={() => setIsContactModalOpen(true)} />


      {/* Contact Modal */}
      <ContactModal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
      />
    </div>
  )
}
