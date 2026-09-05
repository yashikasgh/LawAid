'use client'

import Link from 'next/link'
import { useState } from 'react'
import Navbar from '@/components/Navbar'
import { bnsAPI } from '@/lib/api'

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

const initialForm: FormData = {
  district: '',
  policeStation: '',
  year: '',
  firNo: '',
  firDate: '',

  act1: '',
  section1: '',
  act2: '',
  section2: '',
  act3: '',
  section3: '',
  otherActs: '',

  occurrenceDay: '',
  occurrenceDate: '',
  occurrenceTime: '',
  informationDate: '',
  informationTime: '',
  gdEntry: '',
  gdTime: '',

  informationType: 'Written',

  placeDirection: '',
  beatNo: '',
  placeAddress: '',
  outsidePoliceStation: '',
  outsideDistrict: '',

  complainantName: '',
  fatherHusbandName: '',
  dob: '',
  nationality: '',
  passportNo: '',
  passportDate: '',
  passportPlace: '',
  occupation: '',
  complainantAddress: '',

  accusedDetails: '',
  delayReason: '',
  propertyDetails: '',
  propertyValue: '',
  inquestDetails: '',
  firContents: '',

  actionTaken: '',
  officerRank: '',
  officerName: '',
  officerNo: '',

  dispatchDate: '',
  dispatchTime: '',
}

