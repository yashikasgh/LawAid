
'use client'

import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'
import {
  ArrowRight,
  CalendarDays,
  FileSearch,
  Files,
  BookOpen,
} from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'

export default function LawyerDashboard() {
  const [user, setUser] = useState(getStoredUser())

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  const features = [
    {
      title: 'Case Documents',
      description:
        'Upload and organize case documents to begin reviewing the information relevant to your case.',
      href: '/lawyer/documents',
      icon: Files,
      action: 'Open Documents',
    },
    {
      title: 'AI Case Analysis',
      description:
        'Review extracted facts, parties, locations, and other information from your case documents.',
      href: '/lawyer/analysis',
      icon: FileSearch,
      action: 'Analyze Case',
    },
    {
      title: 'Case Timeline',
      description:
        'Review and organize important case events in chronological order.',
      href: '/lawyer/timeline',
      icon: CalendarDays,
      action: 'View Timeline',
    },
    {
      title: 'Case Summary & Export',
      description:
        'Review key case details and prepare a structured summary for export.',
      href: '/lawyer/summary',
      icon: BookOpen,
      action: 'View Summary',
    },
  ]

  return (
    <>
      <Navbar />

      <main className="relative min-h-screen overflow-hidden">
        {/* Background matching the existing LawAid dashboards */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-citizen-dashboard.png"
            alt=""
            className="h-full w-full object-cover object-center"
          />
        </div>
        <div className="fixed inset-0 -z-10 bg-white/25" />

        <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
          {/* Welcome section */}
          <section className="mb-10 text-center">
            <p className="text-xs font-medium uppercase tracking-[0.3em] text-[#12335b]">
              LAWYER PORTAL
            </p>

            <h1 className="mt-5 font-serif text-4xl font-bold tracking-tight text-[#0b3155] sm:text-5xl md:text-6xl">
              Lawyer Dashboard
            </h1>

            <p className="mt-4 text-lg text-[#123b60] sm:text-xl">
              Welcome, {user?.email || 'Lawyer'}
            </p>

            <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-[#234d72] sm:text-base">
              Organize case documents, review AI-assisted analysis, and prepare
              structured case summaries.
            </p>
          </section>

          {/* Feature cards */}
          <section className="mx-auto max-w-6xl">
            <h2 className="mb-7 font-serif text-3xl font-bold text-[#0b3155] sm:text-4xl">
              Lawyer Tools
            </h2>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {features.map((feature) => {
                const Icon = feature.icon

                return (
                  <Link
                    key={feature.title}
                    href={feature.href}
                    className="group flex min-h-[300px] flex-col rounded-[22px] border border-white/80 bg-white/65 p-7 shadow-[0_10px_35px_rgba(18,51,91,0.10)] backdrop-blur-md transition duration-200 hover:-translate-y-1 hover:border-[#d6b56d] hover:bg-white/75 hover:shadow-[0_16px_40px_rgba(18,51,91,0.15)] sm:p-8"
                  >
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#d9b86f]/70 bg-white/65 text-[#123b60]">
                      <Icon size={29} strokeWidth={1.8} />
                    </div>

                    <h3 className="mt-7 font-serif text-2xl font-bold text-[#123b60] sm:text-3xl">
                      {feature.title}
                    </h3>

                    <p className="mt-4 text-base leading-[1.9] text-[#426b91] sm:text-lg">
                      {feature.description}
                    </p>

                    <div className="mt-auto flex items-center gap-3 pt-6 text-base font-semibold text-[#12335b]">
                      <span>{feature.action}</span>
                      <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#c18a25] text-[#c18a25] transition group-hover:bg-[#c18a25] group-hover:text-white">
                        <ArrowRight size={19} />
                      </span>
                    </div>
                  </Link>
                )
              })}
            </div>
          </section>
        </div>
      </main>
    </>
  )
}
