'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'

export default function PoliceDashboard() {
  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null)

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-100 px-4 py-8">
        <div className="max-w-6xl mx-auto">

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5 mb-10">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-navy">
                Police Dashboard
              </h1>

              <p className="mt-2 text-gray-600">
                Welcome, {user?.email || 'Police Officer'}
              </p>

              <p className="mt-1 text-sm text-gray-500">
                Draft FIRs and search relevant BNS sections.
              </p>
            </div>

            <Link
              href="/police/new-fir"
              className="inline-flex items-center justify-center bg-navy text-white px-6 py-3 rounded-lg font-semibold hover:opacity-90 transition"
            >
              + Create New FIR
            </Link>
          </div>

          {/* Main Features */}
          <section>
            <h2 className="text-2xl font-bold text-navy mb-5">
              Police Tools
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* FIR Drafting */}
              <Link
                href="/police/new-fir"
                className="group bg-white rounded-2xl shadow-sm border border-gray-200 p-7 hover:shadow-lg hover:-translate-y-1 transition-all"
              >
                <div className="w-14 h-14 rounded-xl bg-blue-50 flex items-center justify-center text-3xl mb-5">
                  📄
                </div>

                <h3 className="text-xl font-bold text-navy group-hover:text-blue-700 transition">
                  FIR Drafting
                </h3>

                <p className="mt-3 text-gray-600 leading-relaxed">
                  Create a structured FIR draft using the official IF1 format.
                  Enter incident details, complainant information, occurrence
                  details, accused information and FIR contents.
                </p>

                <div className="mt-6 inline-flex items-center text-sm font-semibold text-navy">
                  Create FIR Draft
                  <span className="ml-2 group-hover:translate-x-1 transition">
                    →
                  </span>
                </div>
              </Link>

              {/* BNS Search */}
              <Link
                href="/bns-search"
                className="group bg-white rounded-2xl shadow-sm border border-gray-200 p-7 hover:shadow-lg hover:-translate-y-1 transition-all"
              >
                <div className="w-14 h-14 rounded-xl bg-purple-50 flex items-center justify-center text-3xl mb-5">
                  ⚖️
                </div>

                <h3 className="text-xl font-bold text-navy group-hover:text-blue-700 transition">
                  BNS Section Search
                </h3>

                <p className="mt-3 text-gray-600 leading-relaxed">
                  Search for relevant Bharatiya Nyaya Sanhita sections while
                  preparing an FIR draft.
                </p>

                <div className="mt-6 inline-flex items-center text-sm font-semibold text-navy">
                  Search BNS Sections
                  <span className="ml-2 group-hover:translate-x-1 transition">
                    →
                  </span>
                </div>
              </Link>

            </div>
          </section>

          {/* Workflow */}
          <section className="mt-10 bg-white rounded-2xl shadow-sm border border-gray-200 p-7">
            <h2 className="text-xl font-bold text-navy">
              FIR Drafting Workflow
            </h2>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-5">

              <WorkflowStep
                number="1"
                title="Enter Information"
                description="Provide the incident statement and required FIR details."
              />

              <WorkflowStep
                number="2"
                title="Search BNS"
                description="Find relevant BNS sections while preparing the FIR."
              />

              <WorkflowStep
                number="3"
                title="Generate Draft"
                description="Review the completed information in the FIR document format."
              />

            </div>
          </section>

        </div>
      </main>
    </>
  )
}

function WorkflowStep({
  number,
  title,
  description,
}: {
  number: string
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-navy text-white flex items-center justify-center font-bold">
        {number}
      </div>

      <div>
        <h3 className="font-semibold text-navy">
          {title}
        </h3>

        <p className="text-sm text-gray-600 mt-1 leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  )
}