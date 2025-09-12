import { TrendingUpDown } from 'lucide-react'
import type { LeaderboardEntry } from '../api'
import MarkdownRenderer from '../lib/MarkdownRenderer'
import { LeaderboardTable } from './LeaderboardTable'
import { RedirectButton } from './ui/redirect-button'
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
          PrediBench
          <TrendingUpDown size={36} />
        </h1>
        <p className="text-lg text-muted-foreground">We give LLMs money, and let them bet on the future.</p>
      </div>

      {/* Leaderboard Table */}
      <div className="mb-16">
        <LeaderboardTable
          leaderboard={leaderboard}
          loading={loading}
          initialVisibleModels={10}
        />
        <div className="text-center mt-6">
          <RedirectButton href="/leaderboard">
            Detailed leaderboard and profit curves
          </RedirectButton>
        </div>
      </div>

      {/* Intro Section (moved from About page) */}
      <div className="mb-16" id="intro">
        <div className="text-center mb-8">
          <div className="w-full h-px bg-border mb-8"></div>
          <h2 className="text-2xl font-bold">Intro</h2>
        </div>
        <div className="max-w-3xl mx-auto">
          <MarkdownRenderer content={aboutContent} />
        </div>
      </div>

      {/* Featured Events removed as requested */}
    </div>
  )
}
