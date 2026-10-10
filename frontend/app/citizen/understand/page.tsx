'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import { firAPI } from '@/lib/api'
import { getStoredUser } from '@/lib/auth'

type ChargeItem = {
  section: string
  title: string
  punishment?: string | string[]
  bailable?: string
  cognizable?: string
  reasoning?: string
  applicability?: string
  law_requires?: string | string[]
  fir_states?: string | string[]
  why_may_apply?: string | string[]
  what_remains_uncertain?: string | string[]
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

// Helper to format array or string fields safely into readable text
function renderFieldContent(content?: string | string[]) {
  if (!content) return null
  if (Array.isArray(content)) {
    return content.length === 1 ? content[0] : content.join(' • ')
  }
  return content
}

// Helper to safely fetch metadata fields from fir_metadata dictionary
function getMetadataVal(metadata: Record<string, string> | undefined, keys: string[]): string | null {
  if (!metadata) return null
  for (const k of keys) {
    const target = k.toLowerCase().replace(/_/g, ' ')
    for (const [mk, mv] of Object.entries(metadata)) {
      const current = mk.toLowerCase().replace(/_/g, ' ')
      if (current === target || current.includes(target)) {
        if (
          mv &&
          typeof mv === 'string' &&
          mv.trim() &&
          !['n/a', 'not provided', 'unknown', 'none'].includes(mv.trim().toLowerCase())
        ) {
          return mv.trim()
        }
      }
    }
  }
  return null
}

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

  // Progressive Disclosure / Accordion States for Dashboard
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [expandedPotentialSections, setExpandedPotentialSections] = useState<Record<string, boolean>>({})
  const [showFullNarrative, setShowFullNarrative] = useState(false)
  const [expandedFactsDrawers, setExpandedFactsDrawers] = useState<Record<string, boolean>>({
    people: false,
    dates: false,
    allegations: false,
  })

  const toggleSectionExpand = (secKey: string) => {
    setExpandedSections((prev) => ({ ...prev, [secKey]: !prev[secKey] }))
  }

  const togglePotentialExpand = (secKey: string) => {
    setExpandedPotentialSections((prev) => ({ ...prev, [secKey]: !prev[secKey] }))
  }

  const toggleFactsDrawer = (drawerKey: string) => {
    setExpandedFactsDrawers((prev) => ({ ...prev, [drawerKey]: !prev[drawerKey] }))
  }

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
    setExpandedSections({})
    setExpandedPotentialSections({})
    setShowFullNarrative(false)

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
    noClick: true,
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
    setExpandedSections({})
    setExpandedPotentialSections({})
    setShowFullNarrative(false)

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
        stopCamera()
        handleFileSelect(file)
        await runAnalysis(file)
      },
      'image/jpeg',
      0.92
    )
  }

  const requestRemoveOrReplace = (action: 'select_new' | 'camera' | 'remove') => {
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

  // Data helpers for structured result views
  const getExplicitSectionChips = (res: UnderstandResponse): string[] => {
    if (res.sections_recorded_in_fir && res.sections_recorded_in_fir.length > 0) {
      return res.sections_recorded_in_fir
    }
    if (res.has_sections_in_fir !== false) {
      const list =
        res.explained_sections && res.explained_sections.length > 0
          ? res.explained_sections
          : res.charges
      if (list && list.length > 0) {
        return Array.from(new Set(list.map((c) => c.section)))
      }
    }
    return []
  }

  const getCleanSummary = (res: UnderstandResponse): string => {
    const candidate = res.plain_summary || res.summary || ''
    if (!candidate) return res.what_fir_alleges || 'Summary unavailable.'
    const noisePattern = /^(NATIONAL INVESTIGATION|BHARATIYA NYAYA|IN THE COURT|POLICE STATION|STATE OF|UNION OF INDIA)/i
    if (noisePattern.test(candidate.trim()) && res.what_fir_alleges) {
      return res.what_fir_alleges
    }
    return candidate
  }

  const getExplicitSections = (res: UnderstandResponse): ChargeItem[] => {
    if (res.has_sections_in_fir === false) return []
    if (res.explained_sections && res.explained_sections.length > 0) return res.explained_sections
    if (res.charges && res.charges.length > 0) return res.charges
    return []
  }

  const getPotentialSections = (res: UnderstandResponse): ChargeItem[] => {
    if (res.potential_sections && res.potential_sections.length > 0) {
      return res.potential_sections
    }
    if (res.has_sections_in_fir === false && res.charges && res.charges.length > 0) {
      return res.charges
    }
    return []
  }

  // Metadata items for Top Overview
  const firNo = result ? getMetadataVal(result.fir_metadata, ['fir_number', 'fir_no', 'fir_num', 'fir', 'number']) : null
  const firDate = result ? getMetadataVal(result.fir_metadata, ['fir_date', 'date_of_fir', 'date', 'date_reported']) : null
  const policeStation = result ? getMetadataVal(result.fir_metadata, ['police_station', 'ps', 'station']) : null
  const district = result ? getMetadataVal(result.fir_metadata, ['district', 'dist']) : null
  const year = result ? getMetadataVal(result.fir_metadata, ['year']) || (firDate ? firDate.match(/\b(20\d\d|19\d\d)\b/)?.[0] || null : null) : null

  // Fact drawer item values
  const complainant = result ? getMetadataVal(result.fir_metadata, ['complainant', 'informant']) : null
  const accused = result ? getMetadataVal(result.fir_metadata, ['accused', 'suspect']) : null
  const victim = result ? getMetadataVal(result.fir_metadata, ['victim']) : null
  const occurrenceDate = result ? getMetadataVal(result.fir_metadata, ['date_of_occurrence', 'occurrence_date', 'incident_date']) : null
  const occurrencePlace = result ? getMetadataVal(result.fir_metadata, ['place_of_occurrence', 'place', 'location']) : null

  const hasPeopleData = Boolean(complainant || accused || victim)
  const hasDatesData = Boolean(firDate || occurrenceDate || policeStation || district || year)
  const hasAllegationsData = Boolean(
    result?.what_fir_alleges ||
      occurrencePlace ||
      (result?.unestablished_facts && result.unestablished_facts.length > 0) ||
      (result?.clarifying_details && result.clarifying_details.length > 0)
  )

  return (
    <div className="min-h-screen text-[#12335B] bg-[#faf8f5]">
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

      {/* Main Container */}
      <main className="relative min-h-[calc(100vh-64px)] overflow-hidden">
        {/* Subdued LawAid Theme Background */}
        <div className="fixed inset-0 -z-10 bg-[#faf8f5]">
          <img
            src="/images/lawaid-feature-bg.png"
            alt="LawAid legal background"
            className="h-full w-full object-cover object-center opacity-30"
          />
        </div>
        <div className="fixed inset-0 -z-10 bg-gradient-to-b from-[#faf8f5]/90 via-[#f7f4ed]/95 to-[#faf8f5]" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Top Navigation Bar with Title & Segmented Tab Controls */}
          <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[#12335B]/10 pb-4">
            <div>
              <div className="flex items-center gap-2.5 mb-1">
                <span className="h-px w-6 bg-[#b98528]" />
                <span className="text-[10px] tracking-[0.25em] uppercase text-[#b98528] font-bold">
                  CITIZEN FIR DASHBOARD
                </span>
              </div>
              <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[#12335B] tracking-tight">
                Understand Your FIR
              </h1>
            </div>

            {/* Segmented Tab Control */}
            <div className="flex items-center gap-1.5 bg-[#f0ebd9]/80 p-1 rounded-full border border-[#d2a14b]/30 shrink-0 self-start">
              <button
                type="button"
                onClick={() => setActiveTab('analyze')}
                className={`px-4 py-1.5 text-xs font-bold rounded-full transition whitespace-nowrap ${
                  activeTab === 'analyze'
                    ? 'bg-[#12335B] text-white shadow-sm'
                    : 'text-[#12335B] hover:bg-white/60'
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
                className={`px-4 py-1.5 text-xs font-bold rounded-full transition flex items-center gap-2 whitespace-nowrap ${
                  activeTab === 'saved'
                    ? 'bg-[#12335B] text-white shadow-sm'
                    : 'text-[#12335B] hover:bg-white/60'
                }`}
              >
                <span>Saved FIRs</span>
                {savedFirs.length > 0 && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-[#b98528] text-white rounded-full font-extrabold">
                    {savedFirs.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          {activeTab === 'saved' ? (
            /* Saved FIRs Management Tab */
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-[#12335B]/10">
              <h2 className="font-serif text-xl font-semibold text-[#12335B] mb-1">
                Your Saved FIRs & Legal Analyses
              </h2>
              <p className="text-xs text-[#56718f] mb-6">
                Access your explicitly saved FIR reports. Only you can view or delete these records.
              </p>

              {savedFirs.length === 0 ? (
                <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl">
                  <p className="text-gray-500 text-xs">You have no saved FIRs yet.</p>
                  <button
                    onClick={() => setActiveTab('analyze')}
                    className="mt-4 px-4 py-2 bg-[#12335B] text-white text-xs font-bold rounded-full shadow-sm hover:bg-[#0c2340] transition"
                  >
                    Upload an FIR to Analyze
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {savedFirs.map((sf) => (
                    <div
                      key={sf.id}
                      className="bg-[#fcfbf8] border border-gray-200 rounded-xl p-4 shadow-sm flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-lg shrink-0">📄</span>
                            <h3 className="font-bold text-[#12335B] text-sm truncate" title={sf.filename}>
                              {sf.filename}
                            </h3>
                          </div>
                          <button
                            type="button"
                            onClick={() => setDeleteModalId(sf.id)}
                            className="text-gray-400 hover:text-red-600 transition p-1 shrink-0"
                            title="Delete saved FIR"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>

                        <p className="text-[11px] text-gray-400 mb-2">
                          Saved: {new Date(sf.created_at).toLocaleDateString()}
                        </p>

                        <p className="text-xs text-gray-700 line-clamp-3 mb-3 leading-relaxed bg-white p-2.5 rounded border border-gray-200">
                          {sf.summary}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => viewSavedFIR(sf)}
                        className="w-full text-center px-4 py-2 bg-[#12335B] text-white text-xs font-semibold rounded-lg hover:bg-[#0c2340] transition"
                      >
                        View Legal Analysis →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Main Upload & Dashboard Layout */
            <div className="space-y-6">
              {/* Top Compact Upload Bar / Document Selector */}
              {!result && !loading && (
                <div
                  {...getRootProps()}
                  onClick={() => requestRemoveOrReplace('select_new')}
                  className={`border border-dashed border-[#d2a14b]/60 rounded-2xl p-6 text-center transition bg-white shadow-sm ${
                    isDragActive ? 'border-[#b98528] bg-[#fdfbf7]' : 'hover:bg-[#fcfbf8] cursor-pointer'
                  }`}
                >
                  <input {...getInputProps()} />
                  <div className="max-w-md mx-auto space-y-3">
                    <div className="w-12 h-12 rounded-full bg-[#f7f4ed] border border-[#d2a14b]/40 flex items-center justify-center mx-auto text-[#b98528]">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <polyline points="10 9 9 9 8 9" />
                      </svg>
                    </div>

                    <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                      {isDragActive ? 'Drop your FIR document here' : 'Upload or Capture an FIR Document'}
                    </h2>

                    <p className="text-xs text-[#56718f]">
                      LawAid extracts statements, maps recorded sections under Bharatiya Nyaya Sanhita (BNS 2023), and provides a clean plain-language breakdown.
                    </p>

                    <div className="pt-2 flex items-center justify-center gap-3">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          requestRemoveOrReplace('select_new')
                        }}
                        className="px-4 py-2 bg-[#12335B] hover:bg-[#0c2340] text-white text-xs font-bold rounded-lg shadow-sm transition flex items-center gap-1.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        <span>Choose Document</span>
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          requestRemoveOrReplace('camera')
                        }}
                        className="px-4 py-2 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-lg shadow-sm transition flex items-center gap-1.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                          <circle cx="12" cy="13" r="3" strokeWidth="2" />
                        </svg>
                        <span>Take Photo</span>
                      </button>
                    </div>

                    <p className="text-[11px] text-[#7890a8] pt-1">
                      Supports: PDF, TXT, JPG, PNG, WEBP, BMP (up to 10MB)
                    </p>
                  </div>
                </div>
              )}

              {/* Active Document Strip when result exists */}
              {result && (
                <div className="bg-white rounded-xl border border-gray-200 p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-sm">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-8 h-8 rounded-lg bg-[#f7f4ed] text-[#b98528] flex items-center justify-center text-sm shrink-0 font-bold">
                      📄
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-[#12335B] truncate" title={result.filename}>
                        {result.filename}
                      </p>
                      <p className="text-[11px] text-gray-500">
                        {selectedFile ? formatFileSize(selectedFile.size) : 'FIR Document'}
                        {result.is_degraded_fallback && (
                          <span className="ml-2 text-amber-700 font-semibold">• Fallback Mode</span>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                    {selectedFile && (
                      <button
                        type="button"
                        onClick={() => runAnalysis(selectedFile)}
                        disabled={loading}
                        className="px-3 py-1.5 text-xs font-semibold text-[#12335B] bg-[#f0ebd9] hover:bg-[#e4ddc4] rounded-lg transition"
                      >
                        Re-analyze
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => requestRemoveOrReplace('select_new')}
                      className="px-3 py-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                    >
                      New Document
                    </button>
                  </div>
                </div>
              )}

              {/* Loading State */}
              {loading && (
                <div className="bg-white rounded-2xl p-8 text-center border border-gray-200 shadow-sm space-y-4">
                  <div className="w-10 h-10 border-3 border-[#b98528] border-t-transparent rounded-full animate-spin mx-auto" />
                  <div>
                    <h3 className="font-serif text-lg font-semibold text-[#12335B] mb-1">
                      Analyzing FIR Document
                    </h3>
                    <p className="text-xs text-[#56718f] animate-pulse">{loadingProgress}</p>
                  </div>
                </div>
              )}

              {/* Error Notice */}
              {error && (
                <div className="bg-red-50/90 border border-red-200 text-red-900 p-5 rounded-2xl shadow-sm space-y-1">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <span>⚠️</span> Notice
                  </div>
                  <p className="text-xs leading-relaxed">{error}</p>
                </div>
              )}

              {/* ========================================================================= */}
              {/* LEGAL INFORMATION DASHBOARD RESULT (PRESENTATION REDESIGN) */}
              {/* ========================================================================= */}
              {result && (
                <div className="space-y-6">

                  {/* -------------------------------------------------- */}
                  {/* 1. TOP: FIR OVERVIEW */}
                  {/* -------------------------------------------------- */}
                  <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 pb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#b98528]">
                        FIR Overview & Metadata
                      </span>
                      {result.file_id && (
                        <span className="text-[11px] text-gray-400 font-mono">
                          Ref: {result.file_id}
                        </span>
                      )}
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="bg-[#fcfbf8] p-2.5 rounded-lg border border-gray-200">
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">FIR Number</span>
                        <span className="font-bold text-[#12335B] mt-0.5 block truncate">
                          {firNo || 'Not specified'}
                        </span>
                      </div>

                      <div className="bg-[#fcfbf8] p-2.5 rounded-lg border border-gray-200">
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">FIR Date</span>
                        <span className="font-bold text-[#12335B] mt-0.5 block truncate">
                          {firDate || 'Not specified'}
                        </span>
                      </div>

                      <div className="bg-[#fcfbf8] p-2.5 rounded-lg border border-gray-200">
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">Police Station</span>
                        <span className="font-bold text-[#12335B] mt-0.5 block truncate">
                          {policeStation || 'Not specified'}
                        </span>
                      </div>

                      <div className="bg-[#fcfbf8] p-2.5 rounded-lg border border-gray-200">
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">District / Year</span>
                        <span className="font-bold text-[#12335B] mt-0.5 block truncate">
                          {district || 'District'}{year ? ` (${year})` : ''}
                        </span>
                      </div>
                    </div>

                    {/* Explicit BNS Section Chips */}
                    <div className="pt-2 flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-[#12335B] mr-1">BNS Sections Recorded:</span>
                      {getExplicitSectionChips(result).length > 0 ? (
                        getExplicitSectionChips(result).map((sec, idx) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 text-xs font-bold bg-[#12335B] text-white rounded-md shadow-xs font-mono"
                          >
                            §{sec}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-gray-500 italic bg-gray-100 px-2.5 py-1 rounded-md">
                          None explicitly recorded in Item 2
                        </span>
                      )}
                    </div>
                  </section>

                  {/* -------------------------------------------------- */}
                  {/* 2. QUICK SUMMARY / "WHAT HAPPENED?" */}
                  {/* -------------------------------------------------- */}
                  <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-3">
                    <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                      What happened?
                    </h2>

                    <p className="text-sm text-gray-800 leading-relaxed font-normal">
                      {getCleanSummary(result)}
                    </p>

                    {/* Expandable Full Narrative Drawer */}
                    {result.extracted_text && (
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={() => setShowFullNarrative(!showFullNarrative)}
                          className="text-xs font-semibold text-[#b98528] hover:text-[#9f7020] flex items-center gap-1 transition"
                        >
                          <span>{showFullNarrative ? 'Hide FIR details ▲' : 'Read the FIR details ▼'}</span>
                        </button>

                        {showFullNarrative && (
                          <div className="mt-3 p-4 bg-[#fcfbf8] rounded-xl border border-gray-200 text-xs text-gray-700 leading-relaxed font-mono whitespace-pre-wrap max-h-80 overflow-y-auto">
                            <strong className="block text-gray-900 font-sans mb-1 text-[11px] uppercase tracking-wider">
                              Extracted FIR Narrative / Text:
                            </strong>
                            {result.extracted_text}
                          </div>
                        )}
                      </div>
                    )}
                  </section>

                  {/* -------------------------------------------------- */}
                  {/* 3. "SECTIONS RECORDED IN THIS FIR" */}
                  {/* -------------------------------------------------- */}
                  <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
                    <div>
                      <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                        Sections recorded in this FIR
                      </h2>
                      <p className="text-xs text-gray-500 mt-0.5">
                        These are the provisions explicitly recorded in the FIR.
                      </p>
                    </div>

                    {getExplicitSections(result).length === 0 ? (
                      <div className="p-4 bg-[#fcfbf8] rounded-xl border border-gray-200 text-xs text-gray-600">
                        No explicit section numbers were recorded in Item 2 of this FIR.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {getExplicitSections(result).map((c, idx) => {
                          const secKey = `explicit_${c.section}_${idx}`
                          const isExpanded = Boolean(expandedSections[secKey])
                          const summaryLine =
                            renderFieldContent(c.why_may_apply) ||
                            c.assessment ||
                            renderFieldContent(c.law_requires) ||
                            c.title

                          return (
                            <div
                              key={secKey}
                              className="border border-gray-200 rounded-xl p-4 bg-white hover:border-gray-300 transition space-y-3"
                            >
                              {/* Horizontal Compact Row */}
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                <div className="space-y-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono font-bold text-[#12335B] text-sm bg-[#f0ebd9] px-2 py-0.5 rounded border border-[#d2a14b]/30">
                                      §{c.section} BNS
                                    </span>
                                    <h3 className="font-semibold text-gray-900 text-sm truncate">
                                      {c.title}
                                    </h3>
                                  </div>
                                  <p className="text-xs text-gray-600 line-clamp-1 leading-normal">
                                    {summaryLine}
                                  </p>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => toggleSectionExpand(secKey)}
                                  className="self-start sm:self-center shrink-0 px-3 py-1.5 text-xs font-semibold text-[#12335B] bg-gray-100 hover:bg-gray-200 rounded-lg transition flex items-center gap-1"
                                >
                                  <span>{isExpanded ? 'Hide details ▲' : 'View legal explanation →'}</span>
                                </button>
                              </div>

                              {/* Expanded Inline Details (Progressive Disclosure) */}
                              {isExpanded && (
                                <div className="pt-3 border-t border-gray-100 space-y-3 text-xs text-gray-800">
                                  {c.bailable || c.cognizable ? (
                                    <div className="flex items-center gap-2 pb-1">
                                      {c.bailable && (
                                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-100 text-slate-800 border border-slate-200">
                                          {c.bailable}
                                        </span>
                                      )}
                                      {c.cognizable && (
                                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-100 text-slate-800 border border-slate-200">
                                          {c.cognizable}
                                        </span>
                                      )}
                                    </div>
                                  ) : null}

                                  {c.law_requires && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">What the law requires</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.law_requires)}</p>
                                    </div>
                                  )}

                                  {c.fir_states && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">What the FIR states</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.fir_states)}</p>
                                    </div>
                                  )}

                                  {(c.why_may_apply || c.reasoning) && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">Why this section may apply</strong>
                                      <p className="leading-relaxed text-gray-700">
                                        {renderFieldContent(c.why_may_apply || c.reasoning)}
                                      </p>
                                    </div>
                                  )}

                                  {c.punishment && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">Statutory punishment</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.punishment)}</p>
                                    </div>
                                  )}

                                  {c.what_remains_uncertain && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">What remains uncertain</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.what_remains_uncertain)}</p>
                                    </div>
                                  )}

                                  <div className="text-[11px] text-gray-400 font-mono pt-1">
                                    Source: BNS 2023 Section {c.section}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </section>

                  {/* -------------------------------------------------- */}
                  {/* 4. "POTENTIALLY RELEVANT LEGAL PROVISIONS" */}
                  {/* -------------------------------------------------- */}
                  {getPotentialSections(result).length > 0 && (
                    <section className="bg-[#fcfbf8] rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
                      <div>
                        <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                          Potentially relevant legal provisions
                        </h2>
                        <p className="text-xs text-gray-500 mt-0.5">
                          These provisions were identified from the facts described in the FIR. They are not necessarily sections recorded in Item 2.
                        </p>
                      </div>

                      <div className="space-y-3">
                        {getPotentialSections(result).map((c, idx) => {
                          const potKey = `potential_${c.section}_${idx}`
                          const isExpanded = Boolean(expandedPotentialSections[potKey])
                          const reasonLine =
                            renderFieldContent(c.why_may_apply) ||
                            c.applicability ||
                            renderFieldContent(c.law_requires) ||
                            c.title

                          return (
                            <div
                              key={potKey}
                              className="border border-gray-200 rounded-xl p-4 bg-white hover:border-gray-300 transition space-y-3"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                <div className="space-y-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono font-bold text-[#12335B] text-xs bg-gray-100 px-2 py-0.5 rounded">
                                      §{c.section}
                                    </span>
                                    <h3 className="font-semibold text-gray-900 text-sm truncate">
                                      {c.title}
                                    </h3>
                                    <span className="text-[10px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded font-medium">
                                      Potentially relevant
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-600 line-clamp-1 leading-normal">
                                    {reasonLine}
                                  </p>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => togglePotentialExpand(potKey)}
                                  className="self-start sm:self-center shrink-0 px-3 py-1.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition flex items-center gap-1"
                                >
                                  <span>{isExpanded ? 'Hide details ▲' : 'View details →'}</span>
                                </button>
                              </div>

                              {isExpanded && (
                                <div className="pt-3 border-t border-gray-100 space-y-3 text-xs text-gray-800">
                                  {c.why_may_apply && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">Why it may apply</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.why_may_apply)}</p>
                                    </div>
                                  )}

                                  {c.law_requires && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">What the law requires</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.law_requires)}</p>
                                    </div>
                                  )}

                                  {c.punishment && (
                                    <div className="bg-[#fcfbf8] p-3 rounded-lg border border-gray-200">
                                      <strong className="text-gray-900 block mb-0.5">Statutory punishment</strong>
                                      <p className="leading-relaxed text-gray-700">{renderFieldContent(c.punishment)}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </section>
                  )}

                  {/* -------------------------------------------------- */}
                  {/* 5. IMPORTANT LEGAL DISTINCTION */}
                  {/* -------------------------------------------------- */}
                  <div className="bg-white border border-[#d2a14b]/40 rounded-xl p-4 text-xs text-[#12335B] flex items-start gap-3 shadow-xs">
                    <span className="text-[#b98528] font-bold text-base shrink-0">ℹ</span>
                    <div>
                      <strong className="font-semibold text-[#12335B] block mb-0.5">Important</strong>
                      <p className="text-gray-600 leading-relaxed">
                        An FIR records allegations and the information reported to police. It does not by itself establish guilt.
                      </p>
                    </div>
                  </div>

                  {/* -------------------------------------------------- */}
                  {/* 6. FACTS / PEOPLE / DATES (COMPACT DRAWERS) */}
                  {/* -------------------------------------------------- */}
                  <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-3">
                    <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                      Stated Facts & Particulars
                    </h2>

                    <div className="space-y-2">
                      {/* People Named */}
                      {hasPeopleData && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                          <button
                            type="button"
                            onClick={() => toggleFactsDrawer('people')}
                            className="w-full text-left p-3 bg-[#fcfbf8] font-semibold text-xs text-[#12335B] flex items-center justify-between hover:bg-gray-100 transition"
                          >
                            <span>People named in the FIR</span>
                            <span>{expandedFactsDrawers.people ? '▲' : '▼'}</span>
                          </button>
                          {expandedFactsDrawers.people && (
                            <div className="p-3 bg-white border-t border-gray-200 text-xs space-y-2">
                              {complainant && (
                                <div>
                                  <span className="font-bold text-gray-700">Complainant / Informant: </span>
                                  <span className="text-gray-900">{complainant}</span>
                                </div>
                              )}
                              {accused && (
                                <div>
                                  <span className="font-bold text-gray-700">Accused / Named: </span>
                                  <span className="text-gray-900">{accused}</span>
                                </div>
                              )}
                              {victim && (
                                <div>
                                  <span className="font-bold text-gray-700">Victim / Affected Party: </span>
                                  <span className="text-gray-900">{victim}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Key Dates & Locations */}
                      {hasDatesData && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                          <button
                            type="button"
                            onClick={() => toggleFactsDrawer('dates')}
                            className="w-full text-left p-3 bg-[#fcfbf8] font-semibold text-xs text-[#12335B] flex items-center justify-between hover:bg-gray-100 transition"
                          >
                            <span>Key dates & location</span>
                            <span>{expandedFactsDrawers.dates ? '▲' : '▼'}</span>
                          </button>
                          {expandedFactsDrawers.dates && (
                            <div className="p-3 bg-white border-t border-gray-200 text-xs space-y-2">
                              {firDate && (
                                <div>
                                  <span className="font-bold text-gray-700">Date Reported: </span>
                                  <span className="text-gray-900">{firDate}</span>
                                </div>
                              )}
                              {occurrenceDate && (
                                <div>
                                  <span className="font-bold text-gray-700">Date of Occurrence: </span>
                                  <span className="text-gray-900">{occurrenceDate}</span>
                                </div>
                              )}
                              {policeStation && (
                                <div>
                                  <span className="font-bold text-gray-700">Police Station: </span>
                                  <span className="text-gray-900">{policeStation}</span>
                                </div>
                              )}
                              {district && (
                                <div>
                                  <span className="font-bold text-gray-700">District: </span>
                                  <span className="text-gray-900">{district}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Allegation Details */}
                      {hasAllegationsData && (
                        <div className="border border-gray-200 rounded-xl overflow-hidden">
                          <button
                            type="button"
                            onClick={() => toggleFactsDrawer('allegations')}
                            className="w-full text-left p-3 bg-[#fcfbf8] font-semibold text-xs text-[#12335B] flex items-center justify-between hover:bg-gray-100 transition"
                          >
                            <span>Allegation details & unestablished aspects</span>
                            <span>{expandedFactsDrawers.allegations ? '▲' : '▼'}</span>
                          </button>
                          {expandedFactsDrawers.allegations && (
                            <div className="p-3 bg-white border-t border-gray-200 text-xs space-y-3">
                              {result.what_fir_alleges && (
                                <div>
                                  <strong className="block text-gray-800 mb-0.5">Allegations Summary:</strong>
                                  <p className="text-gray-700 leading-relaxed">{result.what_fir_alleges}</p>
                                </div>
                              )}

                              {result.unestablished_facts && result.unestablished_facts.length > 0 && (
                                <div>
                                  <strong className="block text-gray-800 mb-0.5">Unestablished Aspects:</strong>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {result.unestablished_facts.map((fact, idx) => (
                                      <li key={idx}>{fact}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {result.clarifying_details && result.clarifying_details.length > 0 && (
                                <div>
                                  <strong className="block text-gray-800 mb-0.5">Details That Would Clarify:</strong>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {result.clarifying_details.map((detail, idx) => (
                                      <li key={idx}>{detail}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </section>

                  {/* -------------------------------------------------- */}
                  {/* 7. "YOUR IMMEDIATE LEGAL RIGHTS" */}
                  {/* -------------------------------------------------- */}
                  {result.rights && result.rights.length > 0 && (
                    <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-3">
                      <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                        Your immediate legal rights
                      </h2>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {result.rights.map((rightText, idx) => (
                          <div
                            key={idx}
                            className="bg-[#fcfbf8] p-3 rounded-xl border border-gray-200 space-y-1"
                          >
                            <span className="font-bold text-[#12335B] block">
                              • Right #{idx + 1}
                            </span>
                            <p className="text-gray-700 leading-relaxed">{rightText}</p>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* -------------------------------------------------- */}
                  {/* 8. "WHAT HAPPENS NEXT" */}
                  {/* -------------------------------------------------- */}
                  {result.next_steps && result.next_steps.length > 0 && (
                    <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-3">
                      <h2 className="font-serif text-lg font-semibold text-[#12335B]">
                        What happens next
                      </h2>

                      <div className="space-y-2 text-xs">
                        {result.next_steps.map((stepText, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-3 p-3 bg-[#fcfbf8] rounded-xl border border-gray-200"
                          >
                            <span className="font-mono font-bold text-[#b98528] text-sm shrink-0">
                              0{idx + 1}
                            </span>
                            <p className="text-gray-800 leading-relaxed pt-0.5">{stepText}</p>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {/* -------------------------------------------------- */}
                  {/* 9. "BOTTOM LINE" */}
                  {/* -------------------------------------------------- */}
                  {result.bottom_line && (
                    <section className="bg-[#12335B] text-white rounded-2xl border border-[#b98528]/40 p-5 shadow-md space-y-2">
                      <h3 className="font-serif text-base font-semibold text-[#dca45a] flex items-center gap-2">
                        <span>📌</span> Bottom Line
                      </h3>
                      <p className="text-xs sm:text-sm text-gray-200 leading-relaxed font-normal">
                        {result.bottom_line}
                      </p>
                    </section>
                  )}

                  {/* -------------------------------------------------- */}
                  {/* 10. SAVE / DISCLAIMER */}
                  {/* -------------------------------------------------- */}
                  {!consentDismissed && saveStatus !== 'saved' && (
                    <div className="bg-[#fcfbf8] border border-gray-300 rounded-2xl p-5 shadow-xs space-y-3">
                      <div>
                        <h4 className="font-serif text-base font-semibold text-[#12335B]">
                          Save this FIR & Analysis to My FIRs?
                        </h4>
                        <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">
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
                          className="px-5 py-2 bg-[#12335B] hover:bg-[#0c2340] text-white text-xs font-bold rounded-lg shadow-xs transition disabled:opacity-50"
                        >
                          {saveStatus === 'saving' ? 'Saving...' : 'Save to My FIRs'}
                        </button>

                        <button
                          type="button"
                          onClick={() => setConsentDismissed(true)}
                          className="px-5 py-2 bg-white border border-gray-300 text-gray-700 hover:bg-gray-100 text-xs font-semibold rounded-lg transition"
                        >
                          Don't Save
                        </button>
                      </div>
                    </div>
                  )}

                  {saveStatus === 'saved' && (
                    <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 p-3.5 rounded-xl text-xs font-medium flex items-center justify-between shadow-xs">
                      <span>✓ FIR Analysis successfully saved to My FIRs. Access it anytime from Saved FIRs tab.</span>
                      <button
                        onClick={() => setActiveTab('saved')}
                        className="underline text-emerald-950 font-bold hover:text-black ml-2 shrink-0"
                      >
                        View Saved FIRs →
                      </button>
                    </div>
                  )}

                  {/* Statutory Disclaimer */}
                  {result.disclaimer && (
                    <p className="text-[11px] text-gray-400 border-t border-gray-200 pt-3 leading-relaxed italic">
                      {result.disclaimer}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Save & Replace Confirmation Modal */}
        {showReplaceModal && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl border border-gray-200 space-y-4">
              <h3 className="font-serif text-lg font-semibold text-[#12335B]">
                Save this FIR before replacing it?
              </h3>

              <p className="text-xs text-gray-600 leading-relaxed">
                You have an unsaved FIR legal breakdown. If you replace or remove this document without saving, your current analysis will be discarded.
              </p>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowReplaceModal(false)
                    setPendingAction(null)
                  }}
                  disabled={isSavingAndReplacing}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-800 rounded-lg border border-gray-300 hover:bg-gray-100 transition text-center"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleConfirmDontSaveAndReplace}
                  disabled={isSavingAndReplacing}
                  className="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition text-center"
                >
                  Don't Save & Replace
                </button>

                <button
                  type="button"
                  onClick={handleConfirmSaveAndReplace}
                  disabled={isSavingAndReplacing}
                  className="px-4 py-2 text-xs font-bold text-white bg-[#12335B] hover:bg-[#0c2340] rounded-lg shadow-xs transition disabled:opacity-50 text-center"
                >
                  {isSavingAndReplacing ? 'Saving...' : 'Save & Replace'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal for Saved FIRs */}
        {deleteModalId !== null && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl border border-gray-200 space-y-4">
              <h3 className="font-serif text-lg font-semibold text-[#12335B]">
                Delete Saved FIR?
              </h3>

              <p className="text-xs text-gray-600 leading-relaxed">
                Delete this saved FIR and its analysis from LawAid active application storage? The database record, analysis summary, and associated document file will be permanently removed from your account.
              </p>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDeleteModalId(null)}
                  disabled={isDeleting}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-800 rounded-lg border border-gray-300 hover:bg-gray-100 transition"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={handleDeleteSavedFIR}
                  disabled={isDeleting}
                  className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-xs transition disabled:opacity-50"
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
            <div className="bg-[#12335B] rounded-2xl border border-white/20 p-5 max-w-2xl w-full shadow-2xl flex flex-col items-center relative overflow-hidden space-y-4">
              <div className="w-full flex items-center justify-between text-white border-b border-white/10 pb-3">
                <div className="flex items-center gap-2 font-serif text-base font-semibold text-[#dca45a]">
                  <span>📷</span>
                  <span>Take FIR Photo</span>
                </div>
                <button
                  type="button"
                  onClick={stopCamera}
                  className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-white font-bold flex items-center justify-center transition text-xs"
                  title="Close camera"
                >
                  ✕
                </button>
              </div>

              <div className="relative w-full aspect-[4/3] max-h-[55vh] bg-black rounded-xl overflow-hidden flex items-center justify-center border border-white/10 shadow-inner">
                {isCameraStarting && (
                  <div className="flex flex-col items-center gap-2 text-white/80">
                    <div className="w-8 h-8 border-3 border-[#b98528] border-t-transparent rounded-full animate-spin" />
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

                {cameraStream && !cameraError && (
                  <div className="absolute inset-4 border-2 border-dashed border-white/40 rounded-lg pointer-events-none flex items-start justify-center p-2">
                    <span className="text-[10px] font-medium text-white/80 bg-black/50 px-2.5 py-0.5 rounded-full backdrop-blur-xs">
                      Align FIR Document Within Frame
                    </span>
                  </div>
                )}

                {cameraError && (
                  <div className="p-6 text-center text-white max-w-md space-y-3">
                    <div className="text-2xl">⚠️</div>
                    <p className="text-xs font-medium leading-relaxed text-red-200">
                      {cameraError}
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => {
                          stopCamera()
                          fileInputRef.current?.click()
                        }}
                        className="px-3.5 py-1.5 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-lg transition"
                      >
                        Upload Image Instead
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          stopCamera()
                          cameraInputRef.current?.click()
                        }}
                        className="px-3.5 py-1.5 bg-white/20 hover:bg-white/30 text-white text-xs font-semibold rounded-lg transition"
                      >
                        Try Mobile Native Camera
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {cameraStream && !cameraError && (
                <div className="w-full flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={stopCamera}
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold rounded-lg transition"
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    onClick={capturePhoto}
                    className="px-6 py-2.5 bg-[#b98528] hover:bg-[#9f7020] text-white text-xs font-bold rounded-lg shadow-md transition flex items-center gap-2"
                  >
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
                    <span>Capture Photo</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      stopCamera()
                      cameraInputRef.current?.click()
                    }}
                    className="text-[11px] text-white/60 hover:text-white underline transition"
                  >
                    Mobile Fallback
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