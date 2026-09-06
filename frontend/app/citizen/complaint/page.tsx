// app/citizen/complaint/page.tsx
'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import StepProgress from '@/components/StepProgress'
import Button from '@/components/Button'
import { bnsAPI } from '@/lib/api'

// Matches the shape returned by GET /fir/bns/search (see shared/schemas/api_contracts.md)
type BNSResult = {
  rank: number
  section: string
  clause: string
  title: string
  text: string
  chapter: string
  bailable: string
  cognizable: string
  similarity: number
}

export default function ComplaintPage() {
  const [complaint, setComplaint] = useState('')
  const [results, setResults] = useState<BNSResult[]>([])
  const [source, setSource] = useState<'rag' | 'mock' | ''>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  async function handleAnalyze() {
    if (!complaint.trim()) return
    setLoading(true)
    setError('')
    setSearched(true)
    setResults([])
    setSource('')
    try {
      const res = await bnsAPI.search(complaint)
      if (res.data.status === 'insufficient_information') {
        setResults([])
        setError('Not enough information to confidently match a BNS section. Try adding more detail.')
      } else {
        setResults(res.data.results || [])
        setSource(res.data.source || '')
      }
    } catch {
      setError('Could not reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const currentStep = results.length > 0 ? 1 : 0

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8 max-w-5xl">
          <h1 className="text-2xl font-bold text-navy mb-6">File a Complaint</h1>

          <StepProgress steps={['Describe Incident', 'Review BNS Sections']} current={currentStep} />

          <div className="flex gap-6">
            {/* Left — input */}
            <div className="flex-1 bg-white rounded-2xl p-6 shadow-sm">
              <label className="text-sm font-semibold text-gray-600 mb-2 block">
                Describe what happened
              </label>
              <textarea
                value={complaint}
                onChange={e => setComplaint(e.target.value)}
                rows={8}
                placeholder="Tell us what happened, in your own words. Include when, where, and who was involved if you can."
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-lawblue transition resize-none"
              />
              <div className="mt-4">
                <Button label={loading ? 'Analyzing...' : 'Analyze & Get BNS Sections'} onClick={handleAnalyze} loading={loading} disabled={!complaint.trim()} />
              </div>
            </div>

            {/* Right — results */}
            {searched && (
              <div className="flex-1 bg-white rounded-2xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-navy">Suggested BNS Sections</h2>
                  {source === 'mock' && (
                    <span className="text-xs bg-yellow-100 text-yellow-700 border border-yellow-300 px-2 py-0.5 rounded-full font-semibold">
                      DEV — mock data
                    </span>
                  )}
                  {source === 'rag' && (
                    <span className="text-xs bg-green-100 text-green-700 border border-green-300 px-2 py-0.5 rounded-full font-semibold">
                      ✓ AI results
                    </span>
                  )}
                </div>

                {loading && <div className="animate-pulse bg-gray-200 rounded-xl h-40" />}
                {error && <p className="text-red-500 text-sm">{error}</p>}

                {!loading && results.length > 0 && (
                  <div className="space-y-4">
                    {results.map(r => (
                      <div key={`${r.section}-${r.clause}`} className="border border-gray-200 rounded-xl overflow-hidden">
                        {/* Header row */}
                        <div className="flex items-center bg-lawblue text-white px-4 py-2 gap-3">
                          <span className="font-bold text-lg">§{r.section}{r.clause ? `(${r.clause})` : ''}</span>
                          <span className="flex-1 font-semibold">{r.title}</span>
                          <span className="text-xs opacity-80">
                            {Math.round(r.similarity * 100)}% match
                          </span>
                        </div>

                        {/* Body */}
                        <div className="p-4 space-y-3">
                          {/* Chapter */}
                          {r.chapter && (
                            <p className="text-xs text-gray-400 uppercase tracking-wide">{r.chapter}</p>
                          )}

                          {/* Text excerpt */}
                          {r.text && (
                            <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">
                              {r.text.split('\n\n').slice(-1)[0].substring(0, 220)}
                              {r.text.length > 220 ? '…' : ''}
                            </p>
                          )}

                          {/* Badges */}
                          <div className="flex gap-2 flex-wrap">
                            {r.bailable && (
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                                r.bailable.toLowerCase().includes('non')
                                  ? 'bg-red-50 text-red-700 border-red-200'
                                  : 'bg-green-50 text-green-700 border-green-200'
                              }`}>
                                {r.bailable}
                              </span>
                            )}
                            {r.cognizable && (
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                                r.cognizable.toLowerCase().includes('non')
                                  ? 'bg-gray-50 text-gray-600 border-gray-200'
                                  : 'bg-blue-50 text-blue-700 border-blue-200'
                              }`}>
                                {r.cognizable}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Next steps hint */}
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-800">
                      <p className="font-semibold mb-1">What to do next</p>
                      <ul className="list-disc list-inside space-y-1 text-xs">
                        <li>Visit your nearest police station with this information</li>
                        <li>Call the emergency helpline: <strong>112</strong></li>
                        <li>Contact legal aid: <strong>15100</strong> (National Legal Services Authority)</li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}