export default function NewFIRPage() {
  const [form, setForm] = useState<FormData>(initialForm)

  const [statement, setStatement] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)

  const [bnsQuery, setBnsQuery] = useState('')
  const [bnsResults, setBnsResults] = useState<
    {
      section: string
      title: string
      similarity: number
    }[]
  >([])

  const [bnsLoading, setBnsLoading] = useState(false)
  const [bnsError, setBnsError] = useState('')

  function updateField(
    field: keyof FormData,
    value: string
  ) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  async function searchBNS() {
    if (bnsQuery.trim().length < 3) {
      setBnsError(
        'Enter at least 3 characters to search.'
      )
      setBnsResults([])
      return
    }

    setBnsLoading(true)
    setBnsError('')

    try {
      const response = await bnsAPI.search(
        bnsQuery.trim()
      )

      const results =
        response.data?.results || []

      setBnsResults(results)

      if (results.length === 0) {
        setBnsError(
          'No matching BNS sections found.'
        )
      }
    } catch {
      setBnsResults([])
      setBnsError(
        'Unable to search BNS sections.'
      )
    } finally {
      setBnsLoading(false)
    }
  }

  function useBNSSection(
    section: string,
    title: string
  ) {
    if (!form.act1) {
      setForm((prev) => ({
        ...prev,
        act1:
          'Bharatiya Nyaya Sanhita, 2023',
        section1:
          `${section} - ${title}`,
      }))
      return
    }

    if (!form.act2) {
      setForm((prev) => ({
        ...prev,
        act2:
          'Bharatiya Nyaya Sanhita, 2023',
        section2:
          `${section} - ${title}`,
      }))
      return
    }

    if (!form.act3) {
      setForm((prev) => ({
        ...prev,
        act3:
          'Bharatiya Nyaya Sanhita, 2023',
        section3:
          `${section} - ${title}`,
      }))
      return
    }

    setForm((prev) => ({
      ...prev,
      otherActs:
        prev.otherActs
          ? `${prev.otherActs}\nBNS ${section} - ${title}`
          : `BNS ${section} - ${title}`,
    }))
  }

  function generatePreview() {
    sessionStorage.setItem(
      'lawaid_fir_draft',
      JSON.stringify({
        ...form,
        statement,
      })
    )

    window.location.href =
      '/police/new-fir/preview'
  }

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-100 px-4 py-8">
        <div className="max-w-6xl mx-auto">

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold text-navy">
                Create FIR Draft
              </h1>

              <p className="mt-2 text-gray-600">
                Prepare a First Information Report using the official IF1 format.
              </p>
            </div>

            <Link
              href="/police"
              className="border border-navy text-navy px-5 py-2.5 rounded-lg font-semibold hover:bg-gray-100"
            >
              ← Back to Dashboard
            </Link>
          </div>

          {/* Draft Status */}
          <div className="bg-white rounded-xl shadow-sm p-5 mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <p className="text-sm text-gray-500">
                Draft Status
              </p>

              <p className="font-semibold text-navy">
                New FIR Draft
              </p>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                disabled
                className="border border-gray-300 text-gray-400 px-5 py-2 rounded-lg font-semibold cursor-not-allowed"
              >
                Save Draft
              </button>

              <button
                type="button"
                onClick={generatePreview}
                className="bg-navy text-white px-5 py-2 rounded-lg font-semibold hover:opacity-90"
              >
                Generate Draft
              </button>
            </div>
          </div>

          {/* Statement Input */}
          <section className="bg-white rounded-xl shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-navy">
                  Statement Input
                </h2>

                <p className="text-sm text-gray-500 mt-1">
                  Enter the incident statement to assist FIR drafting.
                </p>
              </div>

              <Link
                href="/bns-search"
                className="text-sm font-semibold text-navy hover:underline"
              >
                Search BNS Sections →
              </Link>
            </div>

            <textarea
              rows={6}
              value={statement}
              onChange={(e) =>
                setStatement(e.target.value)
              }
              placeholder="Enter the complainant/informant statement or incident description..."
              className="w-full border border-gray-300 rounded-lg p-4 resize-y focus:outline-none focus:ring-2 focus:ring-navy"
            />

            <div className="mt-4 flex flex-col sm:flex-row gap-3">

              <label className="border border-gray-300 rounded-lg px-4 py-2.5 cursor-pointer text-sm font-medium text-gray-700">
                🎙 Upload Recorded Statement

                <input
                  type="file"
                  accept="audio/*"
                  className="hidden"
                  onChange={(e) =>
                    setAudioFile(
                      e.target.files?.[0] || null
                    )
                  }
                />
              </label>

              {audioFile && (
                <div className="flex items-center text-sm text-gray-600">
                  {audioFile.name}
                </div>
              )}

              <button
                type="button"
                className="bg-gray-100 text-navy px-5 py-2.5 rounded-lg font-semibold"
              >
                Extract Information
              </button>

            </div>
          </section>

          {/* Section 1 */}
          <section className="form-section">
            <SectionTitle
              number="1"
              title="FIR Identification"
            />

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

              <Input
                label="District"
                value={form.district}
                onChange={(v) =>
                  updateField(
                    'district',
                    v
                  )
                }
              />

              <Input
                label="Police Station"
                value={form.policeStation}
                onChange={(v) =>
                  updateField(
                    'policeStation',
                    v
                  )
                }
              />

              <Input
                label="Year"
                value={form.year}
                onChange={(v) =>
                  updateField(
                    'year',
                    v
                  )
                }
              />

              <Input
                label="F.I.R. No."
                value={form.firNo}
                onChange={(v) =>
                  updateField(
                    'firNo',
                    v
                  )
                }
              />

            </div>

            <div className="mt-4 max-w-xs">
              <Input
                label="Date"
                type="date"
                value={form.firDate}
                onChange={(v) =>
                  updateField(
                    'firDate',
                    v
                  )
                }
              />
            </div>
          </section>

          {/* Section 2 */}
          <section className="form-section">
            <SectionTitle
              number="2"
              title="Act(s) and Section(s)"
            />

            <div className="space-y-4">

              <ActRow
                number="1"
                act={form.act1}
                section={form.section1}
                onActChange={(v) =>
                  updateField(
                    'act1',
                    v
                  )
                }
                onSectionChange={(v) =>
                  updateField(
                    'section1',
                    v
                  )
                }
              />

              <ActRow
                number="2"
                act={form.act2}
                section={form.section2}
                onActChange={(v) =>
                  updateField(
                    'act2',
                    v
                  )
                }
                onSectionChange={(v) =>
                  updateField(
                    'section2',
                    v
                  )
                }
              />

              <ActRow
                number="3"
                act={form.act3}
                section={form.section3}
                onActChange={(v) =>
                  updateField(
                    'act3',
                    v
                  )
                }
                onSectionChange={(v) =>
                  updateField(
                    'section3',
                    v
                  )
                }
              />

              <Input
                label="Other Acts & Sections"
                value={form.otherActs}
                onChange={(v) =>
                  updateField(
                    'otherActs',
                    v
                  )
                }
              />

            </div>

            {/* BNS Search */}
            <div className="mt-6 rounded-lg bg-gray-50 p-5">

              <h3 className="font-semibold text-navy">
                BNS Section Search
              </h3>

              <p className="text-sm text-gray-500 mt-1">
                Search relevant BNS sections while preparing the FIR draft.
              </p>

              <div className="mt-4 flex flex-col sm:flex-row gap-3">

                <input
                  type="text"
                  value={bnsQuery}
                  onChange={(e) =>
                    setBnsQuery(
                      e.target.value
                    )
                  }
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      searchBNS()
                    }
                  }}
                  placeholder="Example: cheating, intimidation..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-navy"
                />

                <button
                  type="button"
                  onClick={searchBNS}
                  disabled={bnsLoading}
                  className="bg-navy text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-50"
                >
                  {bnsLoading
                    ? 'Searching...'
                    : 'Search BNS'}
                </button>

              </div>

              {bnsError && (
                <p className="mt-3 text-sm text-red-600">
                  {bnsError}
                </p>
              )}

              {bnsResults.length > 0 && (
                <div className="mt-4 space-y-3">

                  {bnsResults.map(
                    (result) => (
                      <div
                        key={`${result.section}-${result.title}`}
                        className="bg-white border border-gray-200 rounded-lg p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                      >

                        <div>
                          <p className="font-semibold text-navy">
                            Section {result.section}
                          </p>

                          <p className="text-sm text-gray-700">
                            {result.title}
                          </p>

                          <p className="text-xs text-gray-500 mt-1">
                            Similarity: {result.similarity}
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() =>
                            useBNSSection(
                              result.section,
                              result.title
                            )
                          }
                          className="border border-navy text-navy px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-100"
                        >
                          Use Section
                        </button>

                      </div>
                    )
                  )}

                </div>
              )}

            </div>
          </section>

          {/* Section 3 */}
          <section className="form-section">
            <SectionTitle
              number="3"
              title="Occurrence of Offence"
            />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              <Input
                label="Day"
                value={form.occurrenceDay}
                onChange={(v) =>
                  updateField(
                    'occurrenceDay',
                    v
                  )
                }
              />

              <Input
                label="Date"
                type="date"
                value={form.occurrenceDate}
                onChange={(v) =>
                  updateField(
                    'occurrenceDate',
                    v
                  )
                }
              />

              <Input
                label="Time"
                type="time"
                value={form.occurrenceTime}
                onChange={(v) =>
                  updateField(
                    'occurrenceTime',
                    v
                  )
                }
              />

            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">

              <Input
                label="Information Received at P.S. — Date"
                type="date"
                value={form.informationDate}
                onChange={(v) =>
                  updateField(
                    'informationDate',
                    v
                  )
                }
              />

              <Input
                label="Information Received at P.S. — Time"
                type="time"
                value={form.informationTime}
                onChange={(v) =>
                  updateField(
                    'informationTime',
                    v
                  )
                }
              />

            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">

              <Input
                label="General Diary Reference — Entry No(s)"
                value={form.gdEntry}
                onChange={(v) =>
                  updateField(
                    'gdEntry',
                    v
                  )
                }
              />

              <Input
                label="General Diary Reference — Time"
                type="time"
                value={form.gdTime}
                onChange={(v) =>
                  updateField(
                    'gdTime',
                    v
                  )
                }
              />

            </div>
          </section>

          {/* Section 4 */}
          <section className="form-section">
            <SectionTitle
              number="4"
              title="Type of Information"
            />

            <div className="flex gap-6">

              <Radio
                label="Written"
                checked={
                  form.informationType ===
                  'Written'
                }
                onChange={() =>
                  updateField(
                    'informationType',
                    'Written'
                  )
                }
              />

              <Radio
                label="Oral"
                checked={
                  form.informationType ===
                  'Oral'
                }
                onChange={() =>
                  updateField(
                    'informationType',
                    'Oral'
                  )
                }
              />

            </div>
          </section>

          {/* Section 5 */}
          <section className="form-section">
            <SectionTitle
              number="5"
              title="Place of Occurrence"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <Input
                label="Direction and Distance from P.S."
                value={form.placeDirection}
                onChange={(v) =>
                  updateField(
                    'placeDirection',
                    v
                  )
                }
              />

              <Input
                label="Beat No."
                value={form.beatNo}
                onChange={(v) =>
                  updateField(
                    'beatNo',
                    v
                  )
                }
              />

            </div>

            <div className="mt-4">
              <TextArea
                label="Address"
                value={form.placeAddress}
                onChange={(v) =>
                  updateField(
                    'placeAddress',
                    v
                  )
                }
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">

              <Input
                label="Other Police Station (if outside limits)"
                value={form.outsidePoliceStation}
                onChange={(v) =>
                  updateField(
                    'outsidePoliceStation',
                    v
                  )
                }
              />

              <Input
                label="District"
                value={form.outsideDistrict}
                onChange={(v) =>
                  updateField(
                    'outsideDistrict',
                    v
                  )
                }
              />

            </div>
          </section>

          {/* Section 6 */}
          <section className="form-section">
            <SectionTitle
              number="6"
              title="Complainant / Informant"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <Input
                label="Name"
                value={form.complainantName}
                onChange={(v) =>
                  updateField(
                    'complainantName',
                    v
                  )
                }
              />

              <Input
                label="Father's / Husband's Name"
                value={form.fatherHusbandName}
                onChange={(v) =>
                  updateField(
                    'fatherHusbandName',
                    v
                  )
                }
              />

              <Input
                label="Date / Year of Birth"
                value={form.dob}
                onChange={(v) =>
                  updateField(
                    'dob',
                    v
                  )
                }
              />

              <Input
                label="Nationality"
                value={form.nationality}
                onChange={(v) =>
                  updateField(
                    'nationality',
                    v
                  )
                }
              />

              <Input
                label="Passport No."
                value={form.passportNo}
                onChange={(v) =>
                  updateField(
                    'passportNo',
                    v
                  )
                }
              />

              <Input
                label="Passport Date of Issue"
                type="date"
                value={form.passportDate}
                onChange={(v) =>
                  updateField(
                    'passportDate',
                    v
                  )
                }
              />

              <Input
                label="Passport Place of Issue"
                value={form.passportPlace}
                onChange={(v) =>
                  updateField(
                    'passportPlace',
                    v
                  )
                }
              />

              <Input
                label="Occupation"
                value={form.occupation}
                onChange={(v) =>
                  updateField(
                    'occupation',
                    v
                  )
                }
              />

            </div>

            <div className="mt-4">
              <TextArea
                label="Address"
                value={form.complainantAddress}
                onChange={(v) =>
                  updateField(
                    'complainantAddress',
                    v
                  )
                }
              />
            </div>
          </section>

          {/* Section 7 */}
          <section className="form-section">
            <SectionTitle
              number="7"
              title="Known / Suspected / Unknown / Accused Details"
            />

            <TextArea
              label="Full particulars"
              rows={7}
              value={form.accusedDetails}
              onChange={(v) =>
                updateField(
                  'accusedDetails',
                  v
                )
              }
              placeholder="Enter details of the known, suspected or unknown accused..."
            />

            <p className="text-xs text-gray-500 mt-2">
              Attach a separate sheet if necessary.
            </p>
          </section>

          {/* Section 8 */}
          <section className="form-section">
            <SectionTitle
              number="8"
              title="Reason for Delay in Reporting"
            />

            <TextArea
              label="Reason for delay"
              rows={5}
              value={form.delayReason}
              onChange={(v) =>
                updateField(
                  'delayReason',
                  v
                )
              }
            />
          </section>

          {/* Section 9 */}
          <section className="form-section">
            <SectionTitle
              number="9"
              title="Particulars of Property Stolen / Involved"
            />

            <TextArea
              label="Property details"
              rows={6}
              value={form.propertyDetails}
              onChange={(v) =>
                updateField(
                  'propertyDetails',
                  v
                )
              }
              placeholder="Describe the property stolen or otherwise involved..."
            />

            <p className="text-xs text-gray-500 mt-2">
              Attach a separate sheet if necessary.
            </p>
          </section>

          {/* Section 10 */}
          <section className="form-section">
            <SectionTitle
              number="10"
              title="Total Value of Property Stolen / Involved"
            />

            <Input
              label="Total Value"
              placeholder="₹"
              value={form.propertyValue}
              onChange={(v) =>
                updateField(
                  'propertyValue',
                  v
                )
              }
            />
          </section>

          {/* Section 11 */}
          <section className="form-section">
            <SectionTitle
              number="11"
              title="Inquest Report / U.D. Case No."
            />

            <TextArea
              label="Details, if any"
              rows={4}
              value={form.inquestDetails}
              onChange={(v) =>
                updateField(
                  'inquestDetails',
                  v
                )
              }
            />
          </section>

          {/* Section 12 */}
          <section className="form-section">
            <SectionTitle
              number="12"
              title="F.I.R. Contents"
            />

            <TextArea
              label="F.I.R. Contents"
              rows={12}
              value={form.firContents}
              onChange={(v) =>
                updateField(
                  'firContents',
                  v
                )
              }
              placeholder="Enter or generate the detailed FIR contents..."
            />

            <p className="text-xs text-gray-500 mt-2">
              Attach separate sheets if required.
            </p>
          </section>

          {/* Section 13 */}
          <section className="form-section">
            <SectionTitle
              number="13"
              title="Action Taken"
            />

            <TextArea
              label="Action Taken"
              rows={7}
              value={form.actionTaken}
              onChange={(v) =>
                updateField(
                  'actionTaken',
                  v
                )
              }
              placeholder="Enter the information required for this section of the official FIR format..."
            />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">

              <Input
                label="Rank"
                value={form.officerRank}
                onChange={(v) =>
                  updateField(
                    'officerRank',
                    v
                  )
                }
              />

              <Input
                label="Officer Name"
                value={form.officerName}
                onChange={(v) =>
                  updateField(
                    'officerName',
                    v
                  )
                }
              />

              <Input
                label="Officer No."
                value={form.officerNo}
                onChange={(v) =>
                  updateField(
                    'officerNo',
                    v
                  )
                }
              />

            </div>
          </section>

          {/* Section 14 */}
          <section className="form-section">
            <SectionTitle
              number="14"
              title="Complainant / Informant Signature"
            />

            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500">
              Signature / Thumb-impression area
            </div>
          </section>

          {/* Section 15 */}
          <section className="form-section">
            <SectionTitle
              number="15"
              title="Date & Time of Despatch to Court"
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <Input
                label="Date"
                type="date"
                value={form.dispatchDate}
                onChange={(v) =>
                  updateField(
                    'dispatchDate',
                    v
                  )
                }
              />

              <Input
                label="Time"
                type="time"
                value={form.dispatchTime}
                onChange={(v) =>
                  updateField(
                    'dispatchTime',
                    v
                  )
                }
              />

            </div>
          </section>

          {/* Bottom Actions */}
          <div className="bg-white rounded-xl shadow-sm p-6 mt-6 mb-10">

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

              <div>
                <p className="font-semibold text-navy">
                  FIR Draft
                </p>

                <p className="text-sm text-gray-500">
                  Review the information before generating the draft.
                </p>
              </div>

              <div className="flex gap-3">

                <button
                  type="button"
                  disabled
                  className="border border-gray-300 text-gray-400 px-6 py-3 rounded-lg font-semibold cursor-not-allowed"
                >
                  Save Draft
                </button>

                <button
                  type="button"
                  onClick={generatePreview}
                  className="bg-navy text-white px-6 py-3 rounded-lg font-semibold hover:opacity-90"
                >
                  Generate FIR Draft
                </button>

              </div>
            </div>
          </div>

        </div>
      </main>
    </>
  )
}

