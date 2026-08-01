// app/citizen/complaint/page.tsx
'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import StepProgress from '@/components/StepProgress'
import Button from '@/components/Button'
import { bnsAPI } from '@/lib/api'

type BNSResult = { section: string; title: string; similarity: number }

export default function ComplaintPage() {
  const [complaint, setComplaint] = useState('')
  const [results, setResults] = useState<BNSResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  async function handleAnalyze() {
    if (!complaint.trim()) return
    setLoading(true)
    setError('')
    setSearched(true)
    try {
      const res = await bnsAPI.search(complaint)
      if (res.data.status === 'insufficient_information') {
        setResults([])
        setError('Not enough information to confidently match a BNS section. Try adding more detail.')
      } else {
        setResults(res.data.results || [])
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
                <h2 className="font-bold text-navy mb-4">Suggested BNS Sections</h2>
                {loading && <div className="animate-pulse bg-gray-200 rounded-xl h-40" />}
                {error && <p className="text-red-500 text-sm">{error}</p>}
                {!loading && results.length > 0 && (
                  <div className="space-y-3">
                    {results.map(r => (
                      <div key={r.section} className="flex border border-gray-200 rounded-xl overflow-hidden">
                        <div className="bg-lawblue text-white px-4 py-3 flex items-center font-bold">
                          §{r.section}
                        </div>
                        <div className="p-3 flex-1">
                          <p className="font-semibold text-navy">{r.title}</p>
                          <p className="text-xs text-gray-400">
                            Match confidence: {Math.round(r.similarity * 100)}%
                          </p>
                        </div>
                      </div>
                    ))}
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