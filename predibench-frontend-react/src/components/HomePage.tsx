import { TrendingUpDown } from 'lucide-react'
import type { Event, LeaderboardEntry } from '../api'
import { FeaturedEvents } from './FeaturedEvents'
import { LeaderboardTable } from './LeaderboardTable'
import { RedirectButton } from './ui/redirect-button'

interface HomePageProps {
  leaderboard: LeaderboardEntry[]
  events: Event[]
  loading?: boolean
}

export function HomePage({ leaderboard, events, loading = false }: HomePageProps) {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Title and Subtitle */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4 flex items-center justify-center gap-3">
          PrediBench
          <TrendingUpDown size={36} />
        </h1>
        <p className="text-lg text-muted-foreground">LLMs bet money on the future!</p>
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

      {/* About Section */}
      <div className="mb-16">
        <div className="text-center mb-8">
          <div className="w-full h-px bg-border mb-8"></div>
          <h2 className="text-2xl font-bold">About</h2>
        </div>
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-muted-foreground mb-6">
            Welcome to PrediBench - the premier platform for evaluating AI model performance in prediction markets.
            Our benchmark tests how well different language models can analyze market conditions, assess probabilities,
            and make profitable trading decisions. Track real-time performance metrics and see which models excel
            at understanding complex market dynamics.
          </p>
          <div className="text-center">
            <RedirectButton href="/about">
              More detail on the benchmark
            </RedirectButton>
          </div>
        </div>
      </div>

      {/* Featured Events */}
      <div>
        <div className="w-full h-px bg-border mb-8"></div>
        <FeaturedEvents
          events={events}
          loading={loading}
          showTitle={true}
          maxEvents={6}
          showFilters={false}
        />
      </div>
    </div>
  )
}