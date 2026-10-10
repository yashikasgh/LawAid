'use client'

import LawyerCaseLayout from '@/components/LawyerCaseLayout'
import { lawyerDocumentsAPI } from '@/lib/api'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  FileUp,
  FolderOpen,
  LoaderCircle,
  RefreshCw,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'

type DocumentStatus = 'waiting' | 'uploading' | 'processing' | 'parsed' | 'failed'

type CaseDocument = {
  id: string
  name: string
  type: string
  size_bytes: number
  uploaded_at?: string | null
  status: DocumentStatus
  progress: number
  pages?: number | null
  extracted_text_available?: boolean
  extracted_entities: string[]
  error?: string | null
  file?: File
}

const MAX_SIZE = 20 * 1024 * 1024
const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
}

const statusStyle: Record<DocumentStatus, string> = {
  waiting: 'bg-slate-100 text-slate-600',
  uploading: 'bg-blue-50 text-[#2368c4]',
  processing: 'bg-blue-50 text-[#2368c4]',
  parsed: 'bg-emerald-50 text-[#148c5f]',
  failed: 'bg-red-50 text-[#be3737]',
}

function displayStatus(status: DocumentStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatSize(bytes: number) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function LawyerDocumentsPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [documents, setDocuments] = useState<CaseDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [message, setMessage] = useState('')
  const [showFormats, setShowFormats] = useState(false)
  const [metrics, setMetrics] = useState<{ documents: number; pages: number; extracted_entities: number } | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [success, setSuccess] = useState('')

  const refreshDocuments = useCallback(async (id: string) => {
    const [response, metricResponse] = await Promise.all([
      lawyerDocumentsAPI.list(id),
      lawyerDocumentsAPI.metrics(id),
    ])
    setDocuments(response.data)
    setMetrics(metricResponse.data)
  }, [])

  useEffect(() => {
    let active = true
    async function loadWorkspace() {
      try {
        const workspace = await lawyerDocumentsAPI.workspace()
        if (!active) return
        const id = workspace.data.id as string
        setCaseId(id)
        await refreshDocuments(id)
      } catch (error: any) {
        if (active) setMessage(error?.response?.data?.detail || 'Unable to load your case documents.')
      } finally {
        if (active) setLoading(false)
      }
    }
    loadWorkspace()
    return () => { active = false }
  }, [refreshDocuments])

  const addFiles = useCallback((files: File[]) => {
    const accepted: CaseDocument[] = []
    const rejected: string[] = []
    for (const file of files) {
      const extension = file.name.split('.').pop()?.toLowerCase()
      if (file.size > MAX_SIZE) rejected.push(`${file.name}: exceeds 20 MB`)
      else if (!extension || !['pdf', 'docx', 'jpg', 'jpeg', 'png'].includes(extension)) rejected.push(`${file.name}: unsupported file type`)
      else if (documents.some((document) => document.name === file.name && document.size_bytes === file.size)) rejected.push(`${file.name}: already selected`)
      else accepted.push({
        id: `local-${file.name}-${file.size}-${file.lastModified}`,
        name: file.name,
        type: extension,
        size_bytes: file.size,
        status: 'waiting',
        progress: 0,
        extracted_entities: [],
        file,
      })
    }
    if (accepted.length) setDocuments((current) => [...current, ...accepted])
    if (rejected.length) setMessage(rejected.join(' · '))
  }, [documents])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop: addFiles,
    accept: ACCEPTED,
    maxSize: MAX_SIZE,
    multiple: true,
    noClick: true,
    noKeyboard: true,
  })

  async function uploadSelected() {
    if (!caseId || uploading) return
    const pending = documents.filter((document) => document.status === 'waiting' && document.file)
    if (!pending.length) return
    setUploading(true)
    setMessage('')
    setDocuments((current) => current.map((document) => pending.some((item) => item.id === document.id)
      ? { ...document, status: 'uploading', progress: 1 } : document))
    try {
      const response = await lawyerDocumentsAPI.upload(caseId, pending.map((document) => document.file!), (progress) => {
        setDocuments((current) => current.map((document) => pending.some((item) => item.id === document.id)
          ? { ...document, progress } : document))
      })
      const uploaded = response.data as CaseDocument[]
      setDocuments((current) => [
        ...current.filter((document) => !pending.some((item) => item.id === document.id)),
        ...uploaded,
      ])
      if (uploaded.some((document) => document.status === 'failed')) setMessage('One or more documents could not be parsed. Use Retry after checking the file.')
      await refreshDocuments(caseId)
    } catch (error: any) {
      const detail = error?.response?.data?.detail || 'Upload failed. Please retry.'
      setMessage(detail)
      setDocuments((current) => current.map((document) => pending.some((item) => item.id === document.id)
        ? { ...document, status: 'failed', progress: 100, error: detail } : document))
    } finally {
      setUploading(false)
    }
  }

  async function removeDocument(document: CaseDocument) {
    if (document.id.startsWith('local-')) {
      setDocuments((current) => current.filter((item) => item.id !== document.id))
      return
    }
    if (!caseId) return
    if (!window.confirm(`Remove ${document.name}? This deletes the stored file. Analysis and timeline results that depend on it will be marked for review.`)) return
    setDeletingId(document.id)
    setMessage('')
    setSuccess('')
    try {
      await lawyerDocumentsAPI.remove(caseId, document.id)
      setDocuments((current) => current.filter((item) => item.id !== document.id))
      await refreshDocuments(caseId)
      setSuccess(`${document.name} was deleted. Any dependent analysis was marked for review.`)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Could not remove this document.')
    } finally {
      setDeletingId(null)
    }
  }

  async function retryDocument(document: CaseDocument) {
    if (!caseId || document.id.startsWith('local-')) return
    setDocuments((current) => current.map((item) => item.id === document.id ? { ...item, status: 'processing', progress: 65, error: null } : item))
    try {
      const response = await lawyerDocumentsAPI.retry(caseId, document.id)
      setDocuments((current) => current.map((item) => item.id === document.id ? response.data : item))
      await refreshDocuments(caseId)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Could not retry parsing this document.')
      await refreshDocuments(caseId)
    }
  }

  async function analyzeDocuments() {
    if (!caseId || analyzing) return
    setAnalyzing(true)
    setMessage('')
    try {
      await lawyerDocumentsAPI.analyze(caseId)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Unable to start case analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  const overview = useMemo(() => ({
    files: metrics?.documents ?? documents.filter((document) => !document.id.startsWith('local-')).length,
    pages: metrics?.pages ?? documents.reduce((total, document) => total + (document.pages || 0), 0),
    entities: metrics?.extracted_entities ?? documents.reduce((total, document) => total + document.extracted_entities.length, 0),
  }), [documents, metrics])
  const allParsed = documents.length > 0 && documents.every((document) => document.status === 'parsed')

  return (
    <LawyerCaseLayout caseId={caseId}>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Header matching screenshot */}
        <header className="mb-10 text-center">
          <div className="flex items-center justify-center gap-4 mb-4">
            <div className="h-[1px] w-12 bg-[#d2a14b]/60"></div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d2a14b]">
              Lawyer Portal
            </p>
            <div className="h-[1px] w-12 bg-[#d2a14b]/60"></div>
          </div>
          <h1 className="font-serif text-4xl font-bold tracking-tight text-[#0f305b] sm:text-5xl">
            Case Documents
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-[#36516e]">
            Upload case documents to begin AI-powered case analysis.
          </p>
        </header>

        {message && <div role="alert" className="mb-5 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50/95 p-4 text-sm text-amber-900"><AlertCircle className="mt-0.5 shrink-0" size={18} /><span>{message}</span></div>}
        {success && <div role="status" className="mb-5 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">{success}</div>}
        
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(290px,0.85fr)]">
          <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]"><FolderOpen size={22} /></div>
              <div className="flex-1 flex justify-between items-center">
                <h2 className="font-serif text-2xl font-bold text-[#0f305b]">Upload Case Documents</h2>
                <button type="button" onClick={() => setShowFormats(true)} className="flex items-center gap-1.5 text-xs font-semibold text-[#64748b] hover:text-[#0f305b] rounded-full border border-[#e2d8c3] px-3 py-1 bg-white">
                  <AlertCircle size={14} /> View Supported Formats
                </button>
              </div>
            </div>
            
            <div {...getRootProps()} className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${isDragActive ? 'border-[#c28b19] bg-amber-50' : 'border-[#d6c9aa] bg-[#faf8f2]/85 hover:border-[#c28b19]'}`}>
              <input {...getInputProps()} />
              <div className="mx-auto flex h-[72px] w-[72px] items-center justify-center rounded-2xl bg-[#fdfaf3]">
                 {/* Decorative file icons based on screenshot */}
                 <div className="relative w-full h-full flex items-center justify-center">
                   <div className="absolute top-2 left-2 w-10 h-12 bg-white border border-[#e6decc] rounded shadow-sm opacity-50"></div>
                   <div className="absolute top-3 right-2 w-10 h-12 bg-white border border-[#e6decc] rounded shadow-sm opacity-70"></div>
                   <div className="absolute z-10 w-11 h-12 bg-[#c28b19] rounded shadow-md flex items-center justify-center">
                      <div className="w-6 space-y-1">
                        <div className="h-0.5 w-full bg-white/80 rounded"></div>
                        <div className="h-0.5 w-full bg-white/80 rounded"></div>
                        <div className="h-0.5 w-3/4 bg-white/80 rounded"></div>
                      </div>
                   </div>
                 </div>
              </div>
              <p className="mt-5 text-base font-bold text-[#0f305b]">{isDragActive ? 'Drop your files here' : <>Drag & drop files here or <span className="text-[#c28b19]">browse</span> from your computer</>}</p>
              <p className="mt-2 text-sm text-[#64748b]">Supported formats: PDF, DOCX, JPG, PNG &bull; Max 20 MB per file</p>
              
              <div className="mt-6 flex justify-center">
                <button type="button" onClick={open} className="inline-flex items-center gap-2 rounded-xl bg-[#c28b19] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#a87815]">
                  <FileUp size={18} /> Browse Files
                </button>
              </div>
            </div>

            <div className="mt-8 flex items-center justify-between gap-3 border-b border-[#eee8dd] pb-3">
              <h3 className="font-bold text-[#0f305b]">Selected Documents ({documents.length})</h3>
              <button onClick={() => {}} className="text-xs font-semibold text-[#be3737] hover:text-red-700 flex items-center gap-1">
                <Trash2 size={14} /> Clear All
              </button>
            </div>
            
            {loading ? (
              <div className="mt-5 flex justify-center py-12 text-[#36516e]"><LoaderCircle className="animate-spin" /></div>
            ) : documents.length === 0 ? (
              <div className="mt-4 py-8 text-center">
                <p className="text-sm text-[#64748b]">Select files to add them to this case workspace.</p>
              </div>
            ) : (
              <ul className="mt-4 space-y-3">
                {documents.map((document) => (
                  <li key={document.id} className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4 shadow-sm">
                    <div className="flex gap-4 items-center">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#ffebe6] text-[#ff5a36]">
                        <span className="text-[10px] font-bold">PF</span>
                      </div>
                      
                      <div className="min-w-0 flex-1 flex flex-col justify-center">
                        <p className="truncate text-sm font-bold text-[#0f305b]">{document.name}</p>
                        <p className="mt-1 text-[11px] text-[#8ba2ba]">Uploaded just now</p>
                      </div>
                      
                      <div className="shrink-0 w-24">
                         <span className="inline-flex items-center rounded bg-[#ffebe6] px-2 py-0.5 text-[10px] font-bold text-[#ff5a36]">
                           FIR
                         </span>
                      </div>
                      
                      <div className="shrink-0 w-16 text-right">
                        <span className="text-[11px] font-medium text-[#64748b]">{formatSize(document.size_bytes)}</span>
                      </div>
                      
                      <div className="shrink-0 w-32">
                        <span className={`inline-flex w-full items-center justify-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${statusStyle[document.status]}`}>
                          {['uploading', 'processing'].includes(document.status) && <LoaderCircle className="animate-spin" size={13} />}
                          {document.status === 'parsed' && <CheckCircle2 size={13} />}
                          {document.status === 'failed' && <AlertCircle size={13} />}
                          {displayStatus(document.status)}
                        </span>
                        {['uploading', 'processing'].includes(document.status) && (
                          <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full bg-[#2368c4] transition-all" style={{ width: `${document.progress}%` }} />
                          </div>
                        )}
                        {document.status === 'parsed' && (
                          <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full bg-[#148c5f] w-full" />
                          </div>
                        )}
                      </div>
                      
                      <div className="flex shrink-0">
                        {document.status === 'failed' && !document.id.startsWith('local-') && (
                          <button onClick={() => retryDocument(document)} aria-label={`Retry ${document.name}`} className="p-2 text-[#2368c4] hover:bg-blue-50 rounded-lg">
                            <RefreshCw size={17} />
                          </button>
                        )}
                        <button onClick={() => removeDocument(document)} disabled={uploading || deletingId === document.id} aria-label={`Remove ${document.name}`} className="p-2 text-[#8ba2ba] hover:text-red-500 transition disabled:opacity-40">
                          {deletingId === document.id ? <LoaderCircle className="animate-spin" size={18} /> : <X size={18} />}
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            
            <div className="mt-7 flex justify-end">
              <button onClick={uploadSelected} disabled={uploading || !caseId || !documents.some((document) => document.status === 'waiting')} className="inline-flex items-center gap-2 rounded-xl bg-[#0f305b] px-6 py-3 text-sm font-bold text-white transition hover:bg-[#173f70] disabled:opacity-50">
                {uploading && <LoaderCircle className="animate-spin" size={17} />}
                {uploading ? 'Uploading Documents…' : 'Upload Selected Documents'}
              </button>
            </div>
          </section>

          <aside className="space-y-6">
            <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.10)]">
              <div className="flex items-center gap-3 mb-5 border-b border-[#eee8dd] pb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f8f6f1] text-[#c28b19]">
                  <FileText size={20} />
                </div>
                <div>
                  <h2 className="font-serif text-xl font-bold text-[#0f305b]">Document Overview</h2>
                  <p className="text-xs text-[#64748b]">Track the processing status of your uploaded documents.</p>
                </div>
              </div>
              
              <dl className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-xl border border-[#eee8dd] bg-[#fdfdfb] py-4">
                  <dt className="flex justify-center mb-1 text-[#c28b19]"><FileText size={18} /></dt>
                  <dd className="text-xl font-bold text-[#0f305b]">{overview.files}</dd>
                  <dt className="text-[10px] uppercase font-bold text-[#64748b] mt-1">Documents</dt>
                </div>
                <div className="rounded-xl border border-[#eee8dd] bg-[#fdfdfb] py-4">
                  <dt className="flex justify-center mb-1 text-[#c28b19]"><FileText size={18} /></dt>
                  <dd className="text-xl font-bold text-[#0f305b]">{overview.pages}</dd>
                  <dt className="text-[10px] uppercase font-bold text-[#64748b] mt-1">Pages</dt>
                </div>
                <div className="rounded-xl border border-[#eee8dd] bg-[#fdfdfb] py-4">
                  <dt className="flex justify-center mb-1 text-[#c28b19]"><FolderOpen size={18} /></dt>
                  <dd className="text-xl font-bold text-[#0f305b]">{overview.entities}</dd>
                  <dt className="text-[10px] uppercase font-bold text-[#64748b] mt-1">Extracted Entities</dt>
                </div>
              </dl>
              
              <h3 className="font-bold text-[#0f305b] mt-6 mb-3">Processing Queue</h3>
              <div className="space-y-4">
                {documents.filter((document) => !document.id.startsWith('local-')).length === 0 ? (
                  <p className="text-sm text-[#64748b]">No uploaded documents yet.</p>
                ) : (
                  documents.filter((document) => !document.id.startsWith('local-')).map((document, idx) => (
                    <div key={document.id} className="flex items-center gap-3 relative">
                      {idx !== documents.filter((d) => !d.id.startsWith('local-')).length - 1 && (
                        <div className="absolute left-3.5 top-8 bottom-[-16px] w-[1px] bg-[#e6e0d4]"></div>
                      )}
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#c28b19] text-xs font-bold text-white z-10">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0 flex flex-col justify-center">
                        <span className="truncate text-xs font-bold text-[#0f305b]">{document.name}</span>
                        <span className="text-[10px] text-[#64748b]">
                          {document.status === 'parsed' ? 'Extracting text and analyzing content...' 
                            : document.status === 'waiting' ? 'In queue for processing...' 
                            : 'Reading document and extracting information...'}
                        </span>
                      </div>
                      <span className={`shrink-0 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 border ${
                        document.status === 'parsed' ? 'border-emerald-200 bg-emerald-50 text-[#148c5f]' 
                        : document.status === 'processing' ? 'border-blue-200 bg-blue-50 text-[#2368c4]' 
                        : 'border-slate-200 bg-slate-50 text-slate-500'
                      }`}>
                        {document.status === 'parsed' && <CheckCircle2 size={12} />}
                        {['uploading', 'processing'].includes(document.status) && <LoaderCircle className="animate-spin" size={12} />}
                        <span className="text-[10px] font-bold">{displayStatus(document.status)}</span>
                      </span>
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-6 rounded-xl bg-[#f8f9fa] p-4 flex gap-3 items-start border border-[#e5e7eb]">
                <div className="text-[#64748b] mt-0.5">🔒</div>
                <div>
                  <p className="text-xs font-bold text-[#0f305b]">Your case documents are processed securely and remain private.</p>
                  <p className="text-[10px] text-[#64748b] mt-1">All files are encrypted and stored securely. Only you can access them.</p>
                </div>
              </div>
              
              <div className="mt-4">
                <button onClick={analyzeDocuments} disabled={!allParsed || analyzing} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#c28b19] px-6 py-4 text-sm font-bold text-white shadow-md transition hover:bg-[#a97512] disabled:opacity-60 disabled:cursor-not-allowed">
                  <FileText size={18} />
                  {analyzing && <LoaderCircle className="animate-spin" size={18} />}
                  {analyzing ? 'Checking Documents…' : 'Analyze Case Documents →'}
                </button>
                <p className="text-center text-[10px] text-white/90 mt-2 absolute w-full left-0 bottom-3">Upload and process all documents to continue</p>
              </div>
            </section>
          </aside>
        </div>
      </div>
      
      {showFormats && (
        <div role="dialog" aria-modal="true" aria-labelledby="formats-title" className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0b274a]/45 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="formats-title" className="font-serif text-2xl font-semibold text-[#0f305b]">Supported Formats</h2>
                <p className="mt-2 text-sm text-[#64748b]">Each file must be 20 MB or less.</p>
              </div>
              <button aria-label="Close supported formats" onClick={() => setShowFormats(false)} className="rounded-lg p-1 text-[#36516e] hover:bg-slate-100"><X /></button>
            </div>
            <ul className="mt-5 space-y-2 text-sm text-[#36516e]">
              <li>PDF — text and page count extracted; scanned files use local OCR when available.</li>
              <li>DOCX — paragraph text extracted; page count is not inferred.</li>
              <li>JPG / JPEG / PNG — local OCR attempted when configured.</li>
            </ul>
          </div>
        </div>
      )}
    </LawyerCaseLayout>
  )
}
