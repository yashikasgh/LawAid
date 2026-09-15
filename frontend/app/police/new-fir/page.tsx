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

      <main className="relative min-h-screen overflow-hidden bg-[#f8f6f1]">

        {/* Background */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-fixed"
          style={{
            backgroundImage:
              "url('/images/lawaid-feature-bg.png')",
          }}
        />

        {/* Light editorial overlay */}
        <div className="absolute inset-0 bg-[#f8f6f1]/10" />

        <div className="relative z-10 px-5 md:px-8 py-10">
          <div className="max-w-6xl mx-auto">

            {/* Header */}
            <div className="mb-8">
              <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">

                <div>
                  <p className="text-xs font-semibold tracking-[0.25em] uppercase text-white mb-3">
                    POLICE PORTAL · FIR DRAFTING
                  </p>

                  <h1 className="font-serif text-4xl md:text-5xl font-bold text-[#cc8427] leading-tight">
                    Create FIR Draft
                  </h1>

                  <p className="mt-3 text-[#dca45a] text-base md:text-lg max-w-2xl">
                    Prepare a First Information Report using
                    the official IF1 format.
                  </p>
                </div>

                <Link
                  href="/police"
                  className="inline-flex items-center justify-center gap-2 border border-[#12335B] bg-white/70 text-[#12335B] px-5 py-3 rounded-lg font-semibold hover:bg-white transition shadow-sm"
                >
                  <svg
                    width="17"
                    height="17"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M19 12H5" />
                    <path d="M12 19l-7-7 7-7" />
                  </svg>

                  Back to Dashboard
                </Link>

              </div>

              <div className="mt-8 h-px bg-[#cbbf9f]" />
            </div>

            {/* Draft Status */}
            <div className="bg-white/75 backdrop-blur-sm border border-[#d9d4ca] rounded-2xl shadow-lg p-6 mb-6">

              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

                <div className="flex items-center gap-4">
                  <div className="w-11 h-11 rounded-full bg-[#f3ead7] flex items-center justify-center">
                    <svg
                      width="21"
                      height="21"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#b98528"
                      strokeWidth="1.8"
                    >
                      <path d="M6 3h9l3 3v15H6z" />
                      <path d="M15 3v4h4" />
                      <path d="M9 12h6" />
                      <path d="M9 16h6" />
                    </svg>
                  </div>

                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#7890a8]">
                      Draft Status
                    </p>

                    <p className="mt-1 font-serif text-xl font-bold text-[#12335B]">
                      New FIR Draft
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">

                  <button
                    type="button"
                    disabled
                    className="border border-[#d5d9df] bg-white/60 text-[#9aa8b8] px-5 py-2.5 rounded-lg font-semibold cursor-not-allowed"
                  >
                    Save Draft
                  </button>

                  <button
                    type="button"
                    onClick={generatePreview}
                    className="bg-[#b98528] text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-[#9f7020] transition shadow-sm"
                  >
                    Generate Draft
                  </button>

                </div>
              </div>
            </div>

            {/* Statement Input */}
            <section className="bg-white/75 backdrop-blur-sm border border-[#d9d4ca] rounded-2xl shadow-lg p-6 md:p-7 mb-6">

              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">

                <div>
                  <p className="text-[11px] font-semibold tracking-[0.2em] uppercase text-[#b98528] mb-2">
                    INCIDENT INFORMATION
                  </p>

                  <h2 className="font-serif text-2xl font-bold text-[#12335B]">
                    Statement Input
                  </h2>

                  <p className="text-sm text-[#56718f] mt-1">
                    Enter the incident statement to assist FIR drafting.
                  </p>
                </div>

                <Link
                  href="/bns-search"
                  className="text-sm font-semibold text-[#12335B] hover:text-[#b98528] transition"
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
                className="w-full bg-white/80 border border-[#cfd3d8] rounded-xl p-4 text-[#315b82] placeholder:text-[#8aa0b5] resize-y focus:outline-none focus:ring-2 focus:ring-[#b98528]/30 focus:border-[#b98528] transition"
              />

              <div className="mt-4 flex flex-col sm:flex-row gap-3">

                <label className="inline-flex items-center justify-center gap-2 border border-[#cfd3d8] bg-white/70 rounded-lg px-4 py-2.5 cursor-pointer text-sm font-medium text-[#12335B] hover:bg-white transition">

                  <svg
                    width="17"
                    height="17"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#b98528"
                    strokeWidth="1.8"
                  >
                    <path d="M12 2v10" />
                    <path d="M8 6a4 4 0 0 1 8 0v6a4 4 0 0 1-8 0z" />
                    <path d="M5 12a7 7 0 0 0 14 0" />
                    <path d="M12 19v3" />
                    <path d="M8 22h8" />
                  </svg>

                  Upload Recorded Statement

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
                  <div className="flex items-center text-sm text-[#56718f] px-2">
                    {audioFile.name}
                  </div>
                )}

                <button
                  type="button"
                  className="bg-[#eef0f2] text-[#12335B] px-5 py-2.5 rounded-lg font-semibold hover:bg-[#e3e6e9] transition"
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
              <div className="mt-7 rounded-xl bg-[#f8f6f1]/80 border border-[#ddd7cb] p-5">

                <div className="flex items-start gap-3">

                  <div className="w-9 h-9 shrink-0 rounded-lg bg-[#f1e6cf] flex items-center justify-center">
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#b98528"
                      strokeWidth="1.8"
                    >
                      <circle
                        cx="11"
                        cy="11"
                        r="6"
                      />
                      <path d="m16 16 5 5" />
                    </svg>
                  </div>

                  <div>
                    <h3 className="font-serif text-lg font-bold text-[#12335B]">
                      BNS Section Search
                    </h3>

                    <p className="text-sm text-[#56718f] mt-1">
                      Search relevant BNS sections while preparing the FIR draft.
                    </p>
                  </div>

                </div>

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
                    className="flex-1 bg-white border border-[#cfd3d8] rounded-lg px-4 py-2.5 text-[#315b82] placeholder:text-[#8aa0b5] focus:outline-none focus:ring-2 focus:ring-[#b98528]/30 focus:border-[#b98528]"
                  />

                  <button
                    type="button"
                    onClick={searchBNS}
                    disabled={bnsLoading}
                    className="bg-[#12335B] text-white px-5 py-2.5 rounded-lg font-semibold hover:bg-[#0d2949] transition disabled:opacity-50"
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
                          className="bg-white/90 border border-[#d9d4ca] rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                        >

                          <div>
                            <p className="text-sm font-semibold text-[#b98528]">
                              Section {result.section}
                            </p>

                            <p className="text-sm text-[#12335B] font-medium mt-1">
                              {result.title}
                            </p>

                            <p className="text-xs text-[#7890a8] mt-1">
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
                            className="border border-[#12335B] text-[#12335B] px-4 py-2 rounded-lg text-sm font-semibold hover:bg-[#12335B] hover:text-white transition"
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

              <div className="flex flex-wrap gap-4">

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

              <p className="text-xs text-[#7890a8] mt-2">
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

              <p className="text-xs text-[#7890a8] mt-2">
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

              <p className="text-xs text-[#7890a8] mt-2">
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

              <div className="border-2 border-dashed border-[#d4cec1] rounded-xl bg-[#faf9f6]/70 p-10 text-center text-[#7890a8]">

                <svg
                  className="mx-auto mb-3"
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#b98528"
                  strokeWidth="1.6"
                >
                  <path d="M4 20c3-4 6-5 9-8l5-5a2 2 0 0 0-3-3l-5 5c-3 3-4 6-8 9" />
                  <path d="M14 5l5 5" />
                  <path d="M3 21h18" />
                </svg>

                <p className="text-sm font-medium">
                  Signature / Thumb-impression area
                </p>

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
            <div className="bg-white/75 backdrop-blur-sm border border-[#d9d4ca] rounded-2xl shadow-lg p-6 mt-6 mb-10">

              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5">

                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] font-semibold text-[#b98528]">
                    FINAL STEP
                  </p>

                  <p className="font-serif text-xl font-bold text-[#12335B] mt-1">
                    FIR Draft
                  </p>

                  <p className="text-sm text-[#56718f] mt-1">
                    Review the information before generating the draft.
                  </p>
                </div>

                <div className="flex gap-3">

                  <button
                    type="button"
                    disabled
                    className="border border-[#d5d9df] bg-white/60 text-[#9aa8b8] px-6 py-3 rounded-lg font-semibold cursor-not-allowed"
                  >
                    Save Draft
                  </button>

                  <button
                    type="button"
                    onClick={generatePreview}
                    className="bg-[#b98528] text-white px-6 py-3 rounded-lg font-semibold hover:bg-[#9f7020] transition shadow-sm"
                  >
                    Generate FIR Draft
                  </button>

                </div>

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
    <div className="flex items-center gap-4 mb-6 pb-4 border-b border-[#d8d1c5]">

      <div className="w-10 h-10 shrink-0 rounded-full bg-[#12335B] text-white flex items-center justify-center font-bold shadow-sm">
        {number}
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.18em] text-[#b98528] font-semibold mb-0.5">
          FIR SECTION
        </p>

        <h2 className="font-serif text-xl md:text-2xl font-bold text-[#12335B]">
          {title}
        </h2>
      </div>

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
      <label className="block text-sm font-semibold text-[#315b82] mb-2">
        {label}
      </label>

      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(e.target.value)
        }
        className="w-full bg-white/80 border border-[#cfd3d8] rounded-lg px-3 py-2.5 text-[#315b82] placeholder:text-[#8aa0b5] focus:outline-none focus:ring-2 focus:ring-[#b98528]/30 focus:border-[#b98528] transition"
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
      <label className="block text-sm font-semibold text-[#315b82] mb-2">
        {label}
      </label>

      <textarea
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(e.target.value)
        }
        className="w-full bg-white/80 border border-[#cfd3d8] rounded-lg px-3 py-3 text-[#315b82] placeholder:text-[#8aa0b5] resize-y focus:outline-none focus:ring-2 focus:ring-[#b98528]/30 focus:border-[#b98528] transition"
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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-[#faf9f6]/70 border border-[#e0dbd1]">

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
    <label
      className={`flex items-center gap-3 cursor-pointer border rounded-lg px-5 py-3 transition ${
        checked
          ? 'border-[#b98528] bg-[#f5eddc] text-[#12335B]'
          : 'border-[#d3d7dc] bg-white/70 text-[#56718f] hover:bg-white'
      }`}
    >

      <input
        type="radio"
        checked={checked}
        onChange={onChange}
        className="accent-[#b98528]"
      />

      <span className="text-sm font-semibold">
        {label}
      </span>

    </label>
  )
}