'use client'

import Navbar from '@/components/Navbar'
import { lawyerDocumentsAPI } from '@/lib/api'
import LawyerTestHeader from '@/components/LawyerTestHeader'
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
    <>
      <Navbar />
      <main className="relative min-h-screen overflow-hidden">
        <div className="fixed inset-0 -z-10"><img src="/images/lawaid-citizen-dashboard.png" alt="" className="h-full w-full object-cover object-center" /></div>
        <div className="fixed inset-0 -z-10 bg-[#f7f4ec]/65" />
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <LawyerTestHeader title="Case Documents" caseId={caseId} />
          <header className="mb-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#98701f]">Lawyer Portal</p>
            <p className="mx-auto max-w-2xl text-sm leading-6 text-[#36516e] md:text-base">Upload case documents and review the text extracted locally before the next case workflow step.</p>
          </header>
          {message && <div role="alert" className="mb-5 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50/95 p-4 text-sm text-amber-900"><AlertCircle className="mt-0.5 shrink-0" size={18} /><span>{message}</span></div>}
          {success && <div role="status" className="mb-5 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">{success}</div>}
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(290px,0.85fr)]">
            <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-8">
              <div className="mb-6 flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]"><FolderOpen size={22} /></div><div><h2 className="font-serif text-2xl font-semibold text-[#0f305b]">Upload Case Documents</h2><p className="mt-1 text-sm text-[#64748b]">Files are kept in private case storage.</p></div></div>
              <div {...getRootProps()} className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${isDragActive ? 'border-[#c28b19] bg-amber-50' : 'border-[#d6c9aa] bg-[#faf8f2]/85 hover:border-[#c28b19]'}`}>
                <input {...getInputProps()} /><div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#0f305b] text-white"><UploadCloud size={30} /></div>
                <p className="mt-5 text-lg font-semibold text-[#0f305b]">{isDragActive ? 'Drop your files here' : 'Drag and drop files here'}</p><p className="mt-2 text-sm text-[#64748b]">PDF, DOCX, JPG or PNG · Maximum 20 MB per file</p>
                <div className="mt-6 flex flex-wrap justify-center gap-3"><button type="button" onClick={open} className="inline-flex items-center gap-2 rounded-xl bg-[#0f305b] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#173f70]"><FileUp size={17} />Browse Files</button><button type="button" onClick={() => setShowFormats(true)} className="rounded-xl border border-[#cdbd97] px-5 py-3 text-sm font-semibold text-[#36516e] hover:bg-white">Supported Formats</button></div>
              </div>
              <div className="mt-8 flex items-center justify-between gap-3"><h3 className="font-serif text-xl font-semibold text-[#0f305b]">Selected Documents</h3><span className="rounded-full bg-[#f3efe4] px-3 py-1 text-xs font-semibold text-[#6d5a32]">{documents.length} {documents.length === 1 ? 'file' : 'files'}</span></div>
              {loading ? <div className="mt-5 flex justify-center py-12 text-[#36516e]"><LoaderCircle className="animate-spin" /></div> : documents.length === 0 ? <div className="mt-4 rounded-xl border border-dashed border-[#d9d3c6] px-4 py-10 text-center"><FileText className="mx-auto text-[#b0a58e]" size={30} /><p className="mt-3 text-sm text-[#64748b]">Select files to add them to this case workspace.</p></div> : <ul className="mt-4 space-y-3">{documents.map((document) => <li key={document.id} className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4"><div className="flex gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#f4f0e6] text-[#0f305b]"><FileText size={20} /></div><div className="min-w-0 flex-1"><p className="break-all text-sm font-semibold text-[#183b62]">{document.name}</p><p className="mt-1 text-xs text-[#718096]">{formatSize(document.size_bytes)} · {document.type.toUpperCase()} {document.uploaded_at ? `· ${new Date(document.uploaded_at).toLocaleString()}` : ''}</p><p className="mt-1 text-xs text-[#64748b]">Extracted text: {document.extracted_text_available ? 'available' : 'not available'}</p><span className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyle[document.status]}`}>{['uploading', 'processing'].includes(document.status) && <LoaderCircle className="animate-spin" size={13} />}{document.status === 'parsed' && <CheckCircle2 size={13} />}{document.status === 'failed' && <AlertCircle size={13} />}{displayStatus(document.status)}</span>{['uploading', 'processing'].includes(document.status) && <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-blue-100"><div className="h-full bg-[#2368c4] transition-all" style={{ width: `${document.progress}%` }} /></div>}{document.error && <p className="mt-2 text-xs text-[#be3737]">{document.error}</p>}</div><div className="flex shrink-0 gap-1">{document.status === 'failed' && !document.id.startsWith('local-') && <button onClick={() => retryDocument(document)} aria-label={`Retry ${document.name}`} className="rounded-lg p-2 text-[#2368c4] hover:bg-blue-50"><RefreshCw size={17} /></button>}<button onClick={() => removeDocument(document)} disabled={uploading || deletingId === document.id} aria-label={`Remove ${document.name}`} className="inline-flex items-center gap-1 rounded-lg p-2 text-[#8a6b59] hover:bg-red-50 hover:text-red-700 disabled:opacity-40">{deletingId === document.id ? <LoaderCircle className="animate-spin" size={17} /> : <Trash2 size={17} />}<span className="text-xs font-semibold">Remove</span></button></div></div></li>)}</ul>}
              <div className="mt-7 flex justify-end"><button onClick={uploadSelected} disabled={uploading || !caseId || !documents.some((document) => document.status === 'waiting')} className="inline-flex items-center gap-2 rounded-xl bg-[#0f305b] px-6 py-3 text-sm font-bold text-white transition hover:bg-[#173f70] disabled:cursor-not-allowed disabled:bg-slate-300">{uploading && <LoaderCircle className="animate-spin" size={17} />}{uploading ? 'Uploading Documents…' : 'Upload Selected Documents'}</button></div>
            </section>
            <aside className="space-y-6">
              <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.10)]"><div className="flex items-center justify-between"><h2 className="font-serif text-2xl font-semibold text-[#0f305b]">Document Overview</h2><button onClick={() => caseId && refreshDocuments(caseId)} className="rounded-lg p-2 text-[#0f305b] hover:bg-[#f7f4ec]" aria-label="Refresh documents"><RefreshCw size={18} /></button></div><dl className="mt-5 grid grid-cols-3 gap-3 text-center"><div className="rounded-xl bg-[#f7f4ec] p-3"><dt className="text-xs text-[#64748b]">Documents</dt><dd className="mt-1 text-2xl font-bold text-[#0f305b]">{overview.files}</dd></div><div className="rounded-xl bg-[#f7f4ec] p-3"><dt className="text-xs text-[#64748b]">Pages</dt><dd className="mt-1 text-2xl font-bold text-[#0f305b]">{overview.pages}</dd></div><div className="rounded-xl bg-[#f7f4ec] p-3"><dt className="text-xs text-[#64748b]">Entities</dt><dd className="mt-1 text-2xl font-bold text-[#0f305b]">{overview.entities}</dd></div></dl><p className="mt-4 text-xs leading-5 text-[#64748b]">DOCX page counts are unavailable until rendered; entities only appear when local extraction finds them.</p></section>
              <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.10)]"><h2 className="font-serif text-2xl font-semibold text-[#0f305b]">Processing Queue</h2><div className="mt-4 space-y-3">{documents.filter((document) => !document.id.startsWith('local-')).length === 0 ? <p className="text-sm text-[#64748b]">No uploaded documents yet.</p> : documents.filter((document) => !document.id.startsWith('local-')).map((document) => <div key={document.id} className="flex items-center justify-between gap-3 border-b border-[#eee8dd] pb-3 last:border-0"><span className="truncate text-sm font-medium text-[#36516e]">{document.name}</span><span className={`shrink-0 text-xs font-semibold ${statusStyle[document.status].split(' ')[1]}`}>{displayStatus(document.status)}</span></div>)}</div></section>
              <button onClick={analyzeDocuments} disabled={!allParsed || analyzing} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#c28b19] px-6 py-4 text-sm font-bold text-white shadow-sm transition hover:bg-[#a97512] disabled:cursor-not-allowed disabled:bg-[#d7d0c0] disabled:text-[#777267]">{analyzing && <LoaderCircle className="animate-spin" size={18} />}{analyzing ? 'Checking Documents…' : 'Analyze Case Documents'}</button>
              <p className="text-center text-xs leading-5 text-[#64748b]">Analysis uses parsed text from this case workspace. Review results on the AI Analysis page.</p>
            </aside>
          </div>
          <div className="mt-7"><Link href="/lawyer" className="text-sm font-semibold text-[#315b82] hover:text-[#c28b19]">← Back to Lawyer Dashboard</Link></div>
        </div>
      </main>
      {showFormats && <div role="dialog" aria-modal="true" aria-labelledby="formats-title" className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0b274a]/45 p-4"><div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><h2 id="formats-title" className="font-serif text-2xl font-semibold text-[#0f305b]">Supported Formats</h2><p className="mt-2 text-sm text-[#64748b]">Each file must be 20 MB or less.</p></div><button aria-label="Close supported formats" onClick={() => setShowFormats(false)} className="rounded-lg p-1 text-[#36516e] hover:bg-slate-100"><X /></button></div><ul className="mt-5 space-y-2 text-sm text-[#36516e]"><li>PDF — text and page count extracted; scanned files use local OCR when available.</li><li>DOCX — paragraph text extracted; page count is not inferred.</li><li>JPG / JPEG / PNG — local OCR attempted when configured.</li></ul></div></div>}
    </>
  )
}
