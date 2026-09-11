// app/citizen/understand/page.tsx
'use client'
import { useState, useCallback, useRef, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import { firAPI } from '@/lib/api'

type ChargeItem = {
  section: string
  clause?: string
  title: string
  punishment?: string
  bailable?: string
  cognizable?: string
  court?: string
  reasoning?: string
  applicability?: string
  status?: string
}

type UnderstandResponse = {
  status: string
  file_id: string
  filename: string
  extracted_text?: string
  entities?: string[]
  summary: string
  charges: ChargeItem[]
  uncertain_provisions?: ChargeItem[]
  analysis?: ChargeItem[]
  rights: string[]
  next_steps: string[]
  disclaimer?: string
}

export default function UnderstandPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<UnderstandResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [progressStep, setProgressStep] = useState<number>(0)
  const [error, setError] = useState('')

  // Camera state
  const [isCameraOpen, setIsCameraOpen] = useState(false)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const [capturedPhotoUrl, setCapturedPhotoUrl] = useState<string | null>(null)
  const [cameraError, setCameraError] = useState('')
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const mobileCameraInputRef = useRef<HTMLInputElement | null>(null)

  // Clean up object URLs
  useEffect(() => {
    return () => {
      if (filePreviewUrl) URL.revokeObjectURL(filePreviewUrl)
      if (capturedPhotoUrl) URL.revokeObjectURL(capturedPhotoUrl)
    }
  }, [filePreviewUrl, capturedPhotoUrl])

  // Handle file selection
  const handleFileSelected = (file: File) => {
    setError('')
    setResult(null)
    setSelectedFile(file)
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setFilePreviewUrl(url)
    } else {
      setFilePreviewUrl(null)
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) {
      handleFileSelected(acceptedFiles[0])
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': [], 'image/png': [], 'image/jpg': [], 'application/pdf': [] },
    maxFiles: 1,
    noClick: true, // Custom buttons trigger file inputs
  })

  const pdfInputRef = useRef<HTMLInputElement | null>(null)
  const imageInputRef = useRef<HTMLInputElement | null>(null)

  // Start Analysis
  const handleAnalyze = async () => {
    if (!selectedFile) return
    setLoading(true)
    setError('')
    setResult(null)
    setProgressStep(1) // Step 1: Uploading

    const timer1 = setTimeout(() => setProgressStep(2), 1200) // Step 2: OCR / Extracting
    const timer2 = setTimeout(() => setProgressStep(3), 3000) // Step 3: Legal Analysis

    try {
      const res = await firAPI.understand(selectedFile)
      setResult(res.data)
    } catch (err: any) {
      const backendDetail = err.response?.data?.detail
      if (backendDetail) {
        setError(backendDetail)
      } else if (err.message) {
        setError(`Analysis failed: ${err.message}`)
      } else {
        setError('Analysis failed. Please check that your FIR file is readable and try again.')
      }
    } finally {
      clearTimeout(timer1)
      clearTimeout(timer2)
      setLoading(false)
      setProgressStep(0)
    }
  }

  // WebRTC Camera Controls
  const startCamera = async () => {
    setCameraError('')
    setCapturedPhotoUrl(null)
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('WebRTC camera not supported')
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      })
      setCameraStream(stream)
      setIsCameraOpen(true)
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream
        }
      }, 100)
    } catch (err: any) {
      console.warn('Camera access error, falling back to native file picker:', err)
      setIsCameraOpen(false)
      // Fallback to mobile input capture
      if (mobileCameraInputRef.current) {
        mobileCameraInputRef.current.click()
      } else {
        setError('Camera access unavailable or permission denied. Please upload an image file instead.')
      }
    }
  }

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop())
      setCameraStream(null)
    }
    setIsCameraOpen(false)
    setCapturedPhotoUrl(null)
  }

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => {
        if (blob) {
          const photoFile = new File([blob], `fir_camera_${Date.now()}.jpg`, { type: 'image/jpeg' })
          const previewUrl = URL.createObjectURL(photoFile)
          setCapturedPhotoUrl(previewUrl)
        }
      }, 'image/jpeg', 0.92)
    }
  }

  const confirmCapturedPhoto = () => {
    if (canvasRef.current) {
      canvasRef.current.toBlob((blob) => {
        if (blob) {
          const photoFile = new File([blob], `fir_camera_${Date.now()}.jpg`, { type: 'image/jpeg' })
          handleFileSelected(photoFile)
          stopCamera()
        }
      }, 'image/jpeg', 0.92)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8 max-w-6xl">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-bold text-navy">Understand Your FIR</h1>
            <span className="text-xs bg-blue-100 text-lawblue px-3 py-1 rounded-full font-semibold border border-blue-200">
              AI Legal Interpreter & OCR
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-6">
            Upload your First Information Report (PDF document or photo) or capture an image of your printed copy using your camera.
            Our AI extracts the text via OCR and explains allegations, legal provisions, and your rights in simple terms.
          </p>

          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left Column: Upload & Options */}
            <div className="w-full lg:w-96 flex flex-col gap-4 shrink-0">
              {/* Dropzone Container */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-2xl p-6 flex flex-col items-center justify-center transition bg-white shadow-sm ${
                  isDragActive ? 'border-lawblue bg-blue-50/50' : 'border-gray-300 hover:border-lawblue'
                }`}
              >
                <input {...getInputProps()} />
                <div className="text-4xl mb-2">📄</div>
                <p className="text-center font-semibold text-gray-700 text-sm mb-1">
                  {isDragActive ? 'Drop FIR file here' : 'Drag & drop FIR document or photo'}
                </p>
                <p className="text-xs text-gray-400 text-center mb-4">Supports PDF, JPG, PNG (up to 10MB)</p>

                {/* Option Buttons */}
                <div className="w-full space-y-2">
                  {/* Upload PDF */}
                  <button
                    type="button"
                    onClick={() => pdfInputRef.current?.click()}
                    className="w-full flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold py-2.5 px-3 rounded-xl border border-slate-300 transition"
                  >
                    <span>📑</span> Upload PDF Document
                  </button>
                  <input
                    ref={pdfInputRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
                  />

                  {/* Upload Image */}
                  <button
                    type="button"
                    onClick={() => imageInputRef.current?.click()}
                    className="w-full flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold py-2.5 px-3 rounded-xl border border-slate-300 transition"
                  >
                    <span>🖼️</span> Upload Image (JPG / PNG)
                  </button>
                  <input
                    ref={imageInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/jpg"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
                  />

                  {/* Take Photo / Camera */}
                  <button
                    type="button"
                    onClick={startCamera}
                    className="w-full flex items-center justify-center gap-2 bg-lawblue hover:bg-blue-700 text-white text-xs font-semibold py-2.5 px-3 rounded-xl shadow-sm transition"
                  >
                    <span>📷</span> Take Photo / Use Camera
                  </button>
                  {/* Mobile Camera Fallback Input */}
                  <input
                    ref={mobileCameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
                  />
                </div>
              </div>

              {/* Selected File Preview Card */}
              {selectedFile && (
                <div className="bg-white rounded-2xl p-4 border border-blue-200 shadow-sm space-y-3">
                  <div className="flex items-start gap-3">
                    {filePreviewUrl ? (
                      <img
                        src={filePreviewUrl}
                        alt="FIR Preview"
                        className="w-16 h-20 object-cover rounded-lg border border-gray-200 shrink-0"
                      />
                    ) : (
                      <div className="w-16 h-20 bg-blue-50 border border-blue-200 rounded-lg flex flex-col items-center justify-center text-lawblue text-2xl shrink-0">
                        📑
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-navy truncate" title={selectedFile.name}>
                        {selectedFile.name}
                      </p>
                      <p className="text-[11px] text-gray-500 mt-0.5">
                        Size: {formatFileSize(selectedFile.size)}
                      </p>
                      <span className="inline-block mt-1 text-[10px] uppercase font-bold bg-gray-100 text-gray-700 px-2 py-0.5 rounded border border-gray-300">
                        {selectedFile.type || 'DOCUMENT'}
                      </span>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <button
                      type="button"
                      onClick={handleAnalyze}
                      disabled={loading}
                      className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold text-xs py-2 px-3 rounded-xl shadow-sm transition flex items-center justify-center gap-1.5"
                    >
                      {loading ? 'Processing...' : '🔍 Analyze FIR'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null)
                        setFilePreviewUrl(null)
                        setResult(null)
                      }}
                      disabled={loading}
                      className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold py-2 px-3 rounded-xl border border-gray-300 transition"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Loading / Error / Results */}
            <div className="flex-1">
              {/* Progress & Loading Indicator */}
              {loading && (
                <div className="bg-white rounded-2xl p-8 shadow-sm space-y-6">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin text-lawblue text-2xl">⏳</div>
                    <div>
                      <h3 className="font-bold text-navy text-sm">Processing Document</h3>
                      <p className="text-xs text-gray-500">Please wait while LawAid extracts and analyzes the text.</p>
                    </div>
                  </div>

                  {/* Progress Steps */}
                  <div className="space-y-3 pt-2">
                    <div className={`flex items-center gap-3 text-xs ${progressStep >= 1 ? 'text-green-700 font-bold' : 'text-gray-400'}`}>
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${progressStep >= 1 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                        {progressStep > 1 ? '✓' : '1'}
                      </span>
                      <span>Uploading FIR File</span>
                    </div>

                    <div className={`flex items-center gap-3 text-xs ${progressStep >= 2 ? 'text-green-700 font-bold' : 'text-gray-400'}`}>
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${progressStep >= 2 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                        {progressStep > 2 ? '✓' : '2'}
                      </span>
                      <span>Extracting Text & Running OCR</span>
                    </div>

                    <div className={`flex items-center gap-3 text-xs ${progressStep >= 3 ? 'text-green-700 font-bold' : 'text-gray-400'}`}>
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${progressStep >= 3 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                        3
                      </span>
                      <span>Analyzing Legal Provisions with LawAid AI</span>
                    </div>
                  </div>

                  <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-lawblue h-full transition-all duration-700"
                      style={{ width: `${progressStep === 1 ? 33 : progressStep === 2 ? 66 : 90}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Banner */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-800 p-5 rounded-2xl shadow-sm space-y-2 mb-6">
                  <div className="flex items-center gap-2 font-bold text-sm text-red-900">
                    <span>⚠️</span> Analysis Could Not Be Completed
                  </div>
                  <p className="text-xs leading-relaxed">{error}</p>
                  <p className="text-[11px] text-red-700 pt-1">
                    Tip: Make sure your uploaded document or photo is clear, well-lit, and contains readable FIR text.
                  </p>
                </div>
              )}

              {/* Initial Empty State */}
              {!loading && !result && !error && (
                <div className="bg-white rounded-2xl p-10 border border-dashed border-gray-300 text-center space-y-3 shadow-sm">
                  <div className="text-5xl">📄</div>
                  <h3 className="font-bold text-navy text-base">No Document Selected Yet</h3>
                  <p className="text-xs text-gray-500 max-w-md mx-auto">
                    Select a PDF, image file, or capture a photo using your camera on the left, then click <strong>Analyze FIR</strong> to generate plain-language explanations and legal provisions.
                  </p>
                </div>
              )}

              {/* Results Container */}
              {result && !loading && (
                <div className="bg-white rounded-2xl p-6 shadow-sm space-y-6">
                  {/* Status header */}
                  <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                    <span className="bg-green-100 text-green-800 text-xs font-bold px-3 py-1 rounded-full border border-green-200 flex items-center gap-1.5">
                      <span>✓</span> FIR Analyzed ({result.filename})
                    </span>
                    <span className="text-xs text-gray-400 font-mono">Document ID: {result.file_id}</span>
                  </div>

                  {/* Summary */}
                  <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-4.5">
                    <h3 className="font-bold text-navy text-sm mb-1.5 flex items-center gap-1.5">
                      <span>📋</span> Plain-Language Explanation
                    </h3>
                    <p className="text-xs text-gray-800 leading-relaxed whitespace-pre-line">{result.summary}</p>
                  </div>

                  {/* PII / Entities Detected */}
                  {result.entities && result.entities.length > 0 && (
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5">
                      <h4 className="font-bold text-gray-700 text-xs mb-2 flex items-center gap-1">
                        <span>🔒</span> Protected Privacy Entities
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {result.entities.map((ent, idx) => (
                          <span key={idx} className="bg-white text-gray-700 border border-gray-300 text-[10px] font-medium px-2 py-0.5 rounded-md shadow-2xs">
                            {ent}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Charges & Legal Analysis */}
                  {(() => {
                    const renderCard = (c: ChargeItem, idx: number, cardType: 'supported' | 'uncertain') => {
                      const isSupp = cardType === 'supported'
                      return (
                        <div key={idx} className={`border rounded-xl p-4 transition ${isSupp ? 'border-emerald-200 bg-emerald-50/20' : 'border-amber-200 bg-amber-50/20'}`}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="font-bold text-navy text-sm">
                              {c.section ? `§ ${c.section}${c.clause ? `(${c.clause})` : ''}` : 'Offence'} — {c.title || 'Legal Provision'}
                            </span>
                            <div className="flex gap-1.5 items-center">
                              {c.bailable && (
                                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                                  c.bailable.toLowerCase().includes('non')
                                    ? 'bg-red-100 text-red-800 border-red-200'
                                    : 'bg-green-100 text-green-800 border-green-200'
                                }`}>
                                  {c.bailable}
                                </span>
                              )}
                              <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full ${isSupp ? 'bg-emerald-600 text-white' : 'bg-amber-500 text-white'}`}>
                                {isSupp ? 'SUPPORTED' : 'UNCERTAIN'}
                              </span>
                            </div>
                          </div>
                          {c.punishment && (
                            <p className="text-xs text-gray-700 mb-1">
                              <strong className="text-gray-900">Punishment:</strong> {c.punishment}
                            </p>
                          )}
                          {c.reasoning && (
                            <p className="text-xs text-gray-700 leading-relaxed bg-white p-2.5 rounded-lg border border-gray-200 mt-2">
                              {c.reasoning}
                            </p>
                          )}
                        </div>
                      )
                    }

                    return (
                      <div className="space-y-5">
                        {/* 1. Supported Provisions */}
                        {result.charges && result.charges.length > 0 && (
                          <div>
                            <h3 className="font-bold text-navy text-sm mb-3 flex items-center gap-1.5">
                              <span>⚖️</span> Identified Offences & Legal Provisions ({result.charges.length})
                            </h3>
                            <div className="space-y-3">
                              {result.charges.map((c, idx) => renderCard(c, idx, 'supported'))}
                            </div>
                          </div>
                        )}

                        {/* 2. Provisions Requiring Further Facts / Provisos */}
                        {result.uncertain_provisions && result.uncertain_provisions.length > 0 && (
                          <div>
                            <h3 className="font-bold text-amber-900 text-sm mb-3 flex items-center gap-1.5">
                              <span>⚠️</span> Provisions Requiring Further Facts / Provisos ({result.uncertain_provisions.length})
                            </h3>
                            <div className="space-y-3">
                              {result.uncertain_provisions.map((c, idx) => renderCard(c, idx, 'uncertain'))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })()}

                  {/* Immediate Rights */}
                  {result.rights && result.rights.length > 0 && (
                    <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4">
                      <h3 className="font-bold text-amber-900 text-sm mb-2 flex items-center gap-1.5">
                        <span>🛡️</span> Your Constitutional & Legal Rights
                      </h3>
                      <ul className="list-disc list-inside space-y-1.5 text-xs text-amber-950">
                        {result.rights.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Next Steps */}
                  {result.next_steps && result.next_steps.length > 0 && (
                    <div className="bg-green-50/70 border border-green-200 rounded-xl p-4">
                      <h3 className="font-bold text-green-900 text-sm mb-2 flex items-center gap-1.5">
                        <span>🚀</span> Recommended Next Steps
                      </h3>
                      <ul className="list-disc list-inside space-y-1.5 text-xs text-green-950">
                        {result.next_steps.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Legal Disclaimer */}
                  {result.disclaimer && (
                    <div className="pt-2 border-t border-gray-100">
                      <p className="text-[11px] text-gray-400 leading-relaxed italic">
                        <strong>Disclaimer:</strong> {result.disclaimer}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* WebRTC Camera Capture Modal */}
          {isCameraOpen && (
            <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl space-y-4 p-5">
                <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                  <h3 className="font-bold text-navy text-sm flex items-center gap-2">
                    <span>📷</span> Capture FIR Document Photo
                  </h3>
                  <button
                    type="button"
                    onClick={stopCamera}
                    className="text-gray-400 hover:text-gray-700 text-lg font-bold"
                  >
                    ✕
                  </button>
                </div>

                <div className="relative bg-black rounded-xl overflow-hidden min-h-[300px] flex items-center justify-center">
                  {capturedPhotoUrl ? (
                    <img src={capturedPhotoUrl} alt="Snapshot Preview" className="max-h-[360px] w-full object-contain" />
                  ) : (
                    <video ref={videoRef} autoPlay playsInline className="max-h-[360px] w-full object-contain" />
                  )}
                  <canvas ref={canvasRef} className="hidden" />
                </div>

                <div className="flex gap-3 pt-2">
                  {capturedPhotoUrl ? (
                    <>
                      <button
                        type="button"
                        onClick={() => setCapturedPhotoUrl(null)}
                        className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-xs py-2.5 px-4 rounded-xl border border-gray-300 transition"
                      >
                        🔄 Re-take Photo
                      </button>
                      <button
                        type="button"
                        onClick={confirmCapturedPhoto}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-sm transition"
                      >
                        ✓ Use This Photo
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={capturePhoto}
                      className="w-full bg-lawblue hover:bg-blue-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-sm transition flex items-center justify-center gap-2"
                    >
                      <span>📸</span> Capture Snapshot
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}