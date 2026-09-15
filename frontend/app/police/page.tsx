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

      <main className="relative min-h-screen overflow-hidden">

        {/* BACKGROUND IMAGE */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-citizen-dashboard.png"
            alt="LawAid legal background"
            className="h-full w-full object-cover object-center"
          />
        </div>

        {/* SOFT LIGHT OVERLAY */}
        <div className="fixed inset-0 -z-10 bg-white/25" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">

          {/* Header */}
          <div className="mb-10 text-center">

            <div className="inline-flex items-center justify-center gap-4 mb-5">

              <span className="text-[11px] tracking-[0.3em] uppercase text-[#052d53] font-medium">
                POLICE PORTAL
              </span>
            </div>

            <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#052d53] tracking-[-0.025em]">
              Police Dashboard
            </h1>

            <p className="mt-3 text-[#052d53] text-lg">
              Welcome, {user?.email || 'Police Officer'}
            </p>

            <p className="mt-1 text-sm text-[#052d53]">
              Draft FIRs and search relevant BNS sections.
            </p>

            <div className="mt-6">
              <Link
                href="/police/new-fir"
                className="inline-flex items-center justify-center bg-[#12335B] text-white px-6 py-3 rounded-lg font-semibold hover:bg-[#0d2949] transition"
              >
                + Create New FIR
              </Link>
            </div>

          </div>

          {/* Main Features */}
          <section>

            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="font-serif text-3xl font-semibold text-[#052d53]">
                  Police Tools
                </h2>

                <div className="mt-3 h-px w-12 bg-[#b98528]" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

              {/* FIR Drafting */}
              <Link
                href="/police/new-fir"
                className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]"
              >

                {/* Icon */}
                <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                  📄
                </div>

                {/* Title */}
                <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  FIR Drafting
                </h3>

                {/* Description */}
                <p className="mt-3 text-[#315b82] leading-relaxed max-w-[500px]">
                  Create a structured FIR draft using the official IF1 format.
                  Enter incident details, complainant information, occurrence
                  details, accused information and FIR contents.
                </p>

                {/* Open */}
                <div className="mt-6 inline-flex items-center gap-3 text-sm font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  Create FIR Draft

                  <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#b98528] text-[#b98528] transition-all duration-300 group-hover:bg-[#b98528] group-hover:text-white group-hover:translate-x-1">
                    →
                  </span>
                </div>

              </Link>

              {/* BNS Search */}
              <Link
                href="/bns-search"
                className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]"
              >

                {/* Icon */}
                <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                  ⚖️
                </div>

                {/* Title */}
                <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  BNS Section Search
                </h3>

                {/* Description */}
                <p className="mt-3 text-[#315b82] leading-relaxed max-w-[500px]">
                  Search for relevant Bharatiya Nyaya Sanhita sections while
                  preparing an FIR draft.
                </p>

                {/* Open */}
                <div className="mt-6 inline-flex items-center gap-3 text-sm font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  Search BNS Sections

                  <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#b98528] text-[#b98528] transition-all duration-300 group-hover:bg-[#b98528] group-hover:text-white group-hover:translate-x-1">
                    →
                  </span>
                </div>

              </Link>

            </div>
            
            <DraftsList />
          </section>

          {/* Workflow */}
          <section className="mt-8 rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.10)] p-7">

            <div className="flex items-center gap-4">
              <span className="h-px w-10 bg-[#b98528]" />

              <span className="text-[11px] tracking-[0.3em] uppercase text-[#56718f] font-medium">
                HOW IT WORKS
              </span>
            </div>

            <h2 className="mt-4 font-serif text-3xl font-semibold text-[#12335B]">
              FIR Drafting Workflow
            </h2>

            <div className="mt-7 grid grid-cols-1 md:grid-cols-3 gap-6">

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

      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#12335B] text-white flex items-center justify-center font-semibold border-2 border-[#b98528]">
        {number}
      </div>

      <div>
        <h3 className="font-semibold text-[#12335B]">
          {title}
        </h3>

        <p className="text-sm text-[#56718f] mt-1 leading-relaxed">
          {description}
        </p>
      </div>

    </div>
  )
}
function DraftsList() {
  const [drafts, setDrafts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDrafts() {
      try {
        const token = localStorage.getItem("access_token")
        const res = await fetch("http://localhost:8000/api/fir/drafts", {
          headers: { "Authorization": `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          setDrafts(data)
        }
      } catch (e) {
        console.error("Failed to load drafts", e)
      } finally {
        setLoading(false)
      }
    }
    loadDrafts()
  }, [])

  if (loading) return null

  if (drafts.length === 0) return null

  return (
    <div className="mt-8">
      <h3 className="font-serif text-[24px] font-semibold text-[#12335B] mb-4">Recent Drafts</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {drafts.map(d => (
          <div key={d.draft_id} className="bg-white/80 border border-gray-200 p-4 rounded-xl shadow-sm">
            <h4 className="font-bold text-[#12335B] mb-1">Draft FIR</h4>
            <p className="text-sm text-gray-600 truncate mb-2">{d.statement?.substring(0, 80) || "No statement"}</p>
            <p className="text-xs text-gray-400 mb-3">Updated: {new Date(d.updated_at).toLocaleString()}</p>
            <Link 
              href="/police/new-fir"
              onClick={() => {
                sessionStorage.setItem("lawaid_draft_id", d.draft_id)
                sessionStorage.setItem("lawaid_fir_draft", JSON.stringify(d))
              }}
              className="text-sm font-semibold text-[#b98528] hover:underline"
            >
              Resume Draft ?
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}

