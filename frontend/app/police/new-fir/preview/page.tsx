'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'

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
  const [form, setForm] = useState<FormData | null>(null)

  useEffect(() => {
    const saved = sessionStorage.getItem('lawaid_fir_draft')

    if (saved) {
      try {
        setForm(JSON.parse(saved))
      } catch {
        setForm(null)
      }
    }
  }, [])

  if (!form) {
    return (
      <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
        <div className="bg-white rounded-xl shadow-md p-8 text-center max-w-md">
          <h1 className="text-2xl font-bold text-navy">
            FIR Draft Not Found
          </h1>

          <p className="text-gray-600 mt-3">
            Please return to the FIR drafting page and generate the draft again.
          </p>

          <Link
            href="/police/new-fir"
            className="inline-block mt-6 bg-navy text-white px-5 py-2.5 rounded-lg font-semibold"
          >
            Back to FIR Drafting
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-200 px-4 py-8">

      {/* Top controls */}
      <div className="print:hidden max-w-5xl mx-auto mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <Link
          href="/police/new-fir"
          className="border border-navy text-navy bg-white px-5 py-2.5 rounded-lg font-semibold"
        >
          ← Edit Draft
        </Link>

        <button
          type="button"
          onClick={() => window.print()}
          className="bg-navy text-white px-5 py-2.5 rounded-lg font-semibold"
        >
          🖨 Print / Save as PDF
        </button>
      </div>

      {/* FIR document */}
      <article className="fir-document max-w-5xl mx-auto bg-white shadow-xl">

        {/* Document header */}
        <header className="border-b-2 border-black p-8 text-center">
          <h1 className="text-2xl font-bold uppercase tracking-wide">
            FIRST INFORMATION REPORT
          </h1>

          <p className="mt-2 font-semibold">
            Under Section 154 Cr.P.C.
          </p>

          <p className="mt-4 text-sm">
            Generated FIR Draft — LawAid
          </p>
        </header>

        {/* Section 1 */}
        <FIRSection number="1" title="FIR Identification">
          <InfoGrid
            items={[
              ['District', form.district],
              ['Police Station', form.policeStation],
              ['Year', form.year],
              ['F.I.R. No.', form.firNo],
              ['Date', form.firDate],
            ]}
          />
        </FIRSection>

        {/* Section 2 */}
        <FIRSection number="2" title="Acts and Sections">
          <Table
            headers={['Act', 'Section(s)']}
            rows={[
              [form.act1, form.section1],
              [form.act2, form.section2],
              [form.act3, form.section3],
            ]}
          />

          <div className="mt-4">
            <Field
              label="Other Acts & Sections"
              value={form.otherActs}
            />
          </div>
        </FIRSection>

        {/* Section 3 */}
        <FIRSection number="3" title="Occurrence of Offence">
          <InfoGrid
            items={[
              ['Day', form.occurrenceDay],
              ['Date', form.occurrenceDate],
              ['Time', form.occurrenceTime],
              [
                'Information Received at P.S. — Date',
                form.informationDate,
              ],
              [
                'Information Received at P.S. — Time',
                form.informationTime,
              ],
              [
                'General Diary Reference — Entry No(s)',
                form.gdEntry,
              ],
              [
                'General Diary Reference — Time',
                form.gdTime,
              ],
            ]}
          />
        </FIRSection>

        {/* Section 4 */}
        <FIRSection number="4" title="Type of Information">
          <Field
            label="Type of Information"
            value={form.informationType}
          />
        </FIRSection>

        {/* Section 5 */}
        <FIRSection number="5" title="Place of Occurrence">
          <InfoGrid
            items={[
              [
                'Direction and Distance from P.S.',
                form.placeDirection,
              ],
              ['Beat No.', form.beatNo],
              [
                'Other Police Station',
                form.outsidePoliceStation,
              ],
              ['District', form.outsideDistrict],
            ]}
          />

          <div className="mt-4">
            <Field
              label="Address"
              value={form.placeAddress}
              multiline
            />
          </div>
        </FIRSection>

        {/* Section 6 */}
        <FIRSection number="6" title="Complainant / Informant">
          <InfoGrid
            items={[
              ['Name', form.complainantName],
              [
                "Father's / Husband's Name",
                form.fatherHusbandName,
              ],
              ['Date / Year of Birth', form.dob],
              ['Nationality', form.nationality],
              ['Passport No.', form.passportNo],
              ['Passport Date of Issue', form.passportDate],
              ['Passport Place of Issue', form.passportPlace],
              ['Occupation', form.occupation],
            ]}
          />

          <div className="mt-4">
            <Field
              label="Address"
              value={form.complainantAddress}
              multiline
            />
          </div>
        </FIRSection>

        {/* Section 7 */}
        <FIRSection
          number="7"
          title="Known / Suspected / Unknown / Accused Details"
        >
          <Field
            label="Full Particulars"
            value={form.accusedDetails}
            multiline
            large
          />
        </FIRSection>

        {/* Section 8 */}
        <FIRSection
          number="8"
          title="Reason for Delay in Reporting"
        >
          <Field
            label="Reason for Delay"
            value={form.delayReason}
            multiline
          />
        </FIRSection>

        {/* Section 9 */}
        <FIRSection
          number="9"
          title="Particulars of Property Stolen / Involved"
        >
          <Field
            label="Property Details"
            value={form.propertyDetails}
            multiline
            large
          />
        </FIRSection>

        {/* Section 10 */}
        <FIRSection
          number="10"
          title="Total Value of Property Stolen / Involved"
        >
          <Field
            label="Total Value"
            value={form.propertyValue}
          />
        </FIRSection>

        {/* Section 11 */}
        <FIRSection
          number="11"
          title="Inquest Report / U.D. Case No."
        >
          <Field
            label="Details, if any"
            value={form.inquestDetails}
            multiline
          />
        </FIRSection>

        {/* Section 12 */}
        <FIRSection
          number="12"
          title="F.I.R. Contents"
        >
          <Field
            label="F.I.R. Contents"
            value={form.firContents}
            multiline
            large
          />
        </FIRSection>

        {/* Section 13 */}
        <FIRSection
          number="13"
          title="Action Taken"
        >
          <Field
            label="Action Taken"
            value={form.actionTaken}
            multiline
            large
          />

          <div className="mt-5">
            <InfoGrid
              items={[
                ['Rank', form.officerRank],
                ['Officer Name', form.officerName],
                ['Officer No.', form.officerNo],
              ]}
            />
          </div>
        </FIRSection>

        {/* Section 14 */}
        <FIRSection
          number="14"
          title="Complainant / Informant Signature"
        >
          <div className="h-28 border border-black mt-2 flex items-end justify-end p-4">
            <span className="text-sm">
              Signature / Thumb-impression
            </span>
          </div>
        </FIRSection>

        {/* Section 15 */}
        <FIRSection
          number="15"
          title="Date & Time of Despatch to Court"
        >
          <InfoGrid
            items={[
              ['Date', form.dispatchDate],
              ['Time', form.dispatchTime],
            ]}
          />
        </FIRSection>

        {/* Footer */}
        <footer className="border-t-2 border-black p-8 text-center">
          <p className="text-xs text-gray-600">
            This is a frontend-generated FIR draft preview.
          </p>

          <p className="text-xs text-gray-600 mt-1">
            Review all information before official submission.
          </p>
        </footer>

      </article>
    </main>
  )
}

