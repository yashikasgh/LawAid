'use client'

import { useState } from 'react'
import { Search, Scale, AlertCircle, Loader2 } from 'lucide-react'
import { bnsAPI } from '@/lib/api'

type BNSResult = {
  section: string
  title: string
  similarity: number
}

type BNSResponse = {
  status: string
  results: BNSResult[]
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
      setResults(data.results || [])
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
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0D2B55]">
            <Scale className="h-6 w-6 text-white" />
          </div>

          <div>
            <h1 className="text-xl font-bold text-[#0D2B55] sm:text-2xl">
              BNS Section Search
            </h1>
            <p className="text-sm text-slate-500">
              Search for relevant Bharatiya Nyaya Sanhita sections
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Search card */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">
              Find a relevant section
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Enter an offence, incident, or legal description.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />

              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. cheating, criminal intimidation..."
                className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-[#1A4A8A] focus:ring-2 focus:ring-[#1A4A8A]/20"
              />
            </div>

            <button
              type="button"
              onClick={handleSearch}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0D2B55] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#1A4A8A] disabled:cursor-not-allowed disabled:opacity-60"
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
            <div className="mt-4 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}
        </section>

        {/* Results */}
        {results.length > 0 && (
          <section className="mt-8">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-slate-900">
                Search Results
              </h2>

              <p className="text-sm text-slate-500">
                {results.length} relevant section
                {results.length !== 1 ? 's' : ''} found
              </p>
            </div>

            <div className="grid gap-4">
              {results.map((result) => (
                <article
                  key={result.section}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex gap-4">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#E8F0FB]">
                        <Scale className="h-6 w-6 text-[#1A4A8A]" />
                      </div>

                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                          BNS Section
                        </p>

                        <h3 className="mt-1 text-xl font-bold text-[#0D2B55]">
                          Section {result.section}
                        </h3>

                        <p className="mt-1 text-base font-medium text-slate-800">
                          {result.title}
                        </p>
                      </div>
                    </div>

                    <div className="rounded-xl bg-[#E8F8F0] px-4 py-2 text-left sm:text-right">
                      <p className="text-xs font-medium text-slate-500">
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
            <section className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />

                <div>
                  <h2 className="font-semibold text-amber-900">
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
            <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#E8F0FB]">
                <Search className="h-7 w-7 text-[#1A4A8A]" />
              </div>

              <h2 className="mt-4 text-lg font-semibold text-slate-900">
                Search the BNS
              </h2>

              <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
                Enter a legal offence or description above to find potentially
                relevant BNS sections.
              </p>
            </section>
          )}

        {/* Development notice */}
        <div className="mt-8 rounded-xl border border-yellow-300 bg-yellow-50 px-4 py-3 text-xs text-yellow-800">
          <strong>Development note:</strong> The frontend is connected to the
          BNS search API, but the current backend endpoint returns mock BNS
          results. The actual retrieval system can replace this data without
          changing this page.
        </div>
      </div>
    </main>
  )
}