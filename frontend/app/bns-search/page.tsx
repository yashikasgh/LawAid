// app/bns-search/page.tsx
'use client'

import { useState } from 'react'
import { Search, Scale, AlertCircle, Loader2 } from 'lucide-react'
import Navbar from '@/components/Navbar'
import { bnsAPI } from '@/lib/api'

type BNSResult = {
  section: string
  title: string
  similarity: number
  clause?: string
  text?: string
  chapter?: string
  bailable?: string
  cognizable?: string
  rank?: number
  items?: BNSResult[]
}

type BNSResponse = {
  status: string
  results: BNSResult[]
}

export function groupBnsResults(rawResults: BNSResult[]): BNSResult[] {
  if (!rawResults || rawResults.length === 0) return []

  const groupsMap = new Map<string, BNSResult[]>()

  for (const item of rawResults) {
    const match = item.section ? String(item.section).match(/\b\d+\b/) : null
    const canonicalKey = match ? match[0] : (item.section || '').trim().toLowerCase()

    if (!groupsMap.has(canonicalKey)) {
      groupsMap.set(canonicalKey, [])
    }
    groupsMap.get(canonicalKey)!.push(item)
  }

  const grouped: BNSResult[] = []

  for (const [key, items] of groupsMap.entries()) {
    const sortedItems = [...items].sort((a, b) => b.similarity - a.similarity)
    const best = sortedItems[0]
    const displaySection = key.match(/^\d+$/) ? key : (best.section || key)

    grouped.push({
      ...best,
      section: displaySection,
      items: sortedItems,
    })
  }

  return grouped.sort((a, b) => b.similarity - a.similarity)
}