function SectionTitle({
  number,
  title,
}: {
  number: string
  title: string
}) {
  return (
    <div className="flex items-center gap-3 mb-5 pb-3 border-b">

      <div className="w-9 h-9 rounded-full bg-navy text-white flex items-center justify-center font-bold">
        {number}
      </div>

      <h2 className="text-xl font-bold text-navy">
        {title}
      </h2>

    </div>
  )
}

function Input({
  label,
  type = 'text',
  placeholder = '',
  value,
  onChange,
}: {
  label: string
  type?: string
  placeholder?: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>

      <label className="block text-sm font-semibold text-gray-700 mb-2">
        {label}
      </label>

      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(e.target.value)
        }
        className="w-full border border-gray-300 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-navy"
      />

    </div>
  )
}

function TextArea({
  label,
  rows = 5,
  placeholder = '',
  value,
  onChange,
}: {
  label: string
  rows?: number
  placeholder?: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div>

      <label className="block text-sm font-semibold text-gray-700 mb-2">
        {label}
      </label>

      <textarea
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(e.target.value)
        }
        className="w-full border border-gray-300 rounded-lg px-3 py-3 resize-y focus:outline-none focus:ring-2 focus:ring-navy"
      />

    </div>
  )
}

function ActRow({
  number,
  act,
  section,
  onActChange,
  onSectionChange,
}: {
  number: string
  act: string
  section: string
  onActChange: (value: string) => void
  onSectionChange: (value: string) => void
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

      <Input
        label={`Act ${number}`}
        value={act}
        onChange={onActChange}
      />

      <Input
        label={`Section(s) ${number}`}
        value={section}
        onChange={onSectionChange}
      />

    </div>
  )
}

function Radio({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: () => void
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">

      <input
        type="radio"
        checked={checked}
        onChange={onChange}
      />

      {label}

    </label>
  )
}