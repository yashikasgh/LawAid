'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import { firAPI } from '@/lib/api'
import { getStoredUser } from '@/lib/auth'

type ChargeItem = {
  section: string
  title: string
  punishment?: string
  bailable?: string
  cognizable?: string
  reasoning?: string
  applicability?: string
  law_requires?: string
  fir_states?: string
  why_may_apply?: string
  what_remains_uncertain?: string
  assessment?: string
}

type UnderstandResponse = {
  status: string
  is_degraded_fallback?: boolean
  sections_recorded_in_fir?: string[]
  has_sections_in_fir?: boolean
  explained_sections?: ChargeItem[]
  potential_sections?: ChargeItem[]
  file_id?: string
  file_stored?: boolean
  filename: string
  extracted_text?: string
  summary: string
  plain_summary?: string
  what_fir_alleges?: string
  unestablished_facts?: string[]
  clarifying_details?: string[]
  bottom_line?: string
  charges: ChargeItem[]
  reference_provisions?: ChargeItem[]
  rights: string[]
  next_steps: string[]
  disclaimer?: string
  fir_metadata?: Record<string, string>
}

type SavedFIRRecord = {
  id: number
  filename: string
  file_type?: string
  file_size?: number
  gridfs_file_id?: string
  summary: string
  charges?: ChargeItem[]
  reference_provisions?: ChargeItem[]
  rights?: string[]
  next_steps?: string[]
  created_at: string
}

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10MB

