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
      <div className="mb-16 max-w-3xl mx-auto" id="about">
        <MarkdownRenderer content={aboutContent} />
      </div>
    </div>
  )
}
