'use client'

import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'

export default function CitizenDashboard() {
  const user = getStoredUser()

  const cards = [
    {
      icon: '📝',
      title: 'File a Complaint',
      desc: 'Describe your incident and find relevant BNS sections.',
      href: '/citizen/complaint',
    },
    {
      icon: '📄',
      title: 'Understand FIR',
      desc: 'Upload an FIR and get a plain-language explanation.',
      href: '/citizen/understand',
    },
    {
      icon: '💬',
      title: 'Legal Chat',
      desc: 'Ask legal questions and get AI-powered assistance.',
      href: '/citizen/chat',
    },
    {
      icon: '⚖️',
      title: 'BNS Search',
      desc: 'Search Bharatiya Nyaya Sanhita sections instantly.',
      href: '/bns-search',
    },
  ]

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-100 px-4 py-8">
        <div className="max-w-6xl mx-auto">

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5 mb-10">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-navy">
                Citizen Dashboard
              </h1>

              <p className="mt-2 text-gray-600">
                Welcome back
                {user?.email
                  ? `, ${user.email.split('@')[0]}`
                  : ''}
                ! 👋
              </p>

              <p className="mt-1 text-sm text-gray-500">
                Access legal assistance and FIR-related services.
              </p>
            </div>
          </div>

          {/* Main Features */}
          <section>
            <h2 className="text-2xl font-bold text-navy mb-5">
              Legal Assistance
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {cards.map((card) => (
                <Link
                  key={card.title}
                  href={card.href}
                  className="group bg-white rounded-2xl shadow-sm border border-gray-200 p-7 hover:shadow-lg hover:-translate-y-1 transition-all"
                >
                  <div className="w-14 h-14 rounded-xl bg-blue-50 flex items-center justify-center text-3xl mb-5">
                    {card.icon}
                  </div>

                  <h3 className="text-xl font-bold text-navy group-hover:text-blue-700 transition">
                    {card.title}
                  </h3>

                  <p className="mt-3 text-gray-600 leading-relaxed">
                    {card.desc}
                  </p>

                  <div className="mt-6 inline-flex items-center text-sm font-semibold text-navy">
                    Open
                    <span className="ml-2 group-hover:translate-x-1 transition">
                      →
                    </span>
                  </div>
                </Link>
              ))}

            </div>
          </section>

          {/* How LawAid Helps */}
          <section className="mt-10 bg-white rounded-2xl shadow-sm border border-gray-200 p-7">
            <h2 className="text-xl font-bold text-navy">
              How LawAid Helps
            </h2>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-5">

              <HelpStep
                number="1"
                title="Describe Your Issue"
                description="Provide details about your legal concern or incident."
              />

              <HelpStep
                number="2"
                title="Get Legal Information"
                description="Explore relevant BNS sections and understand FIR-related information."
              />

              <HelpStep
                number="3"
                title="Take the Next Step"
                description="Use the available information to better understand your legal options."
              />

            </div>
          </section>

        </div>
      </main>
    </>
  )
}

function HelpStep({
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