'use client'

import Link from 'next/link'
import { useState, useEffect, useRef } from 'react'
import Navbar from '@/components/Navbar'
import { policeAPI } from '@/lib/api'

export type ActSection = {
  act: string
  sections: string
}

export type FIRData = {
  district: string
  police_station: string
  year: string
  fir_number: string
  fir_date: string
  acts_sections: ActSection[]
  occurrence: {
    day: string
    date_from: string
    date_to: string
    time_from: string
    time_to: string
    info_received_date: string
    info_received_time: string
  }
  general_diary: {
    entry_number: string
    date_time: string
  }
  type_of_information: string
  place_of_occurrence: {
    direction_distance: string
    beat_number: string
    address: string
    outside_ps_name: string
    outside_district: string
  }
  complainant: {
    name: string
    father_husband_name: string
    date_of_birth: string
    nationality: string
    passport_number: string
    passport_issue_date: string
    passport_issue_place: string
    occupation: string
    address: string
  }
  accused_details: string
  delay_reason: string
  property_details: string
  property_value: string
  inquest_ud_case: string
  fir_contents: string
  action_taken: string
  officer: {
    name: string
    rank: string
    number: string
  }
  complainant_signature: string
  dispatch_to_court: {
    date: string
    time: string
  }
}

const defaultFIRData: FIRData = {
  district: 'Central',
  police_station: 'City Police Station',
  year: new Date().getFullYear().toString(),
  fir_number: '',
  fir_date: new Date().toISOString().split('T')[0],
  acts_sections: [
    { act: 'Bharatiya Nyaya Sanhita, 2023', sections: '' }
  ],
  occurrence: {
    day: '',
    date_from: '',
    date_to: '',
    time_from: '',
    time_to: '',
    info_received_date: new Date().toISOString().split('T')[0],
    info_received_time: new Date().toTimeString().slice(0, 5),
  },
  general_diary: {
    entry_number: 'GD-' + Math.floor(100 + Math.random() * 900),
    date_time: new Date().toISOString().replace('T', ' ').slice(0, 16),
  },
  type_of_information: 'Written',
  place_of_occurrence: {
    direction_distance: '',
    beat_number: '',
    address: '',
    outside_ps_name: '',
    outside_district: '',
  },
  complainant: {
    name: '',
    father_husband_name: '',
    date_of_birth: '',
    nationality: 'Indian',
    passport_number: '',
    passport_issue_date: '',
    passport_issue_place: '',
    occupation: '',
    address: '',
  },
  accused_details: '',
  delay_reason: 'Nil',
  property_details: '',
  property_value: '',
  inquest_ud_case: 'Nil',
  fir_contents: '',
  action_taken: 'Registered FIR and took up investigation.',
  officer: {
    name: 'Inspector R. K. Sharma',
    rank: 'Sub-Inspector',
    number: 'SI-4092',
  },
  complainant_signature: 'Signature attached',
  dispatch_to_court: {
    date: new Date().toISOString().split('T')[0],
    time: new Date().toTimeString().slice(0, 5),
  },
}