export default function UnderstandPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<UnderstandResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState('')
  const [error, setError] = useState('')

  // User Auth & Consent state
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null)
  const [consentDismissed, setConsentDismissed] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [saveError, setSaveError] = useState('')

  // Saved FIRs & Tab navigation
  const [savedFirs, setSavedFirs] = useState<SavedFIRRecord[]>([])
  const [activeTab, setActiveTab] = useState<'analyze' | 'saved'>('analyze')
  const [deleteModalId, setDeleteModalId] = useState<number | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Replace / Remove Confirmation Modal State
  const [showReplaceModal, setShowReplaceModal] = useState(false)
  const [pendingAction, setPendingAction] = useState<'select_new' | 'camera' | 'remove' | null>(null)
  const [isSavingAndReplacing, setIsSavingAndReplacing] = useState(false)

  // Camera Modal State
  const [showCameraModal, setShowCameraModal] = useState(false)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [isCameraStarting, setIsCameraStarting] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const stopCamera = useCallback(() => {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop())
      setCameraStream(null)
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setShowCameraModal(false)
    setCameraError(null)
    setIsCameraStarting(false)
  }, [cameraStream])

  // Clean up camera stream on unmount
  useEffect(() => {
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [cameraStream])

  // Attach camera stream to videoRef when modal opens
  useEffect(() => {
    if (showCameraModal && cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream
      videoRef.current.play().catch(() => {})
    }
  }, [showCameraModal, cameraStream])

  useEffect(() => {
    setUser(getStoredUser())
    loadSavedFirs()
  }, [])

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const loadSavedFirs = async () => {
    try {
      const res = await firAPI.getSavedFIRs()
      setSavedFirs(res.data || [])
    } catch {
      // User may not be logged in or server down
    }
  }

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return 'Selected file exceeds the maximum 10MB limit.'
    }
    const ext = file.name.split('.').pop()?.toLowerCase()
    const validExts = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'webp', 'bmp']
    if (!validExts.includes(ext || '')) {
      return 'Unsupported file format. Please upload a PDF, TXT, JPG, PNG, WEBP, or BMP file.'
    }
    return null
  }

  const handleFileSelect = (file: File) => {
    const err = validateFile(file)
    if (err) {
      setError(err)
      return
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }

    setSelectedFile(file)
    setError('')
    setConsentDismissed(false)
    setSaveStatus('idle')
    setSaveError('')

    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
    }
  }

  const runAnalysis = async (fileToAnalyze: File) => {
    setLoading(true)
    setLoadingProgress('Reading document & extracting text...')
    setError('')
    setResult(null)
    setConsentDismissed(false)
    setSaveStatus('idle')

    try {
      setTimeout(() => {
        setLoadingProgress('Retrieving statutory BNS grounding & legal provisions...')
      }, 1200)

      setTimeout(() => {
        setLoadingProgress('Synthesizing plain-language analysis & rights...')
      }, 2400)

      const res = await firAPI.understand(fileToAnalyze)
      setResult(res.data)
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        'Analysis failed. Make sure the backend server is running and the file format is supported.'
      setError(msg)
    } finally {
      setLoading(false)
      setLoadingProgress('')
    }
  }

  const handleNativeInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      const file = files[0]
      handleFileSelect(file)
      await runAnalysis(file)
    }
  }

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    const file = files[0]
    handleFileSelect(file)
    await runAnalysis(file)
  }, [previewUrl])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.bmp'],
    },
    maxFiles: 1,
    noClick: true, // Handle clicks explicitly for 100% reliable trigger
  })

  const resetCurrentDocumentState = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
    setSelectedFile(null)
    setResult(null)
    setError('')
    setConsentDismissed(false)
    setSaveStatus('idle')
    setSaveError('')

    if (fileInputRef.current) fileInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  const startCamera = async () => {
    setCameraError(null)
    setIsCameraStarting(true)
    setShowCameraModal(true)

    if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsCameraStarting(false)
      setCameraError("Camera access isn't available on this browser or device. You can upload an image instead.")
      return
    }

    try {
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        })
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        })
      }

      setCameraStream(stream)
      setIsCameraStarting(false)
    } catch (err: any) {
      setIsCameraStarting(false)
      let errMsg = "Camera access isn't available. You can upload an image instead."
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        errMsg = "Camera permission was denied. Please allow camera access in your browser or upload an image instead."
      } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
        errMsg = "No camera found on this device. You can upload an image instead."
      }
      setCameraError(errMsg)
    }
  }

  const capturePhoto = () => {
    if (!videoRef.current) return
    const video = videoRef.current
    const width = video.videoWidth || 1280
    const height = video.videoHeight || 720

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(video, 0, 0, width, height)

    canvas.toBlob(
      async (blob) => {
        if (!blob) return
        const file = new File([blob], `fir_photo_${Date.now()}.jpg`, { type: 'image/jpeg' })

        // Stop camera stream & close modal
        stopCamera()

        // Handle file selection & run FIR analysis pipeline
        handleFileSelect(file)
        await runAnalysis(file)
      },
      'image/jpeg',
      0.92
    )
  }

  // User intent to remove/replace file
  const requestRemoveOrReplace = (action: 'select_new' | 'camera' | 'remove') => {
    // Check if there is an active analysis that has NOT been saved yet
    const hasUnsavedAnalysis = result != null && saveStatus !== 'saved'

    if (hasUnsavedAnalysis) {
      setPendingAction(action)
      setShowReplaceModal(true)
    } else {
      if (action === 'select_new') {
        resetCurrentDocumentState()
        setTimeout(() => fileInputRef.current?.click(), 50)
      } else if (action === 'camera') {
        startCamera()
      } else if (action === 'remove') {
        resetCurrentDocumentState()
      }
    }
  }

  const handleSaveFIR = async (): Promise<boolean> => {
    if (!result) return false
    setSaveStatus('saving')
    setSaveError('')

    let fileBase64: string | undefined = undefined
    if (selectedFile) {
      try {
        const buffer = await selectedFile.arrayBuffer()
        const bytes = new Uint8Array(buffer)
        let binary = ''
        for (let i = 0; i < bytes.byteLength; i++) {
          binary += String.fromCharCode(bytes[i])
        }
        fileBase64 = btoa(binary)
      } catch {
        fileBase64 = undefined
      }
    }

    try {
      await firAPI.saveFIR({
        filename: result.filename,
        file_type: selectedFile?.type || 'application/pdf',
        file_size: selectedFile?.size || 0,
        file_base64: fileBase64,
        file_id: result.file_id,
        extracted_text: result.extracted_text,
        summary: result.summary,
        charges: result.charges,
        reference_provisions: result.reference_provisions,
        rights: result.rights,
        next_steps: result.next_steps,
        disclaimer: result.disclaimer,
      })
      setSaveStatus('saved')
      loadSavedFirs()
      return true
    } catch (err: any) {
      setSaveStatus('error')
      setSaveError(
        err?.response?.data?.detail || 'Failed to save FIR. Please check your login session.'
      )
      return false
    }
  }

  const handleConfirmSaveAndReplace = async () => {
    setIsSavingAndReplacing(true)
    const success = await handleSaveFIR()
    setIsSavingAndReplacing(false)

    if (success) {
      const action = pendingAction
      setShowReplaceModal(false)
      setPendingAction(null)
      if (action === 'select_new') {
        resetCurrentDocumentState()
        setTimeout(() => fileInputRef.current?.click(), 50)
      } else if (action === 'camera') {
        startCamera()
      } else if (action === 'remove') {
        resetCurrentDocumentState()
      }
    }
  }

  const handleConfirmDontSaveAndReplace = () => {
    const action = pendingAction
    setShowReplaceModal(false)
    setPendingAction(null)
    if (action === 'select_new') {
      resetCurrentDocumentState()
      setTimeout(() => fileInputRef.current?.click(), 50)
    } else if (action === 'camera') {
      startCamera()
    } else if (action === 'remove') {
      resetCurrentDocumentState()
    }
  }

  const handleDeleteSavedFIR = async () => {
    if (deleteModalId === null) return
    setIsDeleting(true)

    try {
      await firAPI.deleteSavedFIR(deleteModalId)
      setDeleteModalId(null)
      loadSavedFirs()
      if (result && (result as any).id === deleteModalId) {
        setResult(null)
      }
    } catch {
      alert('Could not delete saved FIR. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  const viewSavedFIR = (record: SavedFIRRecord) => {
    setResult({
      status: 'ok',
      file_id: record.gridfs_file_id,
      filename: record.filename,
      summary: record.summary,
      charges: record.charges || [],
      reference_provisions: record.reference_provisions || [],
      rights: record.rights || [],
      next_steps: record.next_steps || [],
      disclaimer:
        'Legal analysis saved on ' +
        new Date(record.created_at).toLocaleDateString() +
        '. For informational and educational purposes only.',
    })
    setSaveStatus('saved')
    setActiveTab('analyze')
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="min-h-screen text-[#12335B]">
      <Navbar />

      {/* Hidden File Inputs */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".pdf,.txt,.jpg,.jpeg,.png,.webp,.bmp"
        className="hidden"
        onChange={handleNativeInputChange}
      />
      <input
        type="file"
        ref={cameraInputRef}
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleNativeInputChange}
      />

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

        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-8">
          {/* Top Bar with Title Header & Segmented Tab Controls */}
          <div className="mb-6 flex flex-col md:flex-row md:items-start md:justify-between gap-6">
            {/* HERO SECTION — Shown BEFORE analysis is generated */}
            {!result && (
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <span className="h-px w-10 bg-[#b98528]" />
                  <span className="text-[11px] tracking-[0.3em] uppercase text-white font-medium">
                    MY FIRs & LEGAL BREAKDOWN
                  </span>
                </div>

                <h1 className="font-serif text-3xl md:text-5xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                  Understand Your FIR
                </h1>

                <p className="mt-2.5 max-w-3xl text-[#dca45a] text-sm md:text-base leading-relaxed">
                  Upload any First Information Report (PDF, TXT, or image photo). LawAid extracts the document text, applies statutory legal grounding under Bharatiya Nyaya Sanhita (BNS), and explains key facts, allegations, applicable sections, and your constitutional rights in simple terms.
                </p>
              </div>
            )}

            {/* If result is present, display compact workspace header */}
            {result && (
              <div className="flex items-center gap-3">
                <span className="h-px w-8 bg-[#b98528]" />
                <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[#cc8427] tracking-tight">
                  FIR Analysis Workspace
                </h1>
              </div>
            )}

            {/* Segmented Tab Control — STRICTLY ONE LINE ALWAYS */}
            <div className="flex items-center gap-2 bg-white/40 p-1.5 rounded-full border border-white/60 backdrop-blur-md self-start shrink-0 flex-nowrap whitespace-nowrap">
              <button
                type="button"
                onClick={() => setActiveTab('analyze')}
                className={`px-4 sm:px-5 py-2 text-xs font-bold rounded-full transition whitespace-nowrap ${
                  activeTab === 'analyze'
                    ? 'bg-[#b98528] text-white shadow-sm'
                    : 'text-[#12335B] hover:bg-white/50'
                }`}
              >
                Upload & Analyze
              </button>

              <button
                type="button"
                onClick={() => {
                  setActiveTab('saved')
                  loadSavedFirs()
                }}
                className={`px-4 sm:px-5 py-2 text-xs font-bold rounded-full transition flex items-center gap-2 whitespace-nowrap ${
                  activeTab === 'saved'
                    ? 'bg-[#b98528] text-white shadow-sm'
                    : 'text-[#12335B] hover:bg-white/50'
                }`}
              >
                <span>Saved FIRs</span>
                {savedFirs.length > 0 && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-white text-[#12335B] rounded-full font-extrabold">
                    {savedFirs.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          {activeTab === 'saved' ? (
            /* Saved FIRs Management Tab */
            <div className="bg-white/80 backdrop-blur-md rounded-[20px] p-8 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70">
              <h2 className="font-serif text-2xl font-semibold text-[#12335B] mb-2">
                Your Saved FIRs & Legal Analyses
              </h2>
              <p className="text-sm text-[#56718f] mb-6">
                Access your explicitly saved FIR reports. Only you can view or delete these records.
              </p>

              {savedFirs.length === 0 ? (
                <div className="text-center py-12 border border-dashed border-gray-300 rounded-[16px]">
                  <p className="text-gray-500 text-sm">You have no saved FIRs yet.</p>
                  <button
                    onClick={() => setActiveTab('analyze')}
                    className="mt-4 px-5 py-2.5 bg-[#b98528] text-white text-xs font-bold rounded-full shadow-sm hover:bg-[#9f7020] transition"
                  >
                    Upload an FIR to Analyze
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {savedFirs.map((sf) => (
                    <div
                      key={sf.id}
                      className="bg-white/90 border border-gray-200 rounded-[16px] p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <span className="text-xl shrink-0">📄</span>
                            <h3 className="font-bold text-[#12335B] text-base truncate" title={sf.filename}>
                              {sf.filename}
                            </h3>
                          </div>
                          <button
                            type="button"
                            onClick={() => setDeleteModalId(sf.id)}
                            className="text-gray-400 hover:text-red-600 transition p-1 shrink-0"
                            title="Delete saved FIR"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>

                        <p className="text-xs text-gray-400 mb-3">
                          Saved on: {new Date(sf.created_at).toLocaleDateString()} at {new Date(sf.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>

                        <p className="text-xs text-gray-700 line-clamp-3 mb-4 leading-relaxed bg-[#f8f6f1]/80 p-3 rounded-lg border border-[#d2a14b]/30">
                          {sf.summary}
                        </p>

                        {sf.charges && sf.charges.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-4">
                            {sf.charges.map((c, idx) => (
                              <span
                                key={idx}
                                className="text-[11px] font-bold bg-[#12335B]/10 text-[#12335B] px-2.5 py-1 rounded-full border border-[#12335B]/20"
                              >
                                §{c.section} {c.title}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => viewSavedFIR(sf)}
                        className="w-full text-center px-4 py-2 bg-[#12335B] text-white text-xs font-semibold rounded-xl hover:bg-[#0c2340] transition"
                      >
                        View Full Legal Analysis →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Main Upload & Analysis Grid */
            <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 items-start">
              {/* Left Upload / Selected File Card */}
              <div
                {...getRootProps()}
                onClick={() => {
                  if (!selectedFile) {
                    requestRemoveOrReplace('select_new')
                  }
                }}
                className={`min-h-[320px] border border-white/70 rounded-[20px] p-6 flex flex-col items-center justify-center transition backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] relative ${
                  selectedFile
                    ? 'bg-white/90 border-[#b98528]'
                    : isDragActive
                    ? 'border-[#b98528] bg-white/80'
                    : 'bg-white/75 hover:bg-white/85 cursor-pointer'
                }`}
              >
                <input {...getInputProps()} />

                {!selectedFile ? (
                  /* Empty Dropzone State */
                  <div className="flex flex-col items-center text-center w-full">
                    <div className="w-16 h-16 rounded-[14px] border border-[#d2a14b]/50 bg-[#f8f6f1]/90 flex items-center justify-center mb-5 shadow-inner">
                      <svg
                        width="34"
                        height="34"
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

                    <p className="font-serif text-lg font-semibold text-[#12335B] mb-1">
                      {isDragActive
                        ? 'Drop FIR document here'
                        : 'Drag & drop FIR document here'}
                    </p>

                    <p className="text-xs text-[#56718f]">
                      or select an option below
                    </p>

                    {/* Dual Action Buttons: [ Upload Document ] [ Take Photo ] */}
                    <div className="mt-5 flex items-center gap-2.5 w-full max-w-[290px]">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          requestRemoveOrReplace('select_new')
                        }}
                        className="flex-1 py-2.5 px-3 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center justify-center gap-1.5"
                      >
                        <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        <span>Upload File</span>
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          requestRemoveOrReplace('camera')
                        }}
                        className="flex-1 py-2.5 px-3 bg-[#12335B] hover:bg-[#0c2340] text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center justify-center gap-1.5"
                      >
                        <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                          <circle cx="12" cy="13" r="3" strokeWidth="2" />
                        </svg>
                        <span>Take Photo</span>
                      </button>
                    </div>

                    <div className="mt-5 h-px w-12 bg-[#b98528]/40" />

                    <p className="text-[11px] text-[#7890a8] mt-3">
                      Supports: PDF, TXT, JPG, PNG, WEBP, BMP (up to 10MB)
                    </p>
                  </div>
                ) : (
                  /* Selected File Card */
                  <div className="w-full flex flex-col items-center text-center">
                    {/* X Remove Button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        requestRemoveOrReplace('remove')
                      }}
                      className="absolute top-3.5 right-3.5 w-8 h-8 rounded-full bg-red-100 hover:bg-red-200 text-red-700 flex items-center justify-center transition shadow-sm font-bold text-sm"
                      title="Remove file"
                    >
                      ✕
                    </button>

                    {/* Preview Icon or Thumbnail */}
                    {previewUrl ? (
                      <div className="w-24 h-24 rounded-xl border-2 border-[#b98528] overflow-hidden mb-3 shadow-md bg-black/5">
                        <img
                          src={previewUrl}
                          alt="FIR document thumbnail"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="w-16 h-16 rounded-[14px] border border-[#d2a14b]/60 bg-[#f8f6f1] flex items-center justify-center mb-3 shadow-sm">
                        <span className="text-2xl">📄</span>
                      </div>
                    )}

                    {/* File Metadata */}
                    <h3
                      className="font-bold text-[#12335B] text-sm max-w-[260px] truncate mb-1"
                      title={selectedFile.name}
                    >
                      {selectedFile.name}
                    </h3>

                    <div className="flex items-center justify-center gap-2 text-xs text-gray-500 mb-5">
                      <span className="uppercase font-semibold px-2 py-0.5 bg-gray-100 rounded text-gray-700">
                        {selectedFile.name.split('.').pop() || 'file'}
                      </span>
                      <span>•</span>
                      <span>{formatFileSize(selectedFile.size)}</span>
                    </div>

                    {/* Re-analyze / Action Buttons */}
                    <div className="flex flex-col gap-2 w-full max-w-[260px]">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          runAnalysis(selectedFile)
                        }}
                        disabled={loading}
                        className="w-full py-2.5 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-full shadow-md transition hover:-translate-y-0.5 disabled:opacity-50"
                      >
                        {loading ? 'Analyzing...' : 'Re-analyze Document'}
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          requestRemoveOrReplace('select_new')
                        }}
                        className="w-full py-2 bg-transparent text-gray-600 hover:text-[#12335B] text-xs font-semibold rounded-full transition"
                      >
                        Replace Document
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Analysis Workspace Panel */}
              <div className="min-w-0">
                {/* Loading State */}
                {loading && (
                  <div className="bg-white/80 backdrop-blur-md rounded-[20px] p-8 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 text-center space-y-5">
                    <div className="w-12 h-12 border-4 border-[#b98528] border-t-transparent rounded-full animate-spin mx-auto" />
                    <div>
                      <h3 className="font-serif text-xl font-semibold text-[#12335B] mb-1.5">
                        Analyzing FIR & Legal Grounding
                      </h3>
                      <p className="text-xs sm:text-sm text-[#56718f] animate-pulse">{loadingProgress}</p>
                    </div>
                  </div>
                )}

                {/* Error Notice */}
                {error && (
                  <div className="bg-red-50/95 border border-red-200 text-red-800 p-6 rounded-[20px] shadow-sm space-y-2">
                    <div className="flex items-center gap-2 font-bold text-red-900 text-base">
                      <span>⚠️</span> Analysis Notice
                    </div>
                    <p className="text-sm leading-relaxed">{error}</p>
                  </div>
                )}

                {/* Initial Empty Workspace State */}
                {!loading && !result && !error && (
                  <div className="min-h-[320px] bg-white/75 backdrop-blur-md rounded-[20px] p-8 border border-white/70 text-center flex flex-col items-center justify-center shadow-[0_15px_40px_rgba(18,51,91,0.10)]">
                    <div className="w-14 h-14 rounded-full bg-[#f8f6f1] border border-[#d2a14b]/40 flex items-center justify-center mb-4">
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
                      No document analyzed yet. Upload an FIR document or take a photo on the left to view the plain-language summary and grounded legal breakdown.
                    </p>
                  </div>
                )}

                {/* Successful Analysis Results */}
                {result && (
                  <div className="bg-white/85 backdrop-blur-md rounded-[20px] p-6 sm:p-8 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 space-y-6">
                    {/* Header Badge & Metadata */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-[#12335B]/10">
                      <div className="flex items-center gap-2">
                        <span className="bg-green-100 text-green-800 text-xs font-bold px-3 py-1.5 rounded-full border border-green-200">
                          ✓ Document Processed ({result.filename})
                        </span>
                        {result.is_degraded_fallback && (
                          <span className="bg-amber-100 text-amber-900 text-xs font-bold px-3 py-1.5 rounded-full border border-amber-300">
                            ⚠️ Degraded Fallback Mode
                          </span>
                        )}
                      </div>

                      {result.file_id && (
                        <span className="text-xs text-gray-400 font-mono truncate max-w-[200px]">
                          Doc Ref: {result.file_id}
                        </span>
                      )}
                    </div>

                    {/* Grounding & Legal Distinctions Notice */}
                    <div className="bg-blue-50/70 border border-blue-200 rounded-[14px] p-4 text-xs text-blue-900 leading-relaxed space-y-1">
                      <p className="font-bold flex items-center gap-1.5 text-blue-950">
                        ⚖ Legal Grounding & Standard Distinctions
                      </p>
                      <p>
                        This analysis distinguishes between <strong>allegations stated in the FIR</strong> and proven offences. Statements in an FIR represent claims filed with law enforcement and require judicial trial for determination. Statutory classifications (bailable/non-bailable, punishments) are retrieved directly from the BNS legal corpus.
                      </p>
                    </div>

                    {/* 1. Plain Language Summary & Structured Facts */}
                    <div className="bg-[#eef4fa]/90 border border-[#d8e4ef] rounded-[16px] p-5 shadow-sm space-y-4">
                      <h3 className="font-serif font-bold text-[#12335B] text-base mb-2">
                        Plain-Language Summary & Facts Stated
                      </h3>
                      <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-line">
                        {result.plain_summary || result.summary}
                      </p>

                      {/* Structured Metadata Pills / Fields */}
                      {result.fir_metadata && Object.keys(result.fir_metadata).length > 0 && (
                        <div className="pt-3 border-t border-[#12335B]/10 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {Object.entries(result.fir_metadata).map(([key, val]) => (
                            <div key={key} className="bg-white/80 p-2.5 rounded-lg border border-[#12335B]/10 flex flex-col">
                              <span className="text-[10px] uppercase font-bold text-[#56718f]">
                                {key.replace(/_/g, ' ')}
                              </span>
                              <span className="font-medium text-[#12335B] mt-0.5">
                                {val}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* 2. What the FIR Alleges */}
                    {result.what_fir_alleges && (
                      <div className="bg-amber-50/60 border border-amber-200/80 rounded-[16px] p-5 space-y-2">
                        <h3 className="font-serif font-bold text-amber-950 text-base">
                          What the FIR Alleges
                        </h3>
                        <p className="text-xs text-amber-900 leading-relaxed">
                          {result.what_fir_alleges}
                        </p>
                      </div>
                    )}

                    {/* 3. Section Analysis: Sections Stated in FIR vs Potentially Relevant Provisions */}
                    {result.has_sections_in_fir === false && (
                      <div className="bg-amber-50/80 border border-amber-200 rounded-[16px] p-4 text-xs text-amber-950 font-medium">
                        ℹ️ <strong>No offence section number was explicitly stated in the uploaded FIR document.</strong> The statutory provisions below represent potentially relevant provisions derived from the stated facts.
                      </div>
                    )}

                    {((result.charges && result.charges.length > 0) || (result.explained_sections && result.explained_sections.length > 0)) && (
                      <div>
                        <h3 className="font-serif font-bold text-[#12335B] text-lg mb-4 flex items-center justify-between">
                          <span>
                            {result.has_sections_in_fir !== false
                              ? "Offence Sections Stated in This FIR & Statutory Analysis"
                              : "Potentially Relevant BNS Provisions Based on Stated Facts"}
                          </span>
                        </h3>

                        <div className="space-y-5">
                          {(result.explained_sections && result.explained_sections.length > 0
                            ? result.explained_sections
                            : result.charges
                          ).map((c, idx) => (
                            <div
                              key={idx}
                              className="border border-[#12335B]/20 rounded-[18px] p-5 bg-white/95 shadow-sm space-y-3"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-gray-100 pb-3">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-[#12335B] text-base">
                                    Section {c.section} — {c.title}
                                  </span>
                                  {result.has_sections_in_fir !== false && (
                                    <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-100 text-blue-900 rounded-full border border-blue-200">
                                      Stated in FIR
                                    </span>
                                  )}
                                  {result.has_sections_in_fir === false && (
                                    <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-100 text-amber-900 rounded-full border border-amber-200">
                                      Potentially Relevant
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-2">
                                  {c.bailable && (
                                    <span
                                      className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${
                                        c.bailable.toLowerCase().includes('non')
                                          ? 'bg-red-50 text-red-700 border-red-200'
                                          : 'bg-green-50 text-green-700 border-green-200'
                                      }`}
                                    >
                                      {c.bailable}
                                    </span>
                                  )}

                                  {c.cognizable && (
                                    <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                                      {c.cognizable}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Structured Legal Elements Grid */}
                              <div className="space-y-2.5 text-xs">
                                {c.law_requires && (
                                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                                    <strong className="text-slate-900 block mb-1">📋 What the law requires:</strong>
                                    <p className="text-slate-700 leading-relaxed">
                                      {Array.isArray(c.law_requires) ? c.law_requires.join(' • ') : c.law_requires}
                                    </p>
                                  </div>
                                )}

                                {c.fir_states && (
                                  <div className="bg-blue-50/60 p-3 rounded-xl border border-blue-200/60">
                                    <strong className="text-blue-950 block mb-1">📄 What the FIR states:</strong>
                                    <p className="text-blue-900 leading-relaxed">
                                      {Array.isArray(c.fir_states) ? c.fir_states.join(' • ') : c.fir_states}
                                    </p>
                                  </div>
                                )}

                                {(c.why_may_apply || c.reasoning) && (
                                  <div className="bg-amber-50/50 p-3 rounded-xl border border-amber-200/60">
                                    <strong className="text-amber-950 block mb-1">⚖ Why this section may apply:</strong>
                                    <p className="text-amber-900 leading-relaxed">
                                      {Array.isArray(c.why_may_apply) ? c.why_may_apply.join(' • ') : (c.why_may_apply || c.reasoning)}
                                    </p>
                                  </div>
                                )}

                                {c.punishment && (
                                  <div className="bg-gray-50 p-3 rounded-xl border border-gray-200">
                                    <strong className="text-gray-900 block mb-1">⚖ Statutory punishment:</strong>
                                    <p className="text-gray-800 leading-relaxed">
                                      {Array.isArray(c.punishment) ? c.punishment.join(' • ') : c.punishment}
                                    </p>
                                  </div>
                                )}

                                {c.what_remains_uncertain && (
                                  <div className="bg-purple-50/50 p-3 rounded-xl border border-purple-200/60">
                                    <strong className="text-purple-950 block mb-1">❓ What remains uncertain:</strong>
                                    <p className="text-purple-900 leading-relaxed">
                                      {Array.isArray(c.what_remains_uncertain) ? c.what_remains_uncertain.join(' • ') : c.what_remains_uncertain}
                                    </p>
                                  </div>
                                )}

                                {c.assessment && (
                                  <div className="bg-[#12335B]/5 p-3 rounded-xl border border-[#12335B]/15">
                                    <strong className="text-[#12335B] block mb-1">📌 Statutory Assessment:</strong>
                                    <p className="text-[#12335B] font-medium leading-relaxed">{c.assessment}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 4. What the FIR Does Not Establish */}
                    {result.unestablished_facts && result.unestablished_facts.length > 0 && (
                      <div className="bg-purple-50/80 border border-purple-200 rounded-[16px] p-5">
                        <h3 className="font-serif font-bold text-purple-950 text-base mb-3 flex items-center gap-2">
                          <span>🔍</span> What the FIR Does Not Establish
                        </h3>
                        <ul className="list-disc list-inside space-y-1.5 text-xs text-purple-900 leading-relaxed">
                          {result.unestablished_facts.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 5. What Details Would Help Clarify This */}
                    {result.clarifying_details && result.clarifying_details.length > 0 && (
                      <div className="bg-sky-50/80 border border-sky-200 rounded-[16px] p-5">
                        <h3 className="font-serif font-bold text-sky-950 text-base mb-3 flex items-center gap-2">
                          <span>❓</span> What Details Would Help Clarify This
                        </h3>
                        <ul className="list-disc list-inside space-y-1.5 text-xs text-sky-900 leading-relaxed">
                          {result.clarifying_details.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 6. Reference Provisions */}
                    {result.reference_provisions && result.reference_provisions.length > 0 && (
                      <details className="bg-slate-50/90 border border-slate-300 rounded-[16px] p-5 space-y-3 group">
                        <summary className="font-serif font-bold text-[#12335B] text-base cursor-pointer select-none flex items-center justify-between">
                          <span>
                            {result.is_degraded_fallback
                              ? "Retrieved source candidates — not assessed for applicability"
                              : "Retrieved BNS Reference Candidates"}
                            <span className="ml-2 text-xs font-normal text-slate-500">
                              ({result.reference_provisions.length} provisions retrieved)
                            </span>
                          </span>
                          <span className="text-xs text-blue-900 group-open:rotate-180 transition-transform">
                            ▼ Click to expand
                          </span>
                        </summary>

                        <p className="text-xs text-slate-600 leading-relaxed mt-2 pt-2 border-t border-slate-200">
                          {result.is_degraded_fallback
                            ? "Automated legal applicability reasoning was unavailable for this document. The statutory provisions below are raw retrieved reference candidates from the BNS legal corpus and have NOT been assessed for legal applicability."
                            : "These statutory provisions were retrieved from the BNS legal corpus as reference material."}
                        </p>

                        <div className="space-y-3 mt-3">
                          {result.reference_provisions.map((c, idx) => (
                            <div
                              key={idx}
                              className="border border-[#12335B]/10 rounded-[14px] p-4 bg-white/90 shadow-sm"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-1">
                                <span className="font-bold text-[#12335B] text-sm">
                                  Section {c.section} — {c.title}
                                </span>
                                {c.bailable && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                                    {c.bailable}
                                  </span>
                                )}
                              </div>
                              {c.punishment && (
                                <p className="text-xs text-gray-600">
                                  <strong>Punishment:</strong> {c.punishment}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}

                    {/* 7. Citizen Legal Rights */}
                    {result.rights && result.rights.length > 0 && (
                      <div className="bg-amber-50/80 border border-amber-200 rounded-[16px] p-5">
                        <h3 className="font-serif font-bold text-amber-900 text-base mb-3 flex items-center gap-2">
                          <span>⚖</span> Your Immediate Legal Rights
                        </h3>
                        <ul className="list-disc list-inside space-y-2 text-xs text-amber-950 leading-relaxed">
                          {result.rights.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 8. Recommended Next Steps */}
                    {result.next_steps && result.next_steps.length > 0 && (
                      <div className="bg-green-50/80 border border-green-200 rounded-[16px] p-5">
                        <h3 className="font-serif font-bold text-green-900 text-base mb-3 flex items-center gap-2">
                          <span>🛡</span> Recommended Next Steps
                        </h3>
                        <ul className="list-disc list-inside space-y-2 text-xs text-green-950 leading-relaxed">
                          {result.next_steps.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 9. Bottom Line */}
                    {result.bottom_line && (
                      <div className="bg-[#12335B] text-white border border-[#b98528]/50 rounded-[16px] p-6 shadow-md space-y-2">
                        <h3 className="font-serif font-bold text-[#dca45a] text-base flex items-center gap-2">
                          <span>📌</span> Bottom Line
                        </h3>
                        <p className="text-xs sm:text-sm text-gray-100 leading-relaxed">
                          {result.bottom_line}
                        </p>
                      </div>
                    )}

                    {/* Consent Persistence Prompt */}
                    {!consentDismissed && saveStatus !== 'saved' && (
                      <div className="bg-[#f8f6f1] border-2 border-[#b98528]/40 rounded-[18px] p-6 shadow-md space-y-4">
                        <div>
                          <h4 className="font-serif font-bold text-[#12335B] text-base">
                            Save this FIR & Analysis to My FIRs?
                          </h4>
                          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                            LawAid respects your privacy. We do not automatically store uploaded FIRs or legal analyses without explicit consent. Would you like to save this FIR to your account so you can view it later?
                          </p>
                        </div>

                        {saveError && (
                          <div className="text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200 font-medium">
                            {saveError}
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-3">
                          <button
                            type="button"
                            onClick={handleSaveFIR}
                            disabled={saveStatus === 'saving'}
                            className="px-6 py-2.5 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-full shadow-sm transition hover:-translate-y-0.5 disabled:opacity-50"
                          >
                            {saveStatus === 'saving' ? 'Saving...' : 'Save to My FIRs'}
                          </button>

                          <button
                            type="button"
                            onClick={() => setConsentDismissed(true)}
                            className="px-6 py-2.5 bg-white border border-gray-300 text-gray-700 hover:bg-gray-100 text-xs font-bold rounded-full transition"
                          >
                            Don't Save
                          </button>
                        </div>
                      </div>
                    )}

                    {saveStatus === 'saved' && (
                      <div className="bg-green-50 border border-green-200 text-green-800 p-4 rounded-[14px] text-xs font-bold flex items-center justify-between shadow-sm">
                        <span>✓ FIR Analysis successfully saved to My FIRs. You can access it anytime from the Saved FIRs tab.</span>
                        <button
                          onClick={() => setActiveTab('saved')}
                          className="underline text-green-900 font-extrabold hover:text-green-950"
                        >
                          View Saved FIRs →
                        </button>
                      </div>
                    )}

                    {/* Statutory Disclaimer */}
                    {result.disclaimer && (
                      <p className="text-[11px] text-gray-400 border-t border-gray-200 pt-4 leading-relaxed italic">
                        {result.disclaimer}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Save & Replace Confirmation Modal */}
        {showReplaceModal && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-[20px] p-6 max-w-md w-full shadow-2xl border border-gray-200 space-y-4">
              <h3 className="font-serif text-xl font-semibold text-[#12335B]">
                Save this FIR before replacing it?
              </h3>

              <p className="text-xs text-gray-600 leading-relaxed">
                You have an unsaved FIR legal breakdown. If you replace or remove this document without saving, your current analysis will be discarded.
              </p>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 pt-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowReplaceModal(false)
                    setPendingAction(null)
                  }}
                  disabled={isSavingAndReplacing}
                  className="px-4 py-2 text-xs font-bold text-gray-600 hover:text-gray-800 rounded-full border border-gray-300 hover:bg-gray-100 transition text-center"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleConfirmDontSaveAndReplace}
                  disabled={isSavingAndReplacing}
                  className="px-4 py-2 text-xs font-bold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-full transition text-center"
                >
                  Don't Save & Replace
                </button>

                <button
                  type="button"
                  onClick={handleConfirmSaveAndReplace}
                  disabled={isSavingAndReplacing}
                  className="px-5 py-2 text-xs font-bold text-white bg-[#b98528] hover:bg-[#9f7020] rounded-full shadow-sm transition disabled:opacity-50 text-center"
                >
                  {isSavingAndReplacing ? 'Saving...' : 'Save & Replace'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal for Saved FIRs */}
        {deleteModalId !== null && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-[20px] p-6 max-w-md w-full shadow-2xl border border-gray-200 space-y-4">
              <h3 className="font-serif text-xl font-semibold text-[#12335B]">
                Delete Saved FIR?
              </h3>

              <p className="text-xs text-gray-600 leading-relaxed">
                Delete this saved FIR and its analysis from LawAid active application storage? The database record, analysis summary, and associated document file will be permanently removed from your account.
              </p>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDeleteModalId(null)}
                  disabled={isDeleting}
                  className="px-5 py-2 text-xs font-bold text-gray-600 hover:text-gray-800 rounded-full border border-gray-300 hover:bg-gray-100 transition"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleDeleteSavedFIR}
                  disabled={isDeleting}
                  className="px-5 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-full shadow-sm transition disabled:opacity-50"
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Responsive Cross-Device Camera Modal */}
        {showCameraModal && (
          <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex flex-col items-center justify-center p-4 sm:p-6">
            <div className="bg-[#12335B] rounded-[24px] border border-white/20 p-5 max-w-2xl w-full shadow-2xl flex flex-col items-center relative overflow-hidden space-y-4">
              {/* Header bar */}
              <div className="w-full flex items-center justify-between text-white border-b border-white/10 pb-3">
                <div className="flex items-center gap-2 font-serif text-lg font-semibold text-[#dca45a]">
                  <span>📷</span>
                  <span>Take FIR Photo</span>
                </div>
                <button
                  type="button"
                  onClick={stopCamera}
                  className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white font-bold flex items-center justify-center transition"
                  title="Close camera"
                >
                  ✕
                </button>
              </div>

              {/* Live Preview Container */}
              <div className="relative w-full aspect-[4/3] max-h-[55vh] bg-black rounded-2xl overflow-hidden flex items-center justify-center border border-white/10 shadow-inner">
                {isCameraStarting && (
                  <div className="flex flex-col items-center gap-3 text-white/80">
                    <div className="w-10 h-10 border-4 border-[#b98528] border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs font-medium">Starting camera...</span>
                  </div>
                )}

                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={`w-full h-full object-cover ${cameraStream && !cameraError ? 'block' : 'hidden'}`}
                />

                {/* Framing Overlay Guide */}
                {cameraStream && !cameraError && (
                  <div className="absolute inset-4 sm:inset-8 border-2 border-dashed border-white/40 rounded-xl pointer-events-none flex items-start justify-center p-3">
                    <span className="text-[11px] font-medium text-white/80 bg-black/50 px-3 py-1 rounded-full backdrop-blur-sm">
                      Align FIR Document Within Frame
                    </span>
                  </div>
                )}

                {/* Camera Error Message & Fallbacks */}
                {cameraError && (
                  <div className="p-6 text-center text-white max-w-md space-y-3">
                    <div className="text-3xl">⚠️</div>
                    <p className="text-xs sm:text-sm font-medium leading-relaxed text-red-200">
                      {cameraError}
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => {
                          stopCamera()
                          fileInputRef.current?.click()
                        }}
                        className="px-4 py-2 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-full shadow-sm transition"
                      >
                        Upload Image Instead
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          stopCamera()
                          cameraInputRef.current?.click()
                        }}
                        className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white text-xs font-semibold rounded-full transition"
                      >
                        Try Mobile Native Camera
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Controls */}
              {cameraStream && !cameraError && (
                <div className="w-full flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={stopCamera}
                    className="px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-full transition"
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    onClick={capturePhoto}
                    className="px-7 py-3 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs sm:text-sm font-bold rounded-full shadow-lg transition transform hover:scale-105 flex items-center gap-2"
                  >
                    <span className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
                    <span>Capture Photo</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      stopCamera()
                      cameraInputRef.current?.click()
                    }}
                    className="text-[11px] text-white/60 hover:text-white underline transition"
                    title="Use system camera picker"
                  >
                    Mobile File Fallback
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}