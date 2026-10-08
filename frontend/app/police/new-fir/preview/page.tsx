'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { policeAPI } from '@/lib/api'
import { generateFIRPdf, FIRFormData } from '@/lib/pdf/fir-generator'

type SignatureState = {
  status: 'NOT_VERIFIED' | 'VALID'
  signed_by: string
  signed_at: string
}

const makeApprovalId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `approval-${Date.now()}-${Math.random().toString(36).slice(2)}`

const toPdfBlob = (bytes: Uint8Array) => {
  const copy = new Uint8Array(bytes.byteLength)
  copy.set(bytes)
  return new Blob([copy.buffer], { type: 'application/pdf' })
}

export default function FIRPreviewPage() {
  const [form, setForm] = useState<FIRFormData | null>(null)
  const [pdfUrl, setPdfUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [otp, setOtp] = useState('')
  const [otpRequested, setOtpRequested] = useState(false)
  const [approving, setApproving] = useState(false)
  const [signature, setSignature] = useState<SignatureState | null>(null)

  useEffect(() => {
    let objectUrl = ''
    async function createPreview() {
      try {
        const saved = sessionStorage.getItem('lawaid_fir_draft')
        if (!saved) throw new Error('No FIR draft found.')

        const savedForm = JSON.parse(saved) as FIRFormData
        setForm(savedForm)
        setSignature({
          status: 'NOT_VERIFIED',
          signed_by: savedForm.officerName || 'Officer pending approval',
          signed_at: new Date().toLocaleString(),
        })
        const pdfBytes = await generateFIRPdf(savedForm)
        objectUrl = URL.createObjectURL(toPdfBlob(pdfBytes))
        setPdfUrl(objectUrl)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Failed to generate FIR preview.')
      } finally {
        setLoading(false)
      }
    }
    createPreview()
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [])

  const approvalId = () => {
    let id = sessionStorage.getItem('lawaid_fir_approval_id')
    if (!id) {
      id = makeApprovalId()
      sessionStorage.setItem('lawaid_fir_approval_id', id)
    }
    return id
  }

  async function requestOtp() {
    try {
      setError('')
      await policeAPI.requestFirApprovalOtp(approvalId())
      setOtpRequested(true)
    } catch (cause: any) {
      setError(cause?.response?.data?.detail || 'Unable to request approval OTP.')
    }
  }

  async function finalizeFir() {
    if (!form || !otp.trim()) return
    try {
      setApproving(true)
      setError('')
      const response = await policeAPI.approveFir({
        fir_draft_id: sessionStorage.getItem('lawaid_draft_id') || undefined,
        approval_id: approvalId(),
        station_code: form.policeStation || 'PS001',
        officer_name: form.officerName || form.officerRank || 'Station House Officer',
        summary: form.firContents || form.statement || '',
        fir_data: form,
        otp_code: otp.trim(),
      })
      const result = response.data
      const finalSignature = result.digital_signature as SignatureState
      if (!finalSignature || finalSignature.status !== 'VALID' || !result.pdf_base64) {
        throw new Error('The FIR was not finalized with a verifiable PDF.')
      }
      const binary = atob(result.pdf_base64)
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
      const finalUrl = URL.createObjectURL(toPdfBlob(bytes))
      if (pdfUrl) URL.revokeObjectURL(pdfUrl)
      setPdfUrl(finalUrl)
      setSignature(finalSignature)
      sessionStorage.removeItem('lawaid_fir_approval_id')
    } catch (cause: any) {
      setError(cause?.response?.data?.detail || cause?.message || 'Unable to finalize FIR.')
    } finally {
      setApproving(false)
    }
  }

  const isFinal = signature?.status === 'VALID'

  if (!loading && error && !form) {
    return (
      <div className="min-h-screen bg-[#f5f3ee]">
        <Navbar />
        <main className="mx-auto max-w-md px-4 py-20 text-center">
          <h1 className="text-2xl font-bold text-[#12355b]">FIR Draft Not Found</h1>
          <p className="mt-3 text-gray-600">{error}</p>
          <Link href="/police/new-fir?mode=resume" onClick={() => sessionStorage.setItem('lawaid_fir_mode', 'resume')} className="mt-6 inline-block rounded bg-[#12355b] px-5 py-2.5 text-sm font-semibold text-white">Back to FIR Drafting</Link>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f3ee]">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#12355b]">FIR Preview</h1>
            <p className="text-sm text-gray-600">Review the exact saved draft before final approval.</p>
          </div>
          <div className="flex gap-2">
            {!isFinal && <Link href="/police/new-fir?mode=resume" onClick={() => sessionStorage.setItem('lawaid_fir_mode', 'resume')} className="rounded bg-white px-4 py-2 text-sm font-medium text-[#12355b] shadow">Edit draft</Link>}
            {pdfUrl && <a href={pdfUrl} download={isFinal ? 'final-fir.pdf' : 'fir-preview.pdf'} className="rounded bg-[#12355b] px-4 py-2 text-sm font-medium text-white">Download PDF</a>}
            {pdfUrl && <button type="button" onClick={() => window.open(pdfUrl, '_blank')} className="rounded border border-[#12355b] bg-white px-4 py-2 text-sm font-medium text-[#12355b]">Print / Save PDF</button>}
          </div>
        </div>

        {signature && (
          <section className={`mb-5 rounded border p-4 ${isFinal ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-amber-50'}`}>
            <p className={`font-semibold ${isFinal ? 'text-green-800' : 'text-amber-800'}`}>{isFinal ? 'Signature Valid' : 'Signature Not Verified'}</p>
            <p className="text-sm text-gray-700">Digitally signed by {signature.signed_by}</p>
            <p className="text-sm text-gray-700">Date: {signature.signed_at}</p>
          </section>
        )}

        {!isFinal && form && (
          <section className="mb-5 rounded border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="font-semibold text-[#12355b]">Officer approval</h2>
            <p className="mt-1 text-sm text-gray-600">Request and enter the one-time approval code to finalize this FIR. The PDF remains unverified until the code is accepted.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={requestOtp} type="button" className="rounded bg-[#12355b] px-4 py-2 text-sm font-medium text-white">{otpRequested ? 'Resend OTP' : 'Request OTP'}</button>
              <input value={otp} onChange={(event) => setOtp(event.target.value)} inputMode="numeric" maxLength={6} placeholder="Enter 6-digit OTP" className="rounded border border-gray-300 px-3 py-2 text-sm" />
              <button onClick={finalizeFir} type="button" disabled={!otp.trim() || approving} className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{approving ? 'Finalizing…' : 'Finalize FIR'}</button>
            </div>
          </section>
        )}

        {error && <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {loading ? <p className="text-gray-600">Generating FIR preview…</p> : pdfUrl ? <iframe title="FIR PDF preview" src={pdfUrl} className="h-[75vh] w-full rounded border bg-white" /> : null}
      </main>
    </div>
  )
}
