'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { generateFIRPdf, FIRFormData } from '@/lib/pdf/fir-generator'

type FormData = {
  district: string
  policeStation: string
  year: string
  firNo: string
  firDate: string

  act1: string
  section1: string
  act2: string
  section2: string
  act3: string
  section3: string
  otherActs: string

  occurrenceDay: string
  occurrenceDate: string
  occurrenceTime: string
  informationDate: string
  informationTime: string
  gdEntry: string
  gdTime: string

  informationType: string

  placeDirection: string
  beatNo: string
  placeAddress: string
  outsidePoliceStation: string
  outsideDistrict: string

  complainantName: string
  fatherHusbandName: string
  dob: string
  nationality: string
  passportNo: string
  passportDate: string
  passportPlace: string
  occupation: string
  complainantAddress: string

  accusedDetails: string
  delayReason: string
  propertyDetails: string
  propertyValue: string
  inquestDetails: string
  firContents: string

  actionTaken: string
  officerRank: string
  officerName: string
  officerNo: string

  dispatchDate: string
  dispatchTime: string
}

export default function FIRPreviewPage() {
  const [form, setForm] = useState<FIRFormData | null>(null)
  const [pdfUrl, setPdfUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let objectUrl = ''

    async function createPdf() {
      try {
        const saved = sessionStorage.getItem('lawaid_fir_draft')

        if (!saved) {
          setError('No FIR draft found.')
          setLoading(false)
          return
        }

        const savedForm = JSON.parse(saved) as FIRFormData
        setForm(savedForm)

        const pdfBytes = await generateFIRPdf(savedForm)

        const pdfBuffer = new ArrayBuffer(pdfBytes.byteLength)
new Uint8Array(pdfBuffer).set(pdfBytes)

const blob = new Blob([pdfBuffer], {
  type: 'application/pdf',
})

        objectUrl = URL.createObjectURL(blob)
        setPdfUrl(objectUrl)
      } catch (err) {
        console.error('FIR PDF generation failed:', err)
        setError('Unable to generate the FIR PDF.')
      } finally {
        setLoading(false)
      }
    }

    createPdf()

    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [])

  const handlePrint = () => {
    if (pdfUrl) {
      window.open(pdfUrl, '_blank')
    }
  }

  if (loading) {
    return (
      <>
        <Navbar />

        <main className="min-h-screen bg-gray-200 flex items-center justify-center px-4">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-navy mx-auto mb-4" />

            <p className="text-gray-600">
              Generating FIR PDF...
            </p>
          </div>
        </main>
      </>
    )
  }

  if (error) {
    return (
      <>
        <Navbar />

        <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
          <div className="bg-white rounded-xl shadow-md p-8 text-center max-w-md">
            <h1 className="text-2xl font-bold text-navy">
              FIR Draft Not Found
            </h1>

            <p className="text-gray-600 mt-3">
              {error}
            </p>

            <Link
              href="/police/new-fir"
              className="inline-block mt-6 bg-navy text-white px-5 py-2.5 rounded-lg font-semibold"
            >
              Back to FIR Drafting
            </Link>
          </div>
        </main>
      </>
    )
  }

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-200 px-4 py-8">
        {/* Top controls */}
        <div className="print:hidden max-w-6xl mx-auto mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <Link
            href="/police/new-fir"
            className="border border-navy text-navy bg-white px-5 py-2.5 rounded-lg font-semibold"
          >
            ← Edit Draft
          </Link>

          <button
            type="button"
            onClick={handlePrint}
            disabled={!pdfUrl}
            className="bg-navy text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-50"
          >
            🖨 Print / Save as PDF
          </button>
        </div>

        {/* FIR PDF */}
        {pdfUrl && (
          <div className="max-w-6xl mx-auto bg-white rounded-xl shadow-xl overflow-hidden">
            <iframe
              src={pdfUrl}
              title="Generated FIR PDF"
              className="w-full h-[85vh]"
            />
          </div>
        )}
      </main>
    </>
  )
}