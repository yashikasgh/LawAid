'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'

export default function CitizenDashboard() {
  const [user, setUser] =
    useState<ReturnType<typeof getStoredUser>>(null)

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  const cards = [
    {
      icon: <FIRIcon />,
      title: 'Understand FIR',
      desc: 'Upload an FIR and get a plain-language explanation.',
      href: '/citizen/understand',
    },
    {
      icon: <ChatIcon />,
      title: 'Legal Chat',
      desc: 'Ask legal questions and get AI-powered assistance.',
      href: '/citizen/chat',
    },
    {
      icon: <ScaleIcon />,
      title: 'BNS Search',
      desc: 'Search Bharatiya Nyaya Sanhita sections instantly.',
      href: '/bns-search',
    },
  ]

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
              {/* <span className="h-px w-10 bg-[#b98528]" /> */}

              <span className="text-[11px] tracking-[0.3em] uppercase text-[#052d53] font-medium">
                CITIZEN PORTAL
              </span>
            </div>

            <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#052d53] tracking-[-0.025em]">
              Citizen Dashboard
            </h1>

            <p className="mt-3 text-[#052d53] text-lg">
              Welcome back
              {user?.email
                ? `, ${user.email.split('@')[0]}`
                : ''}
              !
            </p>

            <p className="mt-1 text-sm text-[#052d53]">
              Access legal assistance and FIR-related services.
            </p>

          </div>

          {/* Main Features */}
          <section>

            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="font-serif text-3xl font-semibold text-[#052d53]">
                  Legal Assistance
                </h2>

                <div className="mt-3 h-px w-12 bg-[#b98528]" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

              {cards.map((card) => (
                <Link
                  key={card.title}
                  href={card.href}
                  className="group min-h-[245px] rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.12)] p-7 transition-all duration-300 hover:-translate-y-1 hover:bg-white/80 hover:shadow-[0_20px_50px_rgba(18,51,91,0.18)]"
                >

                  {/* Icon */}
                  <div className="w-14 h-14 rounded-[12px] border border-[#d2a14b]/50 bg-[#f8f6f1]/70 flex items-center justify-center text-2xl mb-6 transition-transform duration-300 group-hover:-translate-y-1">
                    {card.icon}
                  </div>

                  {/* Title */}
                  <h3 className="font-serif text-[27px] font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                    {card.title}
                  </h3>

                  {/* Description */}
                  <p className="mt-3 text-[#315b82] leading-relaxed max-w-[500px]">
                    {card.desc}
                  </p>

                  {/* Open */}
                  <div className="mt-6 inline-flex items-center gap-3 text-sm font-semibold text-[#12335B] group-hover:text-[#b98528] transition-colors">
                    Open

                    <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#b98528] text-[#b98528] transition-all duration-300 group-hover:bg-[#b98528] group-hover:text-white group-hover:translate-x-1">
                      →
                    </span>
                  </div>

                </Link>
              ))}

            </div>
          </section>

          {/* How LawAid Helps */}
          <section className="mt-8 rounded-[18px] border border-white/70 bg-white/65 backdrop-blur-md shadow-[0_15px_40px_rgba(18,51,91,0.10)] p-7">

            <div className="flex items-center gap-4">
              <span className="h-px w-10 bg-[#b98528]" />

              <span className="text-[11px] tracking-[0.3em] uppercase text-[#56718f] font-medium">
                HOW IT WORKS
              </span>
            </div>

            <h2 className="mt-4 font-serif text-3xl font-semibold text-[#12335B]">
              How LawAid Helps
            </h2>

            <div className="mt-7 grid grid-cols-1 md:grid-cols-3 gap-6">

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

function FIRIcon() {
  return (
    <svg
      width="38"
      height="38"
      viewBox="0 0 38 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M8.5 4.5H23L29.5 11V33.5H8.5V4.5Z"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M23 4.5V11H29.5"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M13 16H24M13 20.5H24M13 25H20"
        stroke="#12335B"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle
        cx="27"
        cy="27"
        r="5"
        fill="#F8F6F1"
        stroke="#B98528"
        strokeWidth="1.7"
      />
      <path
        d="M30.5 30.5L34 34"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg
      width="40"
      height="38"
      viewBox="0 0 40 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M6 7C6 4.79 7.79 3 10 3H30C32.21 3 34 4.79 34 7V21C34 23.21 32.21 25 30 25H19L12 32V25H10C7.79 25 6 23.21 6 21V7Z"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M12 13H28M12 18H23"
        stroke="#12335B"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle
        cx="29"
        cy="28"
        r="3.5"
        fill="#F8F6F1"
        stroke="#B98528"
        strokeWidth="1.5"
      />
    </svg>
  )
}

function ScaleIcon() {
  return (
    <svg
      width="40"
      height="38"
      viewBox="0 0 40 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M20 4V32"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M12 32H28"
        stroke="#12335B"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M8 9H32"
        stroke="#B98528"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M11 9L6 19C6 21.5 8.2 23 12 23C15.8 23 18 21.5 18 19L13 9"
        stroke="#12335B"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M29 9L24 19C24 21.5 26.2 23 30 23C33.8 23 36 21.5 36 19L31 9"
        stroke="#12335B"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <circle
        cx="20"
        cy="4"
        r="2"
        fill="#B98528"
      />
    </svg>
  )
}