export default function BNSSearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<BNSResult[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async () => {
    const trimmedQuery = query.trim()

    if (trimmedQuery.length < 3) {
      setError('Please enter at least 3 characters to search.')
      setResults([])
      setStatus('')
      return
    }

    setLoading(true)
    setError('')
    setResults([])
    setStatus('')

    try {
      const response = await bnsAPI.search(trimmedQuery)
      const data: BNSResponse = response.data

      setStatus(data.status)
      const raw = data.results || []
      setResults(groupBnsResults(raw))
    } catch (err: any) {
      console.error('BNS search failed:', err)

      setError(
        err?.response?.data?.detail ||
          'Unable to search the BNS database. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <>
      <Navbar />

      <main className="relative min-h-[calc(100vh-64px)] overflow-hidden text-[#12335B]">

        {/* Background */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-feature-bg.png"
            alt="LawAid legal background"
            className="h-full w-full object-cover object-center"
          />
        </div>

        {/* Light overlay */}
        <div className="fixed inset-0 -z-10 bg-[#f8f6f1]/10" />

        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-10">

          {/* Page Header */}
          <div className="mb-8">

            <div className="flex items-center gap-3 mb-4">
              <span className="h-px w-10 bg-[#b98528]" />

              <span className="text-[11px] tracking-[0.3em] uppercase text-white font-medium">
                LEGAL RESEARCH
              </span>
            </div>

            <div className="flex items-start gap-5">

              <div className="w-14 h-14 shrink-0 rounded-[14px] border border-[#d2a14b]/50 bg-white/75 backdrop-blur-md flex items-center justify-center shadow-sm">
                <Scale className="h-7 w-7 text-[#b98528]" />
              </div>

              <div>
                <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                  BNS Section Search
                </h1>

                <p className="mt-3 text-[#dca45a] text-sm md:text-base">
                  Search for relevant Bharatiya Nyaya Sanhita sections.
                </p>
              </div>

            </div>
          </div>

          {/* Search card */}
          <section className="rounded-[20px] border border-white/70 bg-white/75 backdrop-blur-md p-6 sm:p-8 shadow-[0_15px_40px_rgba(18,51,91,0.12)]">

            <div className="mb-6">
              <h2 className="font-serif text-2xl font-semibold text-[#12335B]">
                Find a relevant section
              </h2>

              <div className="mt-3 h-px w-12 bg-[#b98528]" />

              <p className="mt-3 text-sm text-[#56718f]">
                Enter an offence, incident, or legal description.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">

              <div className="relative flex-1">

                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#7890a8]" />

                <input
                  type="text"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. cheating, criminal intimidation..."
                  className="w-full rounded-[14px] border border-[#d9d4ca] bg-white/85 py-3.5 pl-11 pr-4 text-sm text-[#315b82] outline-none transition placeholder:text-[#7890a8] focus:border-[#b98528] focus:ring-2 focus:ring-[#b98528]/15"
                />

              </div>

              <button
                type="button"
                onClick={handleSearch}
                disabled={loading}
                className="inline-flex items-center justify-center gap-2 rounded-[14px] bg-[#b98528] px-7 py-3.5 text-sm font-semibold text-white transition hover:bg-[#9f7020] hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Search
                  </>
                )}
              </button>

            </div>

            {/* Validation / API error */}
            {error && (
              <div className="mt-5 flex items-start gap-3 rounded-[14px] border border-red-200 bg-red-50/90 p-4 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

          </section>

          {/* Results */}
          {results.length > 0 && (
            <section className="mt-9">

              <div className="grid gap-4">

                {results.map((result) => (
                  <article
                    key={result.section}
                    className="rounded-[18px] border border-white/70 bg-white/80 backdrop-blur-md p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] transition hover:-translate-y-0.5 hover:shadow-[0_20px_45px_rgba(18,51,91,0.15)]"
                  >

                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

                      <div className="flex gap-4">

                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[12px] border border-[#d2a14b]/40 bg-[#f8f6f1]/90">
                          <Scale className="h-6 w-6 text-[#b98528]" />
                        </div>

                        <div>

                          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-[#7890a8]">
                            BNS Section
                          </p>

                          <h3 className="mt-1 font-serif text-2xl font-semibold text-[#12335B]">
                            Section {result.section}
                          </h3>

                          <p className="mt-1 text-base font-medium text-[#315b82]">
                            {result.title}
                          </p>

                        </div>

                      </div>

                      <div className="rounded-[14px] border border-green-200 bg-green-50/80 px-4 py-2 text-left sm:text-right">

                        <p className="text-xs font-medium text-[#7890a8]">
                          Similarity
                        </p>

                        <p className="text-lg font-bold text-green-700">
                          {(result.similarity * 100).toFixed(0)}%
                        </p>

                      </div>

                    </div>

                  </article>
                ))}

              </div>
            </section>
          )}

          {/* Insufficient information */}
          {!loading &&
            !error &&
            status === 'insufficient_information' && (
              <section className="mt-8 rounded-[18px] border border-amber-200 bg-amber-50/85 backdrop-blur-sm p-6">

                <div className="flex items-start gap-3">

                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />

                  <div>

                    <h2 className="font-serif font-semibold text-amber-900">
                      Insufficient information
                    </h2>

                    <p className="mt-1 text-sm text-amber-800">
                      We could not find a sufficiently relevant BNS section.
                      Try describing the incident in more detail.
                    </p>

                  </div>

                </div>

              </section>
            )}

          {/* Initial state */}
          {!loading &&
            !error &&
            !status &&
            results.length === 0 && (
              <section className="mt-8 rounded-[20px] border border-dashed border-[#cfc8bb] bg-white/70 backdrop-blur-md p-10 text-center shadow-[0_15px_40px_rgba(18,51,91,0.08)]">

                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[#d2a14b]/40 bg-[#f8f6f1]/90">

                  <Search className="h-7 w-7 text-[#b98528]" />

                </div>

                <h2 className="mt-5 font-serif text-2xl font-semibold text-[#12335B]">
                  Search the BNS
                </h2>

                <p className="mx-auto mt-2 max-w-md text-sm text-[#7890a8] leading-relaxed">
                  Enter a legal offence or description above to find potentially
                  relevant BNS sections.
                </p>

              </section>
            )}



        </div>
      </main>
    </>
  )
}