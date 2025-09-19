import { Search, ChevronDown } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { Event } from '../api'
import { EventCard } from './EventCard'
import { Card, CardContent, CardHeader } from './ui/card'

interface FeaturedEventsProps {
  events: Event[]
  loading?: boolean
  showTitle?: boolean
  maxEvents?: number
  showFilters?: boolean
}

export function FeaturedEvents({
  events,
  loading = false,
  showTitle = true,
  maxEvents = 6,
  showFilters = true
}: FeaturedEventsProps) {
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

  // Get unique tags from all events
  const uniqueTags = Array.from(new Set(events.flatMap(event => event.tags || []))).sort()

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

      // Only show events with markets that have multiple datapoints in their timeseries
      const hasMultipleDatapoints = event.markets?.some(market =>
        market.prices && market.prices.length > 1
      ) ?? false

      return matchesSearch && matchesStatus && matchesTag && hasMultipleDatapoints
    })
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'volume':
          comparison = (a.volume || 0) - (b.volume || 0)
          break
        case 'probability': {
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
    <div>
      {showTitle && (
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-4">
            <h2 className="text-2xl font-bold">Featured Events</h2>
            <Link
              to="/events"
              className="text-primary hover:text-primary/80 transition-colors font-medium"
            >
              View all →
            </Link>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      {showFilters && (
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
                  disabled={uniqueTags.length === 0}
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
                    {uniqueTags.length === 0 ? (
                      <div className="w-full text-left text-sm font-medium px-3 py-1 text-muted-foreground">
                        No tags available
                      </div>
                    ) : (
                      uniqueTags.map(tag => (
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
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${isLive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}
              >
                {isLive ? 'Live' : 'All'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Spinner when initially loading */}
      {loading && events.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto mb-2"></div>
            <div className="text-sm text-muted-foreground">Loading events...</div>
          </div>
        </div>
      )}

      {/* Events Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading && events.length === 0 ? (
          Array.from({ length: maxEvents }).map((_, index) => (
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
              </CardHeader>
              <CardContent className="pt-0">
                <div className="h-20 bg-gray-200 rounded animate-pulse"></div>
              </CardContent>
            </Card>
          ))
        ) : filteredAndSortedEvents.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <p className="text-muted-foreground">No events found matching your search criteria.</p>
          </div>
        ) : (
          filteredAndSortedEvents.slice(0, maxEvents).map((event) => (
            <EventCard key={event.id} event={event} />
          ))
        )}
      </div>
    </div>
  )
}