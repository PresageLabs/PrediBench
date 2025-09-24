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
    </div>
  )
}
