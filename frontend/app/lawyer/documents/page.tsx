 'use client'

import Navbar from '@/components/Navbar'
import { firAPI } from '@/lib/api'
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
} from 'lucide-react'
import Link from 'next/link'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'

type DocumentItem = {
  id: string
  file: File
  status: 'Waiting' | 'Processing' | 'Parsed' | 'Failed'
  error?: string
}

const MAX_SIZE = 20 * 1024 * 1024

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
}

export default function LawyerDocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const addFiles = useCallback(
    (files: File[]) => {
      setMessage('')

      const accepted: DocumentItem[] = []
      const rejected: string[] = []

      for (const file of files) {
        if (file.size > MAX_SIZE) {
          rejected.push(`${file.name}: exceeds 20 MB`)
          continue
        }

        const extension = file.name.split('.').pop()?.toLowerCase()

        if (!extension || !['pdf', 'docx', 'jpg', 'jpeg', 'png'].includes(extension)) {
          rejected.push(`${file.name}: unsupported file type`)
          continue
        }

        if (
          documents.some(
            (item) => item.file.name === file.name && item.file.size === file.size,
          )
        ) {
          rejected.push(`${file.name}: already selected`)
          continue
        }

        accepted.push({
          id: `${file.name}-${file.size}-${file.lastModified}`,
          file,
          status: 'Waiting',
        })
      }

      if (accepted.length) {
        setDocuments((current) => [...current, ...accepted])
      }

      if (rejected.length) {
        setMessage(rejected.join(' · '))
      }
    },
    [documents],
  )

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      addFiles(acceptedFiles)
    },
    [addFiles],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: MAX_SIZE,
    multiple: true,
    noClick: true,
    noKeyboard: true,
  })

  function removeDocument(id: string) {
    setDocuments((current) => current.filter((item) => item.id !== id))
  }

  async function processDocuments() {
    if (busy || documents.length === 0) return

    setBusy(true)
    setMessage('')

    const pending = documents.filter((item) => item.status !== 'Parsed')
    let lastResult: unknown = null

    try {
      for (const item of pending) {
        setDocuments((current) =>
          current.map((doc) =>
            doc.id === item.id
              ? { ...doc, status: 'Processing', error: undefined }
              : doc,
          ),
        )

        const extension = item.file.name.split('.').pop()?.toLowerCase()

        if (!['pdf', 'jpg', 'jpeg', 'png'].includes(extension || '')) {
          setDocuments((current) =>
            current.map((doc) =>
              doc.id === item.id
                ? {
                    ...doc,
                    status: 'Failed',
                    error: 'The existing FIR API does not document DOCX support.',
                  }
                : doc,
            ),
          )
          continue
        }

        try {
          const response = await firAPI.understand(item.file)
          lastResult = response.data

          setDocuments((current) =>
            current.map((doc) =>
              doc.id === item.id
                ? { ...doc, status: 'Parsed', error: undefined }
                : doc,
            ),
          )
        } catch (error: unknown) {
          const errorMessage =
            typeof error === 'object' && error !== null && 'message' in error
              ? String(error.message)
              : 'Processing failed. Please retry.'

          setDocuments((current) =>
            current.map((doc) =>
              doc.id === item.id
                ? { ...doc, status: 'Failed', error: errorMessage }
                : doc,
            ),
          )
        }
      }

      if (lastResult !== null) {
        try {
          sessionStorage.setItem(
            'lawaid_lawyer_analysis',
            JSON.stringify(lastResult),
          )

          const latestDocuments = documents.map(({ file, ...rest }) => ({
            ...rest,
            name: file.name,
            size: file.size,
            type: file.type,
          }))

          sessionStorage.setItem(
            'lawaid_lawyer_documents',
            JSON.stringify(latestDocuments),
          )
        } catch {
          setMessage('Processing finished, but the results could not be saved in this session.')
        }
      }
    } finally {
      setBusy(false)
    }
  }

  const parsedCount = documents.filter((doc) => doc.status === 'Parsed').length
  const failedCount = documents.filter((doc) => doc.status === 'Failed').length

  return (
    <>
      <Navbar />

      <main className="relative min-h-screen overflow-hidden">
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-citizen-dashboard.png"
            alt=""
            className="h-full w-full object-cover object-center"
          />
        </div>

        <div className="fixed inset-0 -z-10 bg-[#f7f4ec]/55" />

        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <header className="mb-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#98701f]">
              Lawyer Portal
            </p>

            <h1 className="mt-3 font-serif text-4xl font-semibold tracking-tight text-[#0f305b] md:text-5xl">
              Case Documents
            </h1>

            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#36516e] md:text-base">
              Upload and organize case files before reviewing the information extracted from them.
            </p>
          </header>

          {message && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50/95 p-4 text-sm text-amber-900"
            >
              <AlertCircle className="mt-0.5 shrink-0" size={18} />
              <span>{message}</span>
            </div>
          )}

          <section className="w-full rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-8 lg:p-10">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                <FolderOpen size={22} />
              </div>

              <div>
                <h2 className="font-serif text-2xl font-semibold text-[#0f305b] sm:text-3xl">
                  Upload Case Documents
                </h2>
                <p className="mt-1 text-sm text-[#64748b]">
                  Add the files relevant to this case.
                </p>
              </div>
            </div>

            <div
              {...getRootProps()}
              className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors sm:p-14 ${
                isDragActive
                  ? 'border-[#c28b19] bg-amber-50'
                  : 'border-[#d6c9aa] bg-[#faf8f2]/85 hover:border-[#c28b19]'
              }`}
            >
              <input {...getInputProps()} />

              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#0f305b] text-white">
                <UploadCloud size={30} />
              </div>

              <p className="mt-5 text-lg font-semibold text-[#0f305b]">
                {isDragActive ? 'Drop your files here' : 'Drag and drop files here'}
              </p>

              <p className="mt-2 text-sm text-[#64748b]">
                PDF, DOCX, JPG or PNG · Maximum 20 MB per file
              </p>

              <button
                type="button"
                onClick={open}
                className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#0f305b] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#173f70] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2"
              >
                <FileUp size={17} />
                Browse Files
              </button>
            </div>

            <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-serif text-xl font-semibold text-[#0f305b]">
                Selected Documents
              </h3>

              <span className="rounded-full bg-[#f3efe4] px-3 py-1 text-xs font-semibold text-[#6d5a32]">
                {documents.length} {documents.length === 1 ? 'file' : 'files'}
              </span>
            </div>

            {documents.length === 0 ? (
              <div className="mt-4 rounded-xl border border-dashed border-[#d9d3c6] px-4 py-10 text-center">
                <FileText className="mx-auto text-[#b0a58e]" size={30} />
                <p className="mt-3 text-sm text-[#64748b]">
                  Your selected documents will appear here.
                </p>
              </div>
            ) : (
              <ul className="mt-4 space-y-3">
                {documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#f4f0e6] text-[#0f305b]">
                        <FileText size={20} />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="break-all text-sm font-semibold text-[#183b62]">
                          {doc.file.name}
                        </p>

                        <p className="mt-1 text-xs text-[#718096]">
                          {(doc.file.size / (1024 * 1024)).toFixed(2)} MB ·{' '}
                          {doc.file.type || 'Unknown type'}
                        </p>

                        {doc.error && (
                          <p className="mt-2 text-xs text-red-700">{doc.error}</p>
                        )}

                        <span
                          className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                            doc.status === 'Parsed'
                              ? 'bg-emerald-50 text-emerald-700'
                              : doc.status === 'Processing'
                                ? 'bg-blue-50 text-blue-700'
                                : doc.status === 'Failed'
                                  ? 'bg-red-50 text-red-700'
                                  : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {doc.status === 'Processing' && (
                            <LoaderCircle className="animate-spin" size={13} />
                          )}
                          {doc.status === 'Parsed' && <CheckCircle2 size={13} />}
                          {doc.status === 'Failed' && <AlertCircle size={13} />}
                          {doc.status}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => removeDocument(doc.id)}
                        disabled={busy}
                        aria-label={`Remove ${doc.file.name}`}
                        className="rounded-lg p-2 text-[#8a6b59] hover:bg-red-50 hover:text-red-700 disabled:opacity-40"
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <p className="mt-4 text-xs leading-5 text-[#7a7b78]">
              Note: the current backend provides a single-file FIR understanding endpoint.
              DOCX files can be selected, but the existing endpoint does not document DOCX
              processing support.
            </p>

            <div className="mt-7 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-[#64748b]">
                {parsedCount} processed · {documents.filter((doc) => doc.status === 'Waiting').length} waiting · {failedCount} failed
              </p>

              <button
                type="button"
                onClick={processDocuments}
                disabled={
                  busy ||
                  documents.length === 0 ||
                  documents.every((doc) => doc.status === 'Parsed')
                }
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#c28b19] px-6 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#a97512] disabled:cursor-not-allowed disabled:bg-[#d7d0c0] disabled:text-[#777267] sm:w-auto"
              >
                {busy ? (
                  <LoaderCircle className="animate-spin" size={18} />
                ) : (
                  <RefreshCw size={17} />
                )}
                {busy ? 'Processing Documents…' : 'Process Selected Documents'}
              </button>
            </div>

            <div className="mt-7 border-t border-[#e6e0d4] pt-5">
              <Link
                href="/lawyer"
                className="text-sm font-semibold text-[#315b82] hover:text-[#c28b19]"
              >
                ← Back to Lawyer Dashboard
              </Link>
            </div>
          </section>
        </div>
      </main>
    </>
  )
}
