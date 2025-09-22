import { Search, ChevronDown } from 'lucide-react'
import { useEffect, useMemo, useState, useRef } from 'react'
import type { Event, LeaderboardEntry, ModelInvestmentDecision } from '../api'
import { apiService } from '../api'
import { EventCard } from './EventCard'
import { FeaturedEvents } from './FeaturedEvents'
import { Card, CardContent, CardHeader } from './ui/card'

interface EventsPageProps {
  events: Event[]
  leaderboard: LeaderboardEntry[]
  loading?: boolean
}

export function EventsPage({ events, loading: initialLoading = false }: EventsPageProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'volume' | 'probability' | 'endDate'>('volume')
  const [orderBy, setOrderBy] = useState<'asc' | 'desc'>('desc')
  const [isLive, setIsLive] = useState(false)
  const [selectedTag, setSelectedTag] = useState<string>('')
  const [tagDropdownOpen, setTagDropdownOpen] = useState(false)
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false)
  const [orderDropdownOpen, setOrderDropdownOpen] = useState(false)
  const tagDropdownRef = useRef<HTMLDivElement>(null)
  const sortDropdownRef = useRef<HTMLDivElement>(null)
  const orderDropdownRef = useRef<HTMLDivElement>(null)

  // Featured Events (latest ModelInvestmentDecisions batch)
  const [featuredEventIds, setFeaturedEventIds] = useState<string[]>([])
  const [featuredLoading, setFeaturedLoading] = useState<boolean>(false)

  useEffect(() => {
    let cancelled = false
    const loadFeatured = async () => {
      try {
        setFeaturedLoading(true)
        const dates = await apiService.getPredictionDates()
        if (!dates || dates.length === 0) {
          if (!cancelled) setFeaturedEventIds([])
          return
        }
        const latest = dates.sort((a, b) => b.localeCompare(a))[0]
        const results: ModelInvestmentDecision[] = await apiService.getModelResultsByDate(latest)
        const ids = new Set<string>()
        results.forEach(r => r.event_investment_decisions.forEach(ed => ids.add(ed.event_id)))
        if (!cancelled) setFeaturedEventIds(Array.from(ids))
      } catch (e) {
        console.warn('Failed to load featured events', e)
        if (!cancelled) setFeaturedEventIds([])
      } finally {
        if (!cancelled) setFeaturedLoading(false)
      }
    }
    loadFeatured()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tagDropdownRef.current && !tagDropdownRef.current.contains(event.target as Node)) {
        setTagDropdownOpen(false)
      }
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(event.target as Node)) {
        setSortDropdownOpen(false)
      }
      if (orderDropdownRef.current && !orderDropdownRef.current.contains(event.target as Node)) {
        setOrderDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const featuredEvents = useMemo(() => {
    if (!featuredEventIds.length) return []
    const idSet = new Set(featuredEventIds)
    return events.filter(e => idSet.has(e.id))
  }, [events, featuredEventIds])


  // Rank tags by frequency (after capitalization) and keep top 7
  function capitalizeWords(str: string): string {
    return str
      .split(/\s+/)
      .map(word => {
        // If word is all caps, leave it
        if (word === word.toUpperCase()) return word;
        // Else capitalize first letter, lowercase rest
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      })
      .join(" ");
  }

  const tagCounts = new Map<string, number>();

  for (const tag of events.flatMap(e => e.tags ?? []).map(t => capitalizeWords(t))) {
    tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1);
  }

  const topTags = [...tagCounts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])) // freq desc, then alpha
    .slice(0, 7)
    .map(([tag]) => tag);


  // Filter and sort events
  const filteredAndSortedEvents = events
    .filter(event => {
      const matchesSearch = searchQuery === '' ||
        event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.markets?.some(market =>
          market.question?.toLowerCase().includes(searchQuery.toLowerCase())
        )

      const matchesStatus = isLive ? (event.end_datetime ? new Date(event.end_datetime) > new Date() : true) : true

      const matchesTag = selectedTag === '' || (event.tags && event.tags.includes(selectedTag))

      return matchesSearch && matchesStatus && matchesTag
    })
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'volume':
          comparison = (a.volume || 0) - (b.volume || 0)
          break
        case 'probability': {
          // Use average probability of markets
          const aAvgProb = a.markets?.reduce((sum, m) => sum + (m.outcomes[0].price), 0) / (a.markets.length)
          const bAvgProb = b.markets?.reduce((sum, m) => sum + (m.outcomes[0].price), 0) / (b.markets.length)
          comparison = (aAvgProb) - (bAvgProb)
          break
        }
        case 'endDate':
          comparison = new Date(a.end_datetime || '').getTime() - new Date(b.end_datetime || '').getTime()
          break
      }
      return orderBy === 'desc' ? -comparison : comparison
    })


  return (
    <div className="container mx-auto px-4 py-8">
      {/* Featured Events (latest decisions) */}
      {(featuredLoading || featuredEvents.length > 0) && (
        <div className="mb-10">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold">Featured Events</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Latest prediction markets being analyzed. <a href="/#news-and-prediction-markets-importance-of-actualisation" className="text-primary hover:underline">Why these markets matter →</a>
            </p>
          </div>
          <FeaturedEvents
            events={featuredEvents}
            loading={featuredLoading}
            showTitle={false}
            showFilters={false}
            maxEvents={featuredEvents.length || 6}
          />
          <div className="w-full h-px bg-border mt-10"></div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="text-center mb-4">
        <h2 className="text-2xl font-bold">Search all events</h2>
        <p className="text-sm text-muted-foreground mt-2">
          Browse prediction markets from Polymarket. <a href="/#investment-process" className="text-primary hover:underline">See how models analyze these events →</a>
        </p>
      </div>
      <div className="mb-8 space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search events by title, topic, ticker, or markets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Tag Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Tag:</span>
            <div className="relative" ref={tagDropdownRef}>
              <button
                onClick={() => setTagDropdownOpen(!tagDropdownOpen)}
                disabled={topTags.length === 0}
                className="text-sm font-medium border border-border rounded-md px-3 py-1 bg-background text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors cursor-pointer flex items-center gap-2 min-w-[100px] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="truncate">
                  {selectedTag || 'All tags'}
                </span>
                <ChevronDown className={`h-3 w-3 transition-transform ${tagDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {tagDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full bg-background border border-border rounded-md overflow-hidden z-50 min-w-[100px]">
                  <button
                    onClick={() => {
                      setSelectedTag('')
                      setTagDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    All tags
                  </button>
                  {topTags.length === 0 ? (
                    <div className="w-full text-left text-sm font-medium px-3 py-1 text-muted-foreground">
                      No tags available
                    </div>
                  ) : (
                    topTags.map(tag => (
                      <button
                        key={tag}
                        onClick={() => {
                          setSelectedTag(tag)
                          setTagDropdownOpen(false)
                        }}
                        className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                      >
                        {tag}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sort By */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Sort by:</span>
            <div className="relative" ref={sortDropdownRef}>
              <button
                onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
                className="text-sm font-medium border border-border rounded-md px-3 py-1 bg-background text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors cursor-pointer flex items-center gap-2 min-w-[100px]"
              >
                <span>
                  {sortBy === 'volume' ? 'Volume' :
                   sortBy === 'probability' ? 'Probability' : 'End Date'}
                </span>
                <ChevronDown className={`h-3 w-3 transition-transform ${sortDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {sortDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full bg-background border border-border rounded-md overflow-hidden z-50">
                  <button
                    onClick={() => {
                      setSortBy('volume')
                      setSortDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    Volume
                  </button>
                  <button
                    onClick={() => {
                      setSortBy('probability')
                      setSortDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    Probability
                  </button>
                  <button
                    onClick={() => {
                      setSortBy('endDate')
                      setSortDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    End Date
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Order */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Order:</span>
            <div className="relative" ref={orderDropdownRef}>
              <button
                onClick={() => setOrderDropdownOpen(!orderDropdownOpen)}
                className="text-sm font-medium border border-border rounded-md px-3 py-1 bg-background text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-colors cursor-pointer flex items-center gap-2 min-w-[110px]"
              >
                <span>
                  {orderBy === 'desc' ? 'High to Low' : 'Low to High'}
                </span>
                <ChevronDown className={`h-3 w-3 transition-transform ${orderDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {orderDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full bg-background border border-border rounded-md overflow-hidden z-50">
                  <button
                    onClick={() => {
                      setOrderBy('desc')
                      setOrderDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    High to Low
                  </button>
                  <button
                    onClick={() => {
                      setOrderBy('asc')
                      setOrderDropdownOpen(false)
                    }}
                    className="w-full text-left text-sm font-medium px-3 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    Low to High
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Live/All Toggle */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">Status:</span>
            <button
              onClick={() => setIsLive(!isLive)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isLive
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
                }`}
            >
              {isLive ? 'Live' : 'All'}
            </button>
          </div>
        </div>
      </div>

      {/* Loading Spinner when initially loading */}
      {initialLoading && events.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
            <div className="text-sm text-muted-foreground">Loading events...</div>
          </div>
        </div>
      )}

      {/* Events Grid with Loading States */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {initialLoading && events.length === 0 ? (
          // Show skeleton loading cards while loading
          Array.from({ length: 6 }).map((_, index) => (
            <Card key={index}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
                    <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4"></div>
                  </div>
                  <div className="flex space-x-2 ml-2">
                    <div className="h-6 w-16 bg-gray-200 rounded-full animate-pulse"></div>
                    <div className="h-6 w-12 bg-gray-200 rounded-full animate-pulse"></div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="h-3 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-3 bg-gray-200 rounded animate-pulse w-5/6"></div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-4">
                  <div>
                    <div className="h-3 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="space-y-1">
                      {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-20"></div>
                          <div className="h-3 bg-gray-200 rounded animate-pulse w-12"></div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t pt-3">
                    <div className="flex space-x-4">
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-12"></div>
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-16"></div>
                    </div>
                    <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : filteredAndSortedEvents.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-muted-foreground">No events found matching your search criteria.</p>
          </div>
        ) : (
          filteredAndSortedEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))
        )}
      </div>
    </div>
  )
}
