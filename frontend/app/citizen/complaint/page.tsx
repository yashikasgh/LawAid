// app/citizen/complaint/page.tsx
'use client'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import StepProgress from '@/components/StepProgress'
import Button from '@/components/Button'
import { bnsAPI } from '@/lib/api'

type AnalysisItem = {
  offence_type?: string
  section: string
  clause?: string
  title: string
  applicability?: 'supported' | 'uncertain' | 'not_supported'
  reasoning?: string
  punishment?: string
  bailable?: string
  cognizable?: string
  court?: string
  similarity?: number
}

type PipelineData = {
  status: string
  sanitized_incident?: string
  analysis: AnalysisItem[]
  limitations?: string[]
  disclaimer?: string
}

export default function ComplaintPage() {
  const [complaint, setComplaint] = useState('')
  const [pipelineData, setPipelineData] = useState<PipelineData | null>(null)
  const [source, setSource] = useState<'pipeline' | 'retrieval_fallback' | 'mock' | ''>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  async function handleAnalyze() {
    if (!complaint.trim()) return
    setLoading(true)
    setError('')
    setSearched(true)
    setPipelineData(null)
    setSource('')
    try {
      const res = await bnsAPI.analyze(complaint)
      if (res.data && res.data.data) {
        setPipelineData(res.data.data)
        setSource(res.data.source || 'pipeline')
      } else {
        setError('No analysis results returned. Please provide more details.')
      }
    } catch {
      setError('Could not reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const results = pipelineData?.analysis || []
  const currentStep = results.length > 0 ? 1 : 0

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8 max-w-5xl">
          <h1 className="text-2xl font-bold text-navy mb-6">File a Complaint & Legal Assessment</h1>

          <StepProgress steps={['Describe Incident', 'AI Legal Analysis']} current={currentStep} />

          <div className="flex gap-6">
            {/* Left — input */}
            <div className="flex-1 bg-white rounded-2xl p-6 shadow-sm">
              <label className="text-sm font-semibold text-gray-600 mb-2 block">
                Describe what happened
              </label>
              <textarea
                value={complaint}
                onChange={e => setComplaint(e.target.value)}
                rows={9}
                placeholder="Describe the incident in detail. Mention what happened, where, and any actions taken. Personal information will be automatically sanitized by our local privacy gate."
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-lawblue transition resize-none"
              />
              <div className="mt-4">
                <Button
                  label={loading ? 'Running AI Legal Analysis...' : 'Analyze & Identify BNS Sections'}
                  onClick={handleAnalyze}
                  loading={loading}
                  disabled={!complaint.trim() || complaint.trim().length < 5}
                />
              </div>
            </div>

            {/* Right — results */}
            {searched && (
              <div className="flex-1 bg-white rounded-2xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-navy">Legal Findings</h2>
                  {source === 'pipeline' && (
                    <span className="text-xs bg-green-100 text-green-700 border border-green-300 px-2.5 py-0.5 rounded-full font-semibold">
                      ✓ AI Grounded Analysis
                    </span>
                  )}
                  {source === 'retrieval_fallback' && (
                    <span className="text-xs bg-blue-100 text-blue-700 border border-blue-300 px-2.5 py-0.5 rounded-full font-semibold">
                      Vector Match (RAG)
                    </span>
                  )}
                  {source === 'mock' && (
                    <span className="text-xs bg-yellow-100 text-yellow-700 border border-yellow-300 px-2.5 py-0.5 rounded-full font-semibold">
                      DEV — Mock Data
                    </span>
                  )}
                </div>

                {loading && (
                  <div className="space-y-3">
                    <div className="animate-pulse bg-gray-200 rounded-xl h-28" />
                    <div className="animate-pulse bg-gray-200 rounded-xl h-28" />
                  </div>
                )}
                {error && <p className="text-red-500 text-sm">{error}</p>}

                {!loading && results.length === 0 && !error && (
                  <p className="text-gray-500 text-sm">
                    No matching provisions found. Try adding more concrete facts about what occurred.
                  </p>
                )}

                {!loading && results.length > 0 && (
                  <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
                    {results.map((r, idx) => (
                      <div key={`${r.section}-${idx}`} className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
                        {/* Header row */}
                        <div className="flex items-center bg-lawblue text-white px-4 py-2.5 gap-3">
                          <span className="font-bold text-base">
                            §{r.section}{r.clause ? `(${r.clause})` : ''}
                          </span>
                          <span className="flex-1 font-semibold text-sm truncate">{r.title || r.offence_type}</span>
                          {r.applicability && (
                            <span className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
                              r.applicability === 'supported'
                                ? 'bg-green-600 text-white'
                                : r.applicability === 'uncertain'
                                ? 'bg-amber-500 text-white'
                                : 'bg-red-500 text-white'
                            }`}>
                              {r.applicability}
                            </span>
                          )}
                        </div>

                        {/* Body */}
                        <div className="p-4 space-y-2.5 text-xs text-gray-700">
                          {/* Reasoning */}
                          {r.reasoning && (
                            <div>
                              <span className="font-semibold text-gray-900 block mb-0.5">Legal Assessment:</span>
                              <p className="leading-relaxed bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                                {r.reasoning}
                              </p>
                            </div>
                          )}

                          {/* Punishment & Court */}
                          {r.punishment && r.punishment !== 'not_available_in_retrieved_context' && (
                            <p>
                              <strong className="text-gray-900">Punishment:</strong> {r.punishment}
                            </p>
                          )}

                          {r.court && r.court !== 'not_available_in_retrieved_context' && (
                            <p>
                              <strong className="text-gray-900">Jurisdiction / Court:</strong> {r.court}
                            </p>
                          )}

                          {/* Classification badges */}
                          <div className="flex gap-2 flex-wrap pt-1">
                            {r.bailable && (
                              <span className={`font-semibold px-2 py-0.5 rounded-full border ${
                                r.bailable.toLowerCase().includes('non')
                                  ? 'bg-red-50 text-red-700 border-red-200'
                                  : 'bg-green-50 text-green-700 border-green-200'
                              }`}>
                                {r.bailable}
                              </span>
                            )}
                            {r.cognizable && (
                              <span className={`font-semibold px-2 py-0.5 rounded-full border ${
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

                    {/* Disclaimer note */}
                    {pipelineData?.disclaimer && (
                      <p className="text-[11px] text-gray-500 italic mt-2 border-t pt-2">
                        {pipelineData.disclaimer}
                      </p>
                    )}

                    {/* Next steps advice */}
                    <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-900">
                      <p className="font-bold mb-1">Recommended Citizen Actions:</p>
                      <ul className="list-disc list-inside space-y-0.5">
                        <li>Lodge an official report at the local Police Station</li>
                        <li>Emergency Helpline: <strong>112</strong></li>
                        <li>Free Legal Aid (NALSA): <strong>15100</strong></li>
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