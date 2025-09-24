import type { LeaderboardEntry } from '../api'
import MarkdownRenderer from '../lib/MarkdownRenderer'
import { LeaderboardTable } from './LeaderboardTable'
import { TableOfContents } from './TableOfContents'
// eslint-disable-next-line import/no-relative-packages
import aboutContent from '../content/about.md?raw'

interface HomePageProps {
  leaderboard: LeaderboardEntry[]
  loading?: boolean
}

export function HomePage({ leaderboard, loading = false }: HomePageProps) {
  return (
    <div className="container mx-auto px-4 py-4">
      {/* Page Title and Subtitle */}
      <div className="text-center mb-8 mt-6">
        <h1 className="text-4xl font-bold mb-4 flex items-center justify-center gap-3">
          PrediBench: AI models bet on the future
        </h1>
        <p>We let AI models bet on Polymarket, and track their performance.</p>
      </div>

      {/* Leaderboard Table */}
      <div className="mb-16">
        <LeaderboardTable
          leaderboard={leaderboard}
          loading={loading}
          initialVisibleModels={10}
        />
        <div className="text-center mt-6 space-y-3 md:hidden">
          <div className="text-sm text-muted-foreground">
            Quick links:
            <a href="#methods" className="text-primary hover:underline mx-2">Methods</a>•
            <a href="#metrics" className="text-primary hover:underline mx-2">Metrics</a>•
            <a href="#results" className="text-primary hover:underline mx-2">Results</a>•
            <a href="#how-an-agent-runs" className="text-primary hover:underline mx-2">How Agents Work</a>
          </div>
        </div>
      </div>

      {/* Intro Section (moved from About page) */}
      <div className="mb-16" id="about">
        <div className="flex gap-8 max-w-7xl mx-auto min-w-0">
          {/* Table of Contents */}
          <div className="hidden lg:block w-64 flex-shrink-0">
            <TableOfContents content={aboutContent} />
          </div>

          {/* Main Content */}
          <div className="flex-1 max-w-3xl min-w-0">
            <div className="min-w-0 max-w-full">
              <MarkdownRenderer content={aboutContent} />
            </div>

            {/* Back to top button */}
            <div className="text-center mt-12 pt-8 border-t border-border">
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-sm text-primary hover:underline"
              >
                ↑ Back to top
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* X.com Social Link - Bottom Right */}
      <div className="fixed bottom-8 right-8 z-50">
        <a
          aria-label="Follow Presage Labs on X"
          href="https://x.com/presage_labs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center w-12 h-12 bg-background border border-border rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110 text-muted-foreground hover:text-foreground"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13.3021 10.8029L17.5685 5.84351L17.7862 5.59053H17.4524H16.4233H16.353L16.3072 5.64379L12.6657 9.87668L9.76624 5.65694L9.72061 5.59053H9.64004H6.16602H5.87501L6.03981 5.83037L10.5278 12.362L6.04994 17.5668L5.83228 17.8198H6.16602H7.19527H7.26553L7.31135 17.7666L11.1641 13.288L14.2325 17.7534L14.2781 17.8198H14.3587H17.8327H18.1237L17.9589 17.58L13.3021 10.8029ZM14.9226 16.774L11.8527 12.3829V12.3826L11.8251 12.3431L11.3636 11.6831L11.3636 11.683L7.86001 6.67158H9.06721L11.9848 10.845L11.9848 10.845L12.4463 11.5051L12.4463 11.5051L16.1299 16.774H14.9226Z" fill="currentColor" stroke="currentColor" strokeWidth="0.30625" />
          </svg>
        </a>
      </div>
    </div>
  )
}
