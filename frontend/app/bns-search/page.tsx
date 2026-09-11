'use client'

import { useState } from 'react'
import { Search, Scale, AlertCircle, Loader2, BookOpen, ChevronDown, ChevronUp, Sparkles, CheckCircle2 } from 'lucide-react'
import { bnsAPI } from '@/lib/api'

type BNSResult = {
  rank?: number
  section: string
  clause?: string
  title: string
  text?: string
  chapter?: string
  bailable?: string
  cognizable?: string
  similarity: number
}

type BNSResponse = {
  status: string
  results: BNSResult[]
}

const SAMPLE_QUERIES = [
  'Theft of mobile phone',
  'Cyber fraud and online cheating',
  'Criminal intimidation',
  'Voluntarily causing hurt',
  'House trespass without permission'
]

export default function BNSSearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<BNSResult[]>([])
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  const handleSearch = async (queryText?: string) => {
    const searchTarget = (queryText !== undefined ? queryText : query).trim()

    if (searchTarget.length < 3) {
      setError('Please enter at least 3 characters to search.')
      setResults([])
      setStatus('')
      return
    }

    if (queryText !== undefined) {
      setQuery(queryText)
    }

    setLoading(true)
    setError('')
    setResults([])
    setStatus('')
    setExpandedSections({})

    try {
      const response = await bnsAPI.search(searchTarget)
      const data: BNSResponse = response.data

      setStatus(data.status)
      setResults(data.results || [])
    } catch (err: any) {
      console.error('BNS search failed:', err)
      setError(
        err?.response?.data?.detail ||
          'BNS Search is temporarily unavailable. Please check that the LawAid backend is running.'
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

  const toggleExpand = (secKey: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [secKey]: !prev[secKey]
    }))
  }

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col justify-between">
      <div>
        {/* Header */}
        <header className="border-b border-slate-200 bg-white shadow-xs">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0D2B55] shadow-sm">
                <Scale className="h-6 w-6 text-white" />
              </div>

              <div>
                <h1 className="text-xl font-bold text-[#0D2B55] sm:text-2xl">
                  BNS Section Search
                </h1>
                <p className="text-xs sm:text-sm text-slate-500">
                  Search & explore statutory provisions from Bharatiya Nyaya Sanhita (BNS) 2023
                </p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>358 Sections • 536 Vector Docs</span>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
          {/* Search Card */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="mb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Find Statutory Provisions
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-slate-500">
                  Enter an offence, physical action, or legal concept to retrieve grounded BNS sections.
                </p>
              </div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider self-start sm:self-auto">
                Semantic Vector Search
              </span>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. theft of mobile phone, online cheating, criminal force..."
                  className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm text-slate-900 outline-none transition focus:border-[#1A4A8A] focus:ring-2 focus:ring-[#1A4A8A]/20"
                />
              </div>

              <button
                type="button"
                onClick={() => handleSearch()}
                disabled={loading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0D2B55] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#1A4A8A] disabled:cursor-not-allowed disabled:opacity-60 shadow-sm"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    <span>Search BNS</span>
                  </>
                )}
              </button>
            </div>

            {/* Quick Suggestions */}
            <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400">Try searching:</span>
              {SAMPLE_QUERIES.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSearch(sample)}
                  className="text-xs bg-slate-100 hover:bg-[#E8F0FB] hover:text-[#1A4A8A] border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg transition"
                >
                  {sample}
                </button>
              ))}
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-4 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="font-semibold">BNS Search Unavailable</p>
                  <p className="mt-0.5 text-xs text-red-600">{error}</p>
                </div>
              </div>
            )}
          </section>

          {/* Loading State Skeleton */}
          {loading && (
            <section className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
                <Loader2 className="h-4 w-4 animate-spin text-[#1A4A8A]" />
                <span>Searching LawAid's 536 indexed BNS vector documents...</span>
              </div>
              {[1, 2].map((n) => (
                <div key={n} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm animate-pulse space-y-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-2 w-2/3">
                      <div className="h-4 bg-slate-200 rounded w-1/4" />
                      <div className="h-6 bg-slate-200 rounded w-1/2" />
                    </div>
                    <div className="h-8 bg-slate-200 rounded w-20" />
                  </div>
                  <div className="h-16 bg-slate-100 rounded w-full" />
                </div>
              ))}
            </section>
          )}

          {/* Results Section */}
          {!loading && results.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Retrieved Statutory Provisions
                  </h2>
                  <p className="text-xs text-slate-500">
                    {results.length} relevant BNS section{results.length !== 1 ? 's' : ''} retrieved from knowledge base
                  </p>
                </div>
                <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Semantic Vector Match</span>
                </span>
              </div>

              <div className="grid gap-4">
                {results.map((result, index) => {
                  const isTopMatch = index === 0
                  const secKey = `${result.section}-${result.clause || index}`
                  const isExpanded = expandedSections[secKey] || false
                  const rawText = result.text || ''

                  return (
                    <article
                      key={secKey}
                      className={`rounded-2xl border transition-all bg-white p-6 shadow-sm ${
                        isTopMatch
                          ? 'border-[#1A4A8A]/40 ring-1 ring-[#1A4A8A]/20 bg-gradient-to-b from-blue-50/20 to-white'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                        <div className="flex gap-4">
                          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl font-bold ${
                            isTopMatch ? 'bg-[#0D2B55] text-white' : 'bg-[#E8F0FB] text-[#1A4A8A]'
                          }`}>
                            <Scale className="h-6 w-6" />
                          </div>

                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-bold uppercase tracking-wider text-[#1A4A8A]">
                                BNS Section {result.section}
                              </span>
                              {result.clause && (
                                <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                  Clause {result.clause}
                                </span>
                              )}
                              {isTopMatch && (
                                <span className="text-[11px] font-extrabold text-amber-800 bg-amber-100 border border-amber-300 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                                  <Sparkles className="w-3 h-3 text-amber-600" />
                                  <span>Top Vector Match</span>
                                </span>
                              )}
                            </div>

                            <h3 className="mt-1 text-xl font-extrabold text-[#0D2B55]">
                              {result.title}
                            </h3>
                          </div>
                        </div>

                        {/* Similarity badge */}
                        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-2 text-left sm:text-right shrink-0">
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-800">
                            Similarity
                          </p>
                          <p className="text-lg font-black text-emerald-700">
                            {(result.similarity * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>

                      {/* Statutory Legal Text Preview / Full view */}
                      {rawText && (
                        <div className="mt-4 pt-4 border-t border-slate-100">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5 text-[#1A4A8A]" />
                              <span>Statutory Text & Details</span>
                            </span>
                            <button
                              type="button"
                              onClick={() => toggleExpand(secKey)}
                              className="text-xs font-bold text-[#1A4A8A] hover:underline flex items-center gap-1"
                            >
                              {isExpanded ? (
                                <>
                                  <span>Show Less</span>
                                  <ChevronUp className="w-3.5 h-3.5" />
                                </>
                              ) : (
                                <>
                                  <span>View Full Statutory Text</span>
                                  <ChevronDown className="w-3.5 h-3.5" />
                                </>
                              )}
                            </button>
                          </div>

                          <div className={`text-xs text-slate-700 leading-relaxed font-mono bg-slate-50/80 p-3.5 rounded-xl border border-slate-200 whitespace-pre-line ${
                            !isExpanded ? 'line-clamp-4' : ''
                          }`}>
                            {rawText}
                          </div>
                        </div>
                      )}
                    </article>
                  )
                })}
              </div>
            </section>
          )}

          {/* Insufficient Information / No Results State */}
          {!loading && !error && status === 'insufficient_information' && (
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6 sm:p-8">
              <div className="flex items-start gap-4">
                <AlertCircle className="h-6 w-6 shrink-0 text-amber-600 mt-0.5" />
                <div>
                  <h2 className="text-base font-bold text-amber-900">
                    No sufficiently matching sections found
                  </h2>
                  <p className="mt-1 text-xs sm:text-sm text-amber-800 leading-relaxed">
                    We could not find a BNS section matching your search query above a 30% similarity threshold.
                  </p>
                  <div className="mt-3 pt-3 border-t border-amber-200/60 text-xs text-amber-900">
                    <p className="font-semibold mb-1">Search tips:</p>
                    <ul className="list-disc pl-4 space-y-1 text-amber-800">
                      <li>Use standard legal terms or everyday descriptions (e.g. "theft", "punch", "cheating").</li>
                      <li>Describe the physical actions involved in the incident.</li>
                      <li>Avoid overly vague single letters or abbreviations.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Initial State Before Search */}
          {!loading && !error && !status && results.length === 0 && (
            <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 sm:p-12 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#E8F0FB]">
                <Search className="h-7 w-7 text-[#1A4A8A]" />
              </div>

              <h2 className="mt-4 text-lg font-bold text-[#0D2B55]">
                Search Bharatiya Nyaya Sanhita (BNS 2023)
              </h2>

              <p className="mx-auto mt-2 max-w-md text-xs sm:text-sm text-slate-500 leading-relaxed">
                Enter an offence name, incident description, or legal phrase above to perform semantic vector search across 358 BNS sections.
              </p>
            </section>
          )}
        </div>
      </div>

      {/* Grounding Footer Bar */}
      <footer className="mt-12 border-t border-slate-200 bg-white py-4">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-2xs">
            <div className="flex items-center gap-2 text-center sm:text-left">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="font-bold text-slate-800">LawAid Vector Search</span>
              <span className="text-slate-400 hidden sm:inline">•</span>
              <span className="text-slate-600">
                Grounded in 358 BNS sections and 536 indexed legal documents.
              </span>
            </div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider shrink-0">
              Ollama Embedding Vector Core
            </span>
          </div>
        </div>
      </footer>
    </main>
  )
}