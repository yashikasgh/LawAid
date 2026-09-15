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
  const supportedItems = results.filter(r => r.applicability === 'supported')
  const uncertainItems = results.filter(r => r.applicability === 'uncertain' || (!r.applicability && r.similarity))
  const notSupportedItems = results.filter(r => r.applicability === 'not_supported')
  const visibleCount = supportedItems.length + uncertainItems.length
  const currentStep = visibleCount > 0 ? 1 : 0

  function formatMetaVal(val?: string): string | null {
    if (!val) return null
    const clean = val.trim()
    if (
      clean === 'not_available_in_retrieved_context' ||
      clean.toLowerCase().startsWith('not available')
    ) {
      return 'Not available in retrieved source'
    }
    return clean
  }

  function isMetaAvailable(val?: string): boolean {
    if (!val) return false
    const clean = val.trim()
    if (
      clean === 'not_available_in_retrieved_context' ||
      clean.toLowerCase().startsWith('not available')
    ) {
      return false
    }
    return true
  }

  function renderCard(r: AnalysisItem, idx: number, cardType: 'supported' | 'uncertain' | 'not_supported') {
    const isSupp = cardType === 'supported'
    const isUncert = cardType === 'uncertain'

    const punText = formatMetaVal(r.punishment)
    const courtText = formatMetaVal(r.court)

    return (
      <div
        key={`${r.section}-${idx}`}
        className={`border rounded-xl overflow-hidden shadow-sm transition ${
          isSupp
            ? 'border-emerald-200 bg-white'
            : isUncert
            ? 'border-amber-200 bg-amber-50/20'
            : 'border-gray-200 bg-gray-50/50 opacity-90'
        }`}
      >
        {/* Header row */}
        <div className={`flex items-center px-4 py-2.5 gap-3 text-white ${
          isSupp ? 'bg-navy' : isUncert ? 'bg-amber-700' : 'bg-slate-600'
        }`}>
          <span className="font-bold text-base">
            §{r.section}{r.clause ? `(${r.clause})` : ''}
          </span>
          <span className="flex-1 font-semibold text-sm truncate">{r.title || r.offence_type}</span>
          <span className={`text-xs px-2.5 py-0.5 rounded-full font-extrabold uppercase tracking-wide ${
            isSupp
              ? 'bg-emerald-500 text-white'
              : isUncert
              ? 'bg-amber-400 text-slate-900'
              : 'bg-slate-400 text-white'
          }`}>
            {r.applicability ? r.applicability.replace('_', ' ') : 'UNCERTAIN'}
          </span>
        </div>

        {/* Body */}
        <div className="p-4 space-y-2.5 text-xs text-gray-700">
          {/* Reasoning */}
          {r.reasoning && (
            <div>
              <span className="font-semibold text-gray-900 block mb-0.5">
                {isSupp
                  ? 'Legal Assessment:'
                  : isUncert
                  ? 'Grounded Analysis (Uncertain / Insufficient Facts):'
                  : 'Grounded Analysis (Not Supported):'}
              </span>
              <p className={`leading-relaxed p-2.5 rounded-lg border text-xs ${
                isSupp
                  ? 'bg-emerald-50/50 border-emerald-100 text-gray-800'
                  : isUncert
                  ? 'bg-amber-50/70 border-amber-100 text-gray-800'
                  : 'bg-gray-100/70 border-gray-200 text-gray-600'
              }`}>
                {r.reasoning}
              </p>
            </div>
          )}

          {/* Punishment & Court */}
          <div className="space-y-1 text-xs">
            <p>
              <strong className="text-gray-900">Punishment:</strong>{' '}
              <span className={isMetaAvailable(r.punishment) ? 'text-gray-800' : 'text-gray-400 italic'}>
                {punText || 'Not available in retrieved source'}
              </span>
            </p>

            <p>
              <strong className="text-gray-900">Jurisdiction / Court:</strong>{' '}
              <span className={isMetaAvailable(r.court) ? 'text-gray-800' : 'text-gray-400 italic'}>
                {courtText || 'Not available in retrieved source'}
              </span>
            </p>
          </div>

          {/* Classification badges */}
          <div className="flex gap-2 flex-wrap pt-1">
            {isMetaAvailable(r.bailable) ? (
              <span className={`font-semibold px-2 py-0.5 rounded-full border ${
                r.bailable!.toLowerCase().includes('non')
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
              }`}>
                {r.bailable}
              </span>
            ) : null}

            {isMetaAvailable(r.cognizable) ? (
              <span className={`font-semibold px-2 py-0.5 rounded-full border ${
                r.cognizable!.toLowerCase().includes('non')
                  ? 'bg-gray-50 text-gray-600 border-gray-200'
                  : 'bg-blue-50 text-blue-700 border-blue-200'
              }`}>
                {r.cognizable}
              </span>
            ) : null}

            {!isMetaAvailable(r.bailable) && !isMetaAvailable(r.cognizable) && (
              <span className="text-[11px] text-gray-400 italic">
                Schedule I classification: Not available in retrieved source
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

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
                    <span className="text-xs bg-emerald-50 text-emerald-800 border border-emerald-300 px-3 py-1 rounded-full font-semibold flex items-center gap-1.5" title="Analysis evaluated against retrieved BNS 2023 provisions">
                      <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                      Grounded in BNS 2023 Source Material
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

                {!loading && !error && (
                  <div className="space-y-5 max-h-[75vh] overflow-y-auto pr-1">
                    {/* 1. Service Unavailable Banner */}
                    {pipelineData?.status === 'analysis_unavailable' && (
                      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2">
                        <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                          <svg className="w-5 h-5 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <span>AI legal analysis is temporarily unavailable</span>
                        </div>
                        <p className="text-amber-800 leading-relaxed">
                          {pipelineData.limitations?.[0] ||
                            'The LawAid legal knowledge base was reached successfully, but the AI reasoning service is temporarily unavailable. Please try again shortly.'}
                        </p>
                      </div>
                    )}

                    {/* 2. Genuine No Results State (No Supported or Uncertain Provisions) */}
                    {pipelineData?.status !== 'analysis_unavailable' && visibleCount === 0 && (
                      <p className="text-gray-500 text-sm">
                        No matching provisions found. Try adding more concrete facts about what occurred.
                      </p>
                    )}

                    {/* 3. Evaluated Provisions (Supported & Uncertain) */}
                    {visibleCount > 0 && (
                      <>
                        {/* Legally Supported Provisions */}
                        {supportedItems.length > 0 && (
                          <div className="space-y-3">
                            <h3 className="text-xs font-extrabold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5 border-b border-emerald-100 pb-1.5">
                              <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                              Legally Supported Provisions ({supportedItems.length})
                            </h3>
                            {supportedItems.map((r, idx) => renderCard(r, idx, 'supported'))}
                          </div>
                        )}

                        {/* Provisions Requiring Further Facts / Unstated Provisos */}
                        {uncertainItems.length > 0 && (
                          <div className="space-y-3">
                            <h3 className="text-xs font-extrabold uppercase tracking-wider text-amber-800 flex items-center gap-1.5 border-b border-amber-100 pb-1.5">
                              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                              Provisions Requiring Further Facts / Provisos ({uncertainItems.length})
                            </h3>
                            {uncertainItems.map((r, idx) => renderCard(r, idx, 'uncertain'))}
                          </div>
                        )}
                      </>
                    )}

                    {/* Disclaimer note */}
                    {pipelineData?.disclaimer && (
                      <p className="text-[11px] text-gray-500 italic mt-3 border-t pt-2.5">
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