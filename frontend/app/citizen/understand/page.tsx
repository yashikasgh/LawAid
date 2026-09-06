// app/citizen/understand/page.tsx
'use client'
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
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
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8 max-w-6xl">
          <h1 className="text-2xl font-bold text-navy mb-2">Understand Your FIR</h1>
          <p className="text-sm text-gray-500 mb-6">
            Upload any First Information Report (PDF or image). Our system extracts the legal text and explains allegations, applicable sections, and your constitutional rights in simple terms.
          </p>

          <div className="flex gap-6">
            {/* Upload box */}
            <div
              {...getRootProps()}
              className={`w-96 h-72 border-2 border-dashed rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition shrink-0 ${
                isDragActive ? 'border-lawblue bg-lblue' : 'border-gray-300 hover:border-lawblue bg-white'
              }`}
            >
              <input {...getInputProps()} />
              <div className="text-5xl mb-3">📄</div>
              <p className="text-center font-semibold text-gray-700 text-sm mb-1">
                {isDragActive ? 'Drop FIR document here' : 'Drag & drop FIR document here'}
              </p>
              <p className="text-xs text-gray-400">or click to browse files</p>
              <p className="text-[11px] text-gray-400 mt-3">Supports: PDF, JPG, PNG (up to 10MB)</p>
            </div>

            {/* Results container */}
            <div className="flex-1">
              {loading && (
                <div className="bg-white rounded-2xl p-8 shadow-sm space-y-4">
                  <div className="animate-pulse bg-gray-200 rounded-xl h-6 w-1/3" />
                  <div className="animate-pulse bg-gray-200 rounded-xl h-24" />
                  <div className="animate-pulse bg-gray-200 rounded-xl h-36" />
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
                  {error}
                </div>
              )}

              {!loading && !result && !error && (
                <div className="bg-white rounded-2xl p-8 border border-dashed border-gray-200 text-center text-gray-400 text-sm">
                  No document uploaded yet. Upload an FIR on the left to see the breakdown.
                </div>
              )}

              {result && (
                <div className="bg-white rounded-2xl p-6 shadow-sm space-y-6">
                  {/* Status header */}
                  <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                    <span className="bg-green-100 text-green-700 text-xs font-bold px-3 py-1 rounded-full border border-green-200">
                      ✓ Document Processed ({result.filename})
                    </span>
                    <span className="text-xs text-gray-400 font-mono">ID: {result.file_id}</span>
                  </div>

                  {/* Summary */}
                  <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                    <h3 className="font-bold text-navy text-sm mb-1.5">Plain-Language Summary</h3>
                    <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-line">{result.summary}</p>
                  </div>

                  {/* Charges Breakdown */}
                  {result.charges && result.charges.length > 0 && (
                    <div>
                      <h3 className="font-bold text-navy text-sm mb-3">Identified Offences & Legal Sections</h3>
                      <div className="space-y-2.5">
                        {result.charges.map((c, idx) => (
                          <div key={idx} className="border border-gray-200 rounded-xl p-3.5 bg-gray-50/50">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-navy text-sm">§{c.section} — {c.title}</span>
                              {c.bailable && (
                                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                                  c.bailable.toLowerCase().includes('non')
                                    ? 'bg-red-50 text-red-700 border-red-200'
                                    : 'bg-green-50 text-green-700 border-green-200'
                                }`}>
                                  {c.bailable}
                                </span>
                              )}
                            </div>
                            {c.punishment && (
                              <p className="text-xs text-gray-600">
                                <strong className="text-gray-800">Punishment:</strong> {c.punishment}
                              </p>
                            )}
                            {c.reasoning && (
                              <p className="text-xs text-gray-500 mt-1 italic">{c.reasoning}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citizen Rights */}
                  {result.rights && result.rights.length > 0 && (
                    <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4">
                      <h3 className="font-bold text-amber-900 text-sm mb-2">⚖ Your Immediate Legal Rights</h3>
                      <ul className="list-disc list-inside space-y-1 text-xs text-amber-950">
                        {result.rights.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Suggested Next Steps */}
                  {result.next_steps && result.next_steps.length > 0 && (
                    <div className="bg-green-50/60 border border-green-200 rounded-xl p-4">
                      <h3 className="font-bold text-green-900 text-sm mb-2">🛡 Recommended Next Steps</h3>
                      <ul className="list-disc list-inside space-y-1 text-xs text-green-950">
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
        </main>
      </div>
    </div>
  )
}