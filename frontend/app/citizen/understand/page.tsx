'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import { firAPI } from '@/lib/api'

type ChargeItem = {
  section: string
  title: string
  punishment?: string
  bailable?: string
  reasoning?: string
}

type UnderstandResponse = {
  status: string
  file_id: string
  filename: string
  extracted_text?: string
  summary: string
  charges: ChargeItem[]
  reference_provisions?: ChargeItem[]
  rights: string[]
  next_steps: string[]
}

export default function UnderstandPage() {
  const [result, setResult] = useState<UnderstandResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await firAPI.understand(files[0])
      setResult(res.data)
    } catch {
      setError('Analysis failed. Make sure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': [] },
    maxFiles: 1,
  })

  return (
    <div className="min-h-screen text-[#12335B]">
      <Navbar />

      {/* Background */}
      <main className="relative min-h-[calc(100vh-64px)] overflow-hidden">

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
          <div className="mb-8 flex items-start justify-between gap-6">

            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="h-px w-10 bg-[#b98528]" />

                <span className="text-[11px] tracking-[0.3em] uppercase text-white font-medium">
                  MY FIRs
                </span>
              </div>

              <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                Understand Your FIR
              </h1>

              <p className="mt-3 max-w-5xl text-[#dca45a] text-sm md:text-base leading-relaxed">
                Upload any First Information Report (PDF or image). Our system
                extracts the legal text and explains allegations, applicable
                sections, and your constitutional rights in simple terms.
              </p>
            </div>

            {/* Save Button */}
            <button
              type="button"
              className="shrink-0 inline-flex items-center gap-2 rounded-full bg-[#b98528] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#9f7020] hover:-translate-y-0.5"
            >
              Save
            </button>

          </div>

          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-[390px_1fr] gap-6">

            {/* Upload box */}
            <div
              {...getRootProps()}
              className={`min-h-[335px] border border-white/70 rounded-[20px] p-7 flex flex-col items-center justify-center cursor-pointer transition backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] ${
                isDragActive
                  ? 'border-[#b98528] bg-white/80'
                  : 'bg-white/75 hover:bg-white/85 hover:-translate-y-0.5'
              }`}
            >
              <input {...getInputProps()} />

              <div className="w-16 h-16 rounded-[14px] border border-[#d2a14b]/50 bg-[#f8f6f1]/90 flex items-center justify-center mb-6">
                <svg
                  width="36"
                  height="36"
                  viewBox="0 0 36 36"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M9 4.5H22L28 10.5V31.5H9V4.5Z"
                    stroke="#B98528"
                    strokeWidth="1.7"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M22 4.5V10.5H28"
                    stroke="#B98528"
                    strokeWidth="1.7"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M13 16H24M13 20.5H24M13 25H20"
                    stroke="#12335B"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <p className="text-center font-serif text-xl font-semibold text-[#12335B] mb-2">
                {isDragActive
                  ? 'Drop FIR document here'
                  : 'Drag & drop FIR document here'}
              </p>

              <p className="text-sm text-[#56718f]">
                or click to browse files
              </p>

              <div className="mt-6 h-px w-12 bg-[#b98528]" />

              <p className="text-[11px] text-[#7890a8] mt-4">
                Supports: PDF, JPG, PNG (up to 10MB)
              </p>
            </div>

            {/* Results container */}
            <div className="min-w-0">

              {loading && (
                <div className="bg-white/75 backdrop-blur-md rounded-[20px] p-8 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 space-y-4">
                  <div className="animate-pulse bg-gray-200 rounded-xl h-6 w-1/3" />
                  <div className="animate-pulse bg-gray-200 rounded-xl h-24" />
                  <div className="animate-pulse bg-gray-200 rounded-xl h-36" />
                </div>
              )}

              {error && (
                <div className="bg-red-50/90 border border-red-200 text-red-700 p-5 rounded-[18px] text-sm shadow-sm">
                  {error}
                </div>
              )}

              {!loading && !result && !error && (
                <div className="min-h-[335px] bg-white/75 backdrop-blur-md rounded-[20px] p-8 border border-white/70 text-center flex flex-col items-center justify-center shadow-[0_15px_40px_rgba(18,51,91,0.10)]">

                  <div className="w-14 h-14 rounded-full bg-[#f8f6f1] border border-[#d2a14b]/40 flex items-center justify-center mb-5">
                    <svg
                      width="28"
                      height="28"
                      viewBox="0 0 36 36"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M9 4.5H22L28 10.5V31.5H9V4.5Z"
                        stroke="#B98528"
                        strokeWidth="1.7"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M22 4.5V10.5H28"
                        stroke="#B98528"
                        strokeWidth="1.7"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M13 16H24M13 20.5H24M13 25H20"
                        stroke="#12335B"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>

                  <h2 className="font-serif text-2xl font-semibold text-[#12335B]">
                    Your FIR Analysis
                  </h2>

                  <p className="mt-2 max-w-md text-sm text-[#7890a8] leading-relaxed">
                    No document uploaded yet. Upload an FIR on the left to see
                    the legal breakdown.
                  </p>
                </div>
              )}

              {result && (
                <div className="bg-white/80 backdrop-blur-md rounded-[20px] p-6 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 space-y-6">

                  {/* Status header */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-[#12335B]/10">

                    <span className="bg-green-100 text-green-700 text-xs font-bold px-3 py-1.5 rounded-full border border-green-200">
                      ✓ Document Processed ({result.filename})
                    </span>

                    <span className="text-xs text-gray-400 font-mono">
                      ID: {result.file_id}
                    </span>

                  </div>

                  {/* Summary */}
                  <div className="bg-[#eef4fa]/80 border border-[#d8e4ef] rounded-[16px] p-5">
                    <h3 className="font-serif font-bold text-[#12335B] text-base mb-2">
                      Plain-Language Summary
                    </h3>

                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                      {result.summary}
                    </p>
                  </div>

                  {/* Charges Breakdown */}
                  {result.charges && result.charges.length > 0 && (
                    <div>
                      <h3 className="font-serif font-bold text-[#12335B] text-base mb-4">
                        Identified Offences & Legal Sections
                      </h3>

                      <div className="space-y-3">
                        {result.charges.map((c, idx) => (
                          <div
                            key={idx}
                            className="border border-[#12335B]/10 rounded-[16px] p-4 bg-white/60"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">

                              <span className="font-bold text-[#12335B] text-sm">
                                §{c.section} — {c.title}
                              </span>

                              {c.bailable && (
                                <span
                                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                                    c.bailable
                                      .toLowerCase()
                                      .includes('non')
                                      ? 'bg-red-50 text-red-700 border-red-200'
                                      : 'bg-green-50 text-green-700 border-green-200'
                                  }`}
                                >
                                  {c.bailable}
                                </span>
                              )}

                            </div>

                            {c.punishment && (
                              <p className="text-xs text-gray-600">
                                <strong className="text-gray-800">
                                  Punishment:
                                </strong>{' '}
                                {c.punishment}
                              </p>
                            )}

                            {c.reasoning && (
                              <p className="text-xs text-gray-500 mt-1 italic">
                                {c.reasoning}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reference Provisions (Fallback Path) */}
                  {result.reference_provisions && result.reference_provisions.length > 0 && (
                    <div className="bg-slate-50/80 border border-slate-200 rounded-[16px] p-5 space-y-3">
                      <div>
                        <h3 className="font-serif font-bold text-[#12335B] text-base mb-1">
                          Retrieved BNS Provisions for Reference
                        </h3>
                        <p className="text-xs text-slate-600 leading-relaxed mb-3">
                          These provisions were retrieved from the BNS database but were not validated against the facts because automated legal analysis was unavailable.
                        </p>
                      </div>

                      <div className="space-y-3">
                        {result.reference_provisions.map((c, idx) => (
                          <div
                            key={idx}
                            className="border border-[#12335B]/10 rounded-[16px] p-4 bg-white/80 shadow-sm"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                              <span className="font-bold text-[#12335B] text-sm">
                                §{c.section} — {c.title}
                              </span>

                              {c.bailable && (
                                <span
                                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                                    c.bailable
                                      .toLowerCase()
                                      .includes('non')
                                      ? 'bg-red-50 text-red-700 border-red-200'
                                      : 'bg-green-50 text-green-700 border-green-200'
                                  }`}
                                >
                                  {c.bailable}
                                </span>
                              )}
                            </div>

                            {c.punishment && (
                              <p className="text-xs text-gray-600">
                                <strong className="text-gray-800">
                                  Punishment:
                                </strong>{' '}
                                {c.punishment}
                              </p>
                            )}

                            {c.reasoning && (
                              <p className="text-xs text-gray-500 mt-1 italic">
                                {c.reasoning}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citizen Rights */}
                  {result.rights && result.rights.length > 0 && (
                    <div className="bg-amber-50/70 border border-amber-200 rounded-[16px] p-5">
                      <h3 className="font-serif font-bold text-amber-900 text-base mb-3">
                        ⚖ Your Immediate Legal Rights
                      </h3>

                      <ul className="list-disc list-inside space-y-1.5 text-xs text-amber-950">
                        {result.rights.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Suggested Next Steps */}
                  {result.next_steps && result.next_steps.length > 0 && (
                    <div className="bg-green-50/70 border border-green-200 rounded-[16px] p-5">
                      <h3 className="font-serif font-bold text-green-900 text-base mb-3">
                        🛡 Recommended Next Steps
                      </h3>

                      <ul className="list-disc list-inside space-y-1.5 text-xs text-green-950">
                        {result.next_steps.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                </div>
              )}

            </div>
          </div>
        </div>
      </main>
    </div>
  )
}