function FIRSection({
  number,
  title,
  children,
}: {
  number: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="p-8 border-b border-gray-400">

      <div className="flex items-center gap-3 mb-5">

        <span className="text-lg font-bold">
          {number}.
        </span>

        <h2 className="text-lg font-bold uppercase">
          {title}
        </h2>

      </div>

      {children}
    </section>
  )
}

function InfoGrid({
  items,
}: {
  items: [string, string][]
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 border border-black">
      {items.map(([label, value], index) => (
        <div
          key={`${label}-${index}`}
          className="border-b border-r border-black p-3 min-h-[58px]"
        >
          <p className="text-xs font-bold uppercase text-gray-600">
            {label}
          </p>

          <p className="mt-1 text-sm whitespace-pre-wrap">
            {value || '—'}
          </p>
        </div>
      ))}
    </div>
  )
}

function Field({
  label,
  value,
  multiline = false,
  large = false,
}: {
  label: string
  value: string
  multiline?: boolean
  large?: boolean
}) {
  return (
    <div>
      <p className="text-xs font-bold uppercase text-gray-600 mb-2">
        {label}
      </p>

      <div
        className={`border border-black p-4 whitespace-pre-wrap ${
          multiline
            ? large
              ? 'min-h-[180px]'
              : 'min-h-[100px]'
            : 'min-h-[55px]'
        }`}
      >
        {value || '—'}
      </div>
    </div>
  )
}

function Table({
  headers,
  rows,
}: {
  headers: string[]
  rows: string[][]
}) {
  return (
    <div className="border border-black">

      <div className="grid grid-cols-2 font-bold">
        {headers.map((header) => (
          <div
            key={header}
            className="border-r border-b border-black p-3 text-sm"
          >
            {header}
          </div>
        ))}
      </div>

      {rows.map((row, rowIndex) => (
        <div
          key={rowIndex}
          className="grid grid-cols-2"
        >
          {row.map((cell, cellIndex) => (
            <div
              key={cellIndex}
              className="border-r border-b border-black p-3 text-sm min-h-[50px]"
            >
              {cell || '—'}
            </div>
          ))}
        </div>
      ))}

    </div>
  )
}