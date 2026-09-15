'use client'

import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'
import { useEffect, useState } from 'react'

export default function LawyerDashboard() {
  const [user, setUser] = useState(getStoredUser())

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
                LAWYER PORTAL
              </span>
            </div>

            <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#052d53] tracking-[-0.025em]">
              Lawyer Dashboard
            </h1>

            <p className="mt-3 text-[#052d53] text-lg">
              Welcome, {user?.email || 'Lawyer'}
            </p>

            <p className="mt-1 text-sm text-[#052d53]">
              Review cases, research legal information, and explore BNS sections.
            </p>

          </div>

          {/* Main Features */}
          <section>

            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="font-serif text-3xl font-semibold text-[#052d53]">
                  Legal Tools
                </h2>

                <div className="mt-3 h-px w-12 bg-[#b98528]" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

              {/* My Cases */}
              <div className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]">

                {/* Icon */}
                <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                  📁
                </div>

                {/* Title */}
                <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  My Cases
                </h3>

                {/* Description */}
                <p className="mt-3 text-[#315b82] leading-relaxed">
                  View and manage assigned cases.
                </p>

              </div>

              {/* Case Research */}
              <div className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]">

                {/* Icon */}
                <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                  🔎
                </div>

                {/* Title */}
                <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  Case Research
                </h3>

                {/* Description */}
                <p className="mt-3 text-[#315b82] leading-relaxed">
                  Review case documents and legal information.
                </p>

              </div>

              {/* IPC → BNS */}
              <div className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]">

                {/* Icon */}
                <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                  ⚖️
                </div>

                {/* Title */}
                <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                  IPC → BNS
                </h3>

                {/* Description */}
                <p className="mt-3 text-[#315b82] leading-relaxed">
                  Convert IPC sections to corresponding BNS sections.
                </p>

              </div>

            </div>
          </section>

        </div>
      </main>
    </>
  )
}