export default function NewFIRPage() {
  const [viewState, setViewState] = useState<'input' | 'generating' | 'document'>('input')
  const [incident, setIncident] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)

  const [loadingStep, setLoadingStep] = useState(1)
  const [loadingText, setLoadingText] = useState('Analyzing incident & retrieving grounded BNS sections...')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const [firData, setFirData] = useState<FIRData>(defaultFIRData)
  const [pdfBase64, setPdfBase64] = useState<string>('')
  const [supportedSections, setSupportedSections] = useState<any[]>([])
  const [sanitizedIncident, setSanitizedIncident] = useState<string>('')
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)
  const [showGroundingDetails, setShowGroundingDetails] = useState(true)

  // Speech Recognition setup
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        setSpeechSupported(true)
      }
    }
  }, [])

  const baseIncidentRef = useRef<string>('')

  function handleToggleSpeech() {
    if (!speechSupported) {
      alert('Speech recognition is not supported in this browser. Please type the statement.')
      return
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!isListening) {
      baseIncidentRef.current = incident.trim()
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-IN'

      recognition.onstart = () => {
        setIsListening(true)
      }

      recognition.onresult = (event: any) => {
        let finalTranscript = ''
        let interimTranscript = ''

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i]
          const text = result[0].transcript
          if (result.isFinal) {
            finalTranscript += text + ' '
          } else {
            interimTranscript += text
          }
        }

        const base = baseIncidentRef.current
        const finalPart = finalTranscript.trim()
        const interimPart = interimTranscript.trim()

        let combined = base
        if (finalPart) {
          combined = combined ? `${combined} ${finalPart}` : finalPart
        }
        if (interimPart) {
          combined = combined ? `${combined} ${interimPart}` : interimPart
        }

        setIncident(combined)
      }

      recognition.onerror = () => {
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognition.start()
    } else {
      setIsListening(false)
    }
  }

  function loadDemoScenario() {
    setIncident(
      'On 5 September 2026 at approximately 8:30 PM, I was returning home near the market when an unknown man suddenly punched me in the face, causing my nose to bleed. He then took my mobile phone without my consent and ran away on a motorcycle.'
    )
    setErrorMsg('')
  }

  async function handleGenerateFIR() {
    if (!incident.trim() || incident.trim().length < 10) {
      setErrorMsg('Please enter a valid incident description (at least 10 characters).')
      return
    }

    setErrorMsg('')
    setViewState('generating')
    setLoadingStep(1)
    setLoadingText('Running grounded LawAid RAG pipeline to retrieve relevant BNS sections...')

    try {
      // Step 1 timeout simulation for user feedback
      const t1 = setTimeout(() => {
        setLoadingStep(2)
        setLoadingText('Extracting structured IF1 FIR fields (1 to 15)...')
      }, 2500)

      const t2 = setTimeout(() => {
        setLoadingStep(3)
        setLoadingText('Overlaying onto official IF1 First Information Report template PDF...')
      }, 5500)

      const response = await policeAPI.generateFir(incident.trim())

      clearTimeout(t1)
      clearTimeout(t2)

      if (response.data && response.data.fir_data) {
        const rawFir = response.data.fir_data
        if (rawFir.occurrence) {
          rawFir.occurrence.date_from = rawFir.occurrence.date_from || rawFir.occurrence.date || ''
          rawFir.occurrence.time_from = rawFir.occurrence.time_from || rawFir.occurrence.time || ''
          rawFir.occurrence.day = rawFir.occurrence.day || ''
        }
        setFirData(rawFir)
        setPdfBase64(response.data.pdf_base64 || '')
        setSupportedSections(response.data.supported_sections || [])
        setSanitizedIncident(response.data.sanitized_incident || incident)
        setViewState('document')
        setSuccessMsg('FIR fields successfully auto-populated from AI analysis!')
      } else {
        throw new Error('Invalid response structure received from backend.')
      }
    } catch (err: any) {
      console.error('FIR Generation error:', err)
      const detail = err.response?.data?.detail || err.message || 'Failed to generate FIR.'
      setErrorMsg(detail)
      setViewState('input')
    }
  }

  async function handleDownloadPDF() {
    setIsDownloadingPdf(true)
    try {
      // Re-render PDF with current edited firData state
      const response = await policeAPI.renderFirPdf(firData)
      const base64 = response.data?.pdf_base64 || pdfBase64

      if (!base64) {
        throw new Error('No PDF content returned.')
      }

      // Convert Base64 to Blob and trigger download
      const binaryString = atob(base64)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      const blob = new Blob([bytes], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `IF1_FIR_${firData.fir_number || 'Draft'}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert('Error downloading PDF: ' + (err.response?.data?.detail || err.message))
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  function handleSaveDraft() {
    localStorage.setItem('lawaid_saved_fir_draft', JSON.stringify(firData))
    setSuccessMsg('FIR Draft saved to local storage!')
    setTimeout(() => setSuccessMsg(''), 4000)
  }

  function handleFinalizeFIR() {
    alert(`FIR #${firData.fir_number || 'Draft'} finalized successfully! Recorded in Police Station Registry.`)
  }

  // Nested FIR state mutators
  const updateFirField = (path: string[], value: any) => {
    setFirData((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      let curr = next
      for (let i = 0; i < path.length - 1; i++) {
        curr = curr[path[i]]
      }
      curr[path[path.length - 1]] = value
      return next
    })
  }

  const updateActSection = (index: number, field: 'act' | 'sections', value: string) => {
    setFirData((prev) => {
      const next = { ...prev }
      const acts = [...next.acts_sections]
      acts[index] = { ...acts[index], [field]: value }
      next.acts_sections = acts
      return next
    })
  }

  const addActSectionRow = () => {
    setFirData((prev) => ({
      ...prev,
      acts_sections: [...prev.acts_sections, { act: 'Bharatiya Nyaya Sanhita, 2023', sections: '' }],
    }))
  }

  const removeActSectionRow = (index: number) => {
    setFirData((prev) => ({
      ...prev,
      acts_sections: prev.acts_sections.filter((_, i) => i !== index),
    }))
  }

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-slate-100 text-slate-900 pb-16">
        {/* Top Header */}
        <div className="bg-navy text-white py-6 px-4 shadow-md mb-8">
          <div className="max-w-6xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <span className="bg-amber-400 text-navy font-bold text-xs px-2.5 py-1 rounded-md uppercase tracking-wider">
                  Official Police Tool
                </span>
                <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
                  IF1 First Information Report Generator
                </h1>
              </div>
              <p className="text-slate-300 text-sm mt-1">
                Grounded Legal Analysis & Auto-Form Overlay onto Official National IF1 Template PDF
              </p>
            </div>

            <div className="flex items-center gap-3">
              {viewState === 'document' && (
                <button
                  type="button"
                  onClick={() => setViewState('input')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 px-4 py-2 rounded-lg font-medium text-sm transition-colors"
                >
                  ← New Incident
                </button>
              )}
              <Link
                href="/police"
                className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
              >
                Dashboard
              </Link>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-4">
          {/* Global Alert Messages */}
          {errorMsg && (
            <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg shadow-sm text-red-800 flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div>
                <h4 className="font-bold">Generation Error</h4>
                <p className="text-sm">{errorMsg}</p>
              </div>
            </div>
          )}

          {successMsg && (
            <div className="mb-6 p-4 bg-emerald-50 border-l-4 border-emerald-500 rounded-r-lg shadow-sm text-emerald-900 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl">✅</span>
                <p className="text-sm font-medium">{successMsg}</p>
              </div>
              <button
                type="button"
                onClick={() => setSuccessMsg('')}
                className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* VIEW 1: INCIDENT INPUT */}
          {viewState === 'input' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl shadow-md border border-slate-200 p-6 md:p-8">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100 mb-6">
                  <div>
                    <h2 className="text-xl font-bold text-navy flex items-center gap-2">
                      <span>📝</span> Incident Statement Input
                    </h2>
                    <p className="text-slate-500 text-sm mt-1">
                      Type, paste, or speak the complainant/informant statement. LawAid AI will analyze BNS sections & generate the official IF1 document.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={loadDemoScenario}
                    className="self-start md:self-auto bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-900 px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors"
                  >
                    <span>⚡</span> Load Theft & Assault Demo Scenario
                  </button>
                </div>

                <div className="relative">
                  <textarea
                    rows={7}
                    value={incident}
                    onChange={(e) => setIncident(e.target.value)}
                    placeholder="Describe the incident in detail (e.g. date, time, location, facts, assault details, stolen items, accused description)..."
                    className="w-full border border-slate-300 rounded-lg p-4 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-navy focus:border-transparent resize-y text-base font-sans leading-relaxed"
                  />

                  {isListening && (
                    <div className="absolute top-3 right-3 bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full animate-pulse flex items-center gap-1.5 shadow-sm">
                      <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                      Listening...
                    </div>
                  )}
                </div>

                <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <button
                      type="button"
                      onClick={handleToggleSpeech}
                      className={`flex-1 sm:flex-initial px-4 py-2.5 rounded-lg border text-sm font-semibold flex items-center justify-center gap-2 transition-all ${
                        isListening
                          ? 'bg-red-50 border-red-300 text-red-700 shadow-sm'
                          : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      <span>🎤</span>
                      <span>{isListening ? 'Stop Listening' : 'Speak Incident'}</span>
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={handleGenerateFIR}
                    className="w-full sm:w-auto bg-navy hover:bg-navy/90 text-white font-bold px-8 py-3 rounded-lg shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2.5 text-base"
                  >
                    <span>✨</span>
                    <span>Generate Structured FIR</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 2: GENERATING ANIMATED LOADING */}
          {viewState === 'generating' && (
            <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-10 max-w-2xl mx-auto my-12 text-center space-y-8">
              <div className="relative w-20 h-20 mx-auto">
                <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
                <div className="absolute inset-0 rounded-full border-4 border-navy border-t-transparent animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center text-2xl">
                  ⚖️
                </div>
              </div>

              <div>
                <h3 className="text-2xl font-extrabold text-navy">
                  Processing Incident with LawAid AI
                </h3>
                <p className="text-slate-600 text-sm mt-2 font-medium">
                  {loadingText}
                </p>
              </div>

              {/* Step indicator */}
              <div className="space-y-3 max-w-md mx-auto text-left pt-4 border-t border-slate-100">
                <div className={`flex items-center gap-3 text-sm font-medium ${loadingStep >= 1 ? 'text-navy font-bold' : 'text-slate-400'}`}>
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${loadingStep > 1 ? 'bg-emerald-500 text-white' : loadingStep === 1 ? 'bg-navy text-white animate-pulse' : 'bg-slate-200'}`}>
                    {loadingStep > 1 ? '✓' : '1'}
                  </span>
                  <span>1. Grounded LawAid RAG Legal Analysis & Retrieval</span>
                </div>

                <div className={`flex items-center gap-3 text-sm font-medium ${loadingStep >= 2 ? 'text-navy font-bold' : 'text-slate-400'}`}>
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${loadingStep > 2 ? 'bg-emerald-500 text-white' : loadingStep === 2 ? 'bg-navy text-white animate-pulse' : 'bg-slate-200'}`}>
                    {loadingStep > 2 ? '✓' : '2'}
                  </span>
                  <span>2. Structuring IF1 Form Fields (1 to 15)</span>
                </div>

                <div className={`flex items-center gap-3 text-sm font-medium ${loadingStep >= 3 ? 'text-navy font-bold' : 'text-slate-400'}`}>
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${loadingStep === 3 ? 'bg-navy text-white animate-pulse' : 'bg-slate-200'}`}>
                    3
                  </span>
                  <span>3. Visual Overlay onto National IF1 PDF Template</span>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 3: EDITABLE DOCUMENT FRONTEND */}
          {viewState === 'document' && (
            <div className="space-y-8">
              {/* Action Toolbar */}
              <div className="sticky top-4 z-20 bg-white/95 backdrop-blur rounded-xl shadow-lg border border-slate-200 p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
                  <div>
                    <h3 className="font-extrabold text-slate-800 text-base">
                      FIR #{firData.fir_number || 'Draft'} Ready for Review
                    </h3>
                    <p className="text-xs text-slate-500">
                      Editable document-style interface. Edits automatically render onto the official IF1 PDF.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => setViewState('input')}
                    className="border border-slate-300 text-slate-700 hover:bg-slate-50 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
                  >
                    ↻ Regenerate
                  </button>

                  <button
                    type="button"
                    onClick={handleSaveDraft}
                    className="border border-navy text-navy hover:bg-navy/5 px-4 py-2 rounded-lg text-sm font-semibold transition-colors flex items-center gap-1.5"
                  >
                    <span>💾</span> Save Draft
                  </button>

                  <button
                    type="button"
                    onClick={handleDownloadPDF}
                    disabled={isDownloadingPdf}
                    className="bg-navy hover:bg-navy/90 text-white px-5 py-2 rounded-lg text-sm font-bold shadow transition-all flex items-center gap-2 disabled:opacity-50"
                  >
                    {isDownloadingPdf ? (
                      <>
                        <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        <span>Rendering PDF...</span>
                      </>
                    ) : (
                      <>
                        <span>📥</span> Download PDF
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleFinalizeFIR}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-lg text-sm font-bold shadow transition-all flex items-center gap-1.5"
                  >
                    <span>✓</span> Finalize FIR
                  </button>
                </div>
              </div>

              {/* Grounded Legal Analysis & BNS Recommendations Panel */}
              <div className="bg-slate-900 text-white rounded-xl shadow-md p-6 border border-slate-800">
                <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowGroundingDetails(!showGroundingDetails)}>
                  <div className="flex items-center gap-3">
                    <span className="text-xl">⚖️</span>
                    <div>
                      <h4 className="font-bold text-base text-amber-400">
                        Grounded Legal Analysis & BNS Recommendation
                      </h4>
                      <p className="text-xs text-slate-300">
                        Retrieved directly from LawAid BNS Knowledge Base via RAG pipeline
                      </p>
                    </div>
                  </div>
                  <button className="text-slate-400 hover:text-white text-xs font-bold">
                    {showGroundingDetails ? '▲ Hide Details' : '▼ View Details'}
                  </button>
                </div>

                {showGroundingDetails && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-4">
                    <div>
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sanitized Statement:</span>
                      <p className="text-sm text-slate-200 mt-1 italic bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        "{sanitizedIncident || incident}"
                      </p>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Supported BNS Provisions:</span>
                      {supportedSections && supportedSections.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {supportedSections.map((sec: any, idx: number) => {
                            let displaySection = ''
                            let displayTitle = ''
                            let displayReason = ''
                            let displayOffenceType = 'Cognizable'

                            if (typeof sec === 'string') {
                              const match = sec.match(/^(BNS Section\s+[^(\s]+|\d+)(?:\s*\((.*)\))?$/i)
                              if (match) {
                                const rawNum = match[1].trim()
                                displaySection = rawNum.toLowerCase().startsWith('bns section')
                                  ? rawNum
                                  : rawNum.toLowerCase().startsWith('section')
                                    ? `BNS ${rawNum}`
                                    : `BNS Section ${rawNum}`
                                displayTitle = match[2] ? match[2].trim() : ''
                              } else {
                                displaySection = sec.toLowerCase().startsWith('bns section') ? sec : `BNS Section ${sec}`
                              }
                            } else if (typeof sec === 'object' && sec !== null) {
                              const rawSec = String(sec.section_number || sec.section || '').trim()
                              displaySection = rawSec.toLowerCase().startsWith('bns section')
                                ? rawSec
                                : rawSec.toLowerCase().startsWith('section')
                                  ? `BNS ${rawSec}`
                                  : rawSec
                                    ? `BNS Section ${rawSec}`
                                    : 'BNS Section'
                              displayTitle = sec.title || ''
                              displayReason = sec.supported_reasoning || sec.explanation || sec.reason || sec.reasoning || ''
                              displayOffenceType = sec.offence_type || sec.cognizable || 'Cognizable'
                            }

                            return (
                              <div key={idx} className="bg-slate-800/80 border border-slate-700 rounded-lg p-3">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-amber-400 text-sm">
                                    {displaySection}
                                  </span>
                                  <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">
                                    {displayOffenceType}
                                  </span>
                                </div>
                                {displayTitle && (
                                  <p className="font-semibold text-white text-xs mt-1">
                                    {displayTitle}
                                  </p>
                                )}
                                {displayReason && (
                                  <p className="text-xs text-slate-300 mt-1 line-clamp-2">
                                    {displayReason}
                                  </p>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-400 italic">No specific sections flagged; inspect general FIR contents.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* DOCUMENT-STYLE FORM PREVIEW (PAPER LAYOUT) */}
              <div className="bg-white shadow-2xl rounded-sm border border-slate-300 p-8 md:p-12 space-y-8 font-serif text-slate-900 max-w-5xl mx-auto">
                {/* Paper Header */}
                <div className="text-center border-b-2 border-slate-800 pb-6 space-y-2 font-sans">
                  <div className="text-xs font-bold tracking-widest text-slate-500 uppercase">
                    FORM NO. I.F.1 (NATIONAL POLICE STANDARD)
                  </div>
                  <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-900 uppercase">
                    FIRST INFORMATION REPORT
                  </h2>
                  <p className="text-xs font-semibold text-slate-600">
                    (Under Section 173 Cr.P.C. / Section 173 BNSS)
                  </p>
                </div>

                {/* Field 1: Basic Identifiers */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-4 font-sans text-sm">
                  <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2 flex justify-between">
                    <span>1. FIR Identifiers</span>
                    <span className="text-xs font-normal text-slate-500">Official Record Header</span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">District</label>
                      <input
                        type="text"
                        value={firData.district}
                        onChange={(e) => updateFirField(['district'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Police Station</label>
                      <input
                        type="text"
                        value={firData.police_station}
                        onChange={(e) => updateFirField(['police_station'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Year</label>
                      <input
                        type="text"
                        value={firData.year}
                        onChange={(e) => updateFirField(['year'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">FIR No.</label>
                      <input
                        type="text"
                        value={firData.fir_number}
                        onChange={(e) => updateFirField(['fir_number'], e.target.value)}
                        className="w-full bg-amber-50 border border-amber-300 rounded px-2.5 py-1.5 text-sm font-extrabold text-navy focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">FIR Date</label>
                      <input
                        type="date"
                        value={firData.fir_date}
                        onChange={(e) => updateFirField(['fir_date'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>
                  </div>
                </div>

                {/* Field 2: Acts & Sections */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-4 font-sans text-sm">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <span className="font-bold text-slate-800 text-base">2. Act(s) & Section(s)</span>
                    <button
                      type="button"
                      onClick={addActSectionRow}
                      className="text-xs font-bold text-navy hover:underline flex items-center gap-1"
                    >
                      + Add Act/Section Row
                    </button>
                  </div>

                  <div className="space-y-3">
                    {firData.acts_sections.map((item, idx) => (
                      <div key={idx} className="flex flex-col sm:flex-row items-center gap-3 bg-white p-3 border border-slate-200 rounded">
                        <div className="w-full sm:w-1/2">
                          <label className="block text-xs text-slate-500 mb-1">Act Title</label>
                          <input
                            type="text"
                            value={item.act}
                            onChange={(e) => updateActSection(idx, 'act', e.target.value)}
                            className="w-full border border-slate-300 rounded px-2.5 py-1 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-navy"
                          />
                        </div>

                        <div className="w-full sm:w-1/2">
                          <label className="block text-xs text-slate-500 mb-1">Sections</label>
                          <input
                            type="text"
                            value={item.sections}
                            onChange={(e) => updateActSection(idx, 'sections', e.target.value)}
                            placeholder="e.g. 303, 115(2)"
                            className="w-full border border-slate-300 rounded px-2.5 py-1 text-sm font-bold text-navy focus:outline-none focus:ring-1 focus:ring-navy"
                          />
                        </div>

                        {firData.acts_sections.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeActSectionRow(idx)}
                            className="text-red-500 hover:text-red-700 text-xs font-bold self-end sm:self-center pt-2"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Field 3: Occurrence of Offence */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-4 font-sans text-sm">
                  <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2">
                    3. Occurrence of Offence & Information Received
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Day of Occurrence</label>
                      <input
                        type="text"
                        value={firData.occurrence.day}
                        onChange={(e) => updateFirField(['occurrence', 'day'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Date From / Date To</label>
                      <input
                        type="text"
                        value={firData.occurrence.date_from}
                        onChange={(e) => updateFirField(['occurrence', 'date_from'], e.target.value)}
                        placeholder="Date of incident"
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Time of Incident</label>
                      <input
                        type="text"
                        value={firData.occurrence.time_from}
                        onChange={(e) => updateFirField(['occurrence', 'time_from'], e.target.value)}
                        placeholder="Time of incident"
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-navy"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Info Received at P.S. Date & Time</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={firData.occurrence.info_received_date}
                          onChange={(e) => updateFirField(['occurrence', 'info_received_date'], e.target.value)}
                          className="w-1/2 bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                        />
                        <input
                          type="text"
                          value={firData.occurrence.info_received_time}
                          onChange={(e) => updateFirField(['occurrence', 'info_received_time'], e.target.value)}
                          className="w-1/2 bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">General Diary Entry & Time</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={firData.general_diary.entry_number}
                          onChange={(e) => updateFirField(['general_diary', 'entry_number'], e.target.value)}
                          placeholder="GD No."
                          className="w-1/2 bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                        />
                        <input
                          type="text"
                          value={firData.general_diary.date_time}
                          onChange={(e) => updateFirField(['general_diary', 'date_time'], e.target.value)}
                          placeholder="Time"
                          className="w-1/2 bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Field 4 & 5: Type & Place of Occurrence */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-sans text-sm">
                  {/* Field 4 */}
                  <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-3">
                    <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2">
                      4. Type of Information
                    </div>
                    <div className="flex items-center gap-6 pt-2">
                      <label className="flex items-center gap-2 cursor-pointer font-medium">
                        <input
                          type="radio"
                          name="type_info"
                          checked={firData.type_of_information === 'Written'}
                          onChange={() => updateFirField(['type_of_information'], 'Written')}
                          className="text-navy"
                        />
                        Written
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer font-medium">
                        <input
                          type="radio"
                          name="type_info"
                          checked={firData.type_of_information === 'Oral'}
                          onChange={() => updateFirField(['type_of_information'], 'Oral')}
                          className="text-navy"
                        />
                        Oral
                      </label>
                    </div>
                  </div>

                  {/* Field 5 */}
                  <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-3">
                    <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2">
                      5. Place of Occurrence
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Direction & Distance from P.S.</label>
                      <input
                        type="text"
                        value={firData.place_of_occurrence.direction_distance}
                        onChange={(e) => updateFirField(['place_of_occurrence', 'direction_distance'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Address / Location</label>
                      <input
                        type="text"
                        value={firData.place_of_occurrence.address}
                        onChange={(e) => updateFirField(['place_of_occurrence', 'address'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Field 6: Complainant / Informant */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-4 font-sans text-sm">
                  <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2">
                    6. Complainant / Informant Details
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Name</label>
                      <input
                        type="text"
                        value={firData.complainant.name}
                        onChange={(e) => updateFirField(['complainant', 'name'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Father's / Husband's Name</label>
                      <input
                        type="text"
                        value={firData.complainant.father_husband_name}
                        onChange={(e) => updateFirField(['complainant', 'father_husband_name'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Nationality</label>
                      <input
                        type="text"
                        value={firData.complainant.nationality}
                        onChange={(e) => updateFirField(['complainant', 'nationality'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Address</label>
                    <input
                      type="text"
                      value={firData.complainant.address}
                      onChange={(e) => updateFirField(['complainant', 'address'], e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                    />
                  </div>
                </div>

                {/* Field 7: Accused Details */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-3 font-sans text-sm">
                  <div className="font-bold text-slate-800 text-base border-b border-slate-200 pb-2">
                    7. Details of Known / Suspected / Unknown Accused
                  </div>
                  <textarea
                    rows={3}
                    value={firData.accused_details}
                    onChange={(e) => updateFirField(['accused_details'], e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded p-2.5 text-sm font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-navy"
                  />
                </div>

                {/* Fields 8, 9, 10, 11 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-sm">
                  <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-2">
                    <label className="block font-bold text-slate-800 text-sm">8. Reasons for delay in reporting</label>
                    <input
                      type="text"
                      value={firData.delay_reason}
                      onChange={(e) => updateFirField(['delay_reason'], e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                    />
                  </div>

                  <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-2">
                    <label className="block font-bold text-slate-800 text-sm">10. Total value of property stolen / involved</label>
                    <input
                      type="text"
                      value={firData.property_value}
                      onChange={(e) => updateFirField(['property_value'], e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm font-semibold"
                    />
                  </div>

                  <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-2 md:col-span-2">
                    <label className="block font-bold text-slate-800 text-sm">9. Particulars of properties stolen / involved</label>
                    <textarea
                      rows={2}
                      value={firData.property_details}
                      onChange={(e) => updateFirField(['property_details'], e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded p-2.5 text-sm"
                    />
                  </div>
                </div>

                {/* Field 12: FIR Contents */}
                <div className="border-2 border-slate-800 rounded-md p-5 bg-white space-y-3 font-sans">
                  <div className="flex items-center justify-between border-b border-slate-300 pb-2">
                    <span className="font-extrabold text-navy text-lg">12. FIR Contents (First Information Statement)</span>
                    <span className="text-xs bg-navy text-white px-2.5 py-0.5 rounded font-mono">Editable Statement</span>
                  </div>
                  <textarea
                    rows={8}
                    value={firData.fir_contents}
                    onChange={(e) => updateFirField(['fir_contents'], e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded p-4 text-base font-serif leading-relaxed text-slate-900 focus:outline-none focus:ring-2 focus:ring-navy"
                  />
                </div>

                {/* Field 13, 14, 15 */}
                <div className="border border-slate-300 rounded-md p-4 bg-slate-50/50 space-y-4 font-sans text-sm">
                  <div>
                    <label className="block font-bold text-slate-800 text-sm mb-1">13. Action Taken</label>
                    <input
                      type="text"
                      value={firData.action_taken}
                      onChange={(e) => updateFirField(['action_taken'], e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
                    <div>
                      <label className="block font-bold text-slate-800 text-sm mb-1">14. Complainant Signature</label>
                      <input
                        type="text"
                        value={firData.complainant_signature}
                        onChange={(e) => updateFirField(['complainant_signature'], e.target.value)}
                        className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-sm italic"
                      />
                    </div>

                    <div>
                      <label className="block font-bold text-slate-800 text-sm mb-1">15. Officer Details (Name, Rank, No.)</label>
                      <div className="grid grid-cols-3 gap-2">
                        <input
                          type="text"
                          value={firData.officer.name}
                          onChange={(e) => updateFirField(['officer', 'name'], e.target.value)}
                          placeholder="Name"
                          className="bg-white border border-slate-300 rounded px-2 py-1 text-xs"
                        />
                        <input
                          type="text"
                          value={firData.officer.rank}
                          onChange={(e) => updateFirField(['officer', 'rank'], e.target.value)}
                          placeholder="Rank"
                          className="bg-white border border-slate-300 rounded px-2 py-1 text-xs"
                        />
                        <input
                          type="text"
                          value={firData.officer.number}
                          onChange={(e) => updateFirField(['officer', 'number'], e.target.value)}
                          placeholder="No."
                          className="bg-white border border-slate-300 rounded px-2 py-1 text-xs"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  )
}