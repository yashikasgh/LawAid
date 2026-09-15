'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { getStoredUser, logout } from '@/lib/auth'

export default function HomePage() {
  const [user, setUser] = useState(getStoredUser())

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  async function handleProtectedAction(
    event: React.MouseEvent<HTMLAnchorElement>
  ) {
    event.preventDefault()

    if (user) {
      await logout()
      setUser(null)
    }

    window.location.href = '/login'
  }

  return (
    <main className="min-h-screen bg-[#f8f6f1] text-[#12335B]">

      {/* HERO */}
      <section className="relative min-h-[calc(100vh-0px)] overflow-hidden">
        <div className="absolute inset-0">
          <img
            src="/images/lawaid-hero.png"
            alt="LawAid legal assistance"
            className="h-full w-full object-cover object-center"
          />
        </div>

        <div className="relative z-10 min-h-screen flex items-center">
          <div className="w-full max-w-[1500px] mx-auto px-8 sm:px-12 lg:px-20 xl:px-28">
            <div className="ml-auto w-full lg:w-[52%] xl:w-[50%] pt-16 lg:pt-0">
              <div className="bg-[#F8F8F8]/15 backdrop-blur-[2px] px-8 py-10 lg:px-10 lg:py-12">
                <div className="flex items-center gap-5 mb-8">
                  <span className="h-px w-12 bg-[#b98528]" />
                  <span className="text-[12px] sm:text-[13px] tracking-[0.35em] uppercase text-[#b98528] font-medium">
                    AI-POWERED LEGAL ASSISTANCE
                  </span>
                </div>

                <h1 className="font-serif text-[#12335B] text-[58px] sm:text-[72px] lg:text-[76px] xl:text-[88px] leading-[0.92] tracking-[-0.035em]">
                  Justice
                  <br />
                  Made{' '}
                  <span className="italic text-[#b98528]">
                    Simple.
                  </span>
                </h1>

                <p className="mt-10 max-w-[650px] text-[18px] sm:text-[20px] lg:text-[22px] leading-relaxed text-[#173f67]">
                  Understand your rights. Access legal guidance.
                  Take the next step with confidence.
                </p>

                <div className="mt-9 flex flex-wrap gap-4">
                  <Link
                    href="/login"
                    onClick={handleProtectedAction}
                    className="inline-flex items-center justify-center gap-5 rounded-full bg-[#b98528] px-8 py-4 text-[15px] font-semibold text-white shadow-md transition hover:bg-[#a8751e] hover:-translate-y-0.5"
                  >
                    Get Legal Help
                    <span className="text-xl leading-none">→</span>
                  </Link>

                  <Link
                    href="/login"
                    onClick={handleProtectedAction}
                    className="inline-flex items-center justify-center rounded-full border border-[#12335B] bg-white px-8 py-4 text-[15px] font-semibold text-[#12335B] transition hover:bg-[#f3f0e9] hover:-translate-y-0.5"
                  >
                    Upload Your FIR
                  </Link>
                </div>

                <div className="mt-20 flex items-center gap-5">
                  <span className="h-px w-12 bg-[#b98528]" />
                  <span className="text-[11px] sm:text-[12px] tracking-[0.35em] uppercase text-[#56718f]">
                    ACCESSIBLE LEGAL INFORMATION
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      

      {/* ABOUT */}
      <section id="about" className="bg-[#f8f6f1]">
        <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[620px]">

          {/* LEFT CONTENT */}
          <div className="px-8 sm:px-12 lg:px-16 xl:px-20 py-20 lg:py-24 flex flex-col justify-center">

            <div className="flex items-center gap-5 mb-8">
              <span className="h-px w-10 bg-[#b98528]" />

              <span className="text-[11px] tracking-[0.35em] uppercase text-[#56718f]">
                ABOUT LAWAID
              </span>
            </div>

            <h2 className="font-serif text-[#12335B] text-[48px] sm:text-[56px] lg:text-[58px] leading-[1.05] tracking-[-0.025em] max-w-[650px]">
              Bridging the gap
              <br />
              between people and
              <br />
              justice.
            </h2>

            <p className="mt-9 max-w-[650px] text-[17px] leading-[1.7] text-[#315b82]">
              LawAid is an AI-powered legal assistance platform
              designed to make legal information accessible,
              understandable, and actionable for every Indian
              citizen.
            </p>

            <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-7 max-w-[700px]">
              <Principle
                icon={<PeopleIcon />}
                text={
                  <>
                    People
                    <br />
                    First
                  </>
                }
              />

              <Principle
                icon={<ShieldIcon />}
                text={
                  <>
                    Reliable
                    <br />
                    Information
                  </>
                }
              />

              <Principle
                icon={<ScaleIcon />}
                text={
                  <>
                    Technology for
                    <br />
                    Justice
                  </>
                }
              />
            </div>

            <div className="mt-10">
              <Link
                href="/login"
                onClick={handleProtectedAction}
                className="inline-flex items-center gap-5 rounded-full bg-[#b98528] px-7 py-3.5 text-sm font-semibold text-white transition hover:bg-[#a8751e] hover:-translate-y-0.5"
              >
                Learn More
                <span className="text-lg">→</span>
              </Link>
            </div>

          </div>

          {/* RIGHT IMAGE + QUOTE OVERLAY */}
          <div className="relative min-h-[620px] overflow-hidden">

            {/* FULL RIGHT-SIDE IMAGE */}
            <img
              src="/images/lawaid-about.png"
              alt="Supreme Court of India"
              className="absolute inset-0 h-full w-full object-cover object-center"
            />

            {/* WHITE TRANSLUCENT CONTENT PANEL */}
            <div className="absolute top-8 left-8 sm:top-10 sm:left-10 lg:top-12 lg:left-12 px-4">

              <div className="w-full max-w-[390px] bg-transparent px-8 sm:px-10 py-10 shadow-[0_15px_40px_rgba(18,51,91,0.10)]">

                <div className="flex items-center gap-5 mb-7">
                  {/* <span className="h-20px w-20 bg-[#b98528]" /> */}

                  {/* <span className="text-[10px] sm:text-[11px] tracking-[0.32em] uppercase text-[#56718f]">
                    LAW & JUSTICE
                  </span> */}
                </div>

                <blockquote className="font-serif text-[28px] sm:text-[31px] leading-[1.3] text-[#12335B]">
                  “Justice is not a privilege
                  <br />
                  for a few, but a right for all.”
                </blockquote>

                <p className="mt-7 text-[10px] tracking-[0.25em] uppercase text-[#56718f]">
                  — CONSTITUTION OF INDIA
                </p>

              </div>

            </div>

          </div>

        </div>
      </section>

      {/* STATS */}
      <section className="relative bg-[#f8f6f1] border-t border-[#ddd7ca] border-b border-[#ddd7ca]">
        <div className="grid grid-cols-2 lg:grid-cols-4 items-center py-12 sm:py-14">
          <Stat number="358+" label="BNS Sections" border />
          <Stat number="24/7" label="AI Assistance" border />
          <Stat number="3" label="User Portals" border />
          <Stat number="1" label="Mission" />
        </div>
      </section>

      {/* SERVICES */}
      <section id="services" className="relative min-h-[620px] overflow-hidden">
        <div className="absolute inset-0">
          <img
            src="/images/lawaid-services.png"
            alt="Elegant legal office with books and scale of justice"
            className="h-full w-full object-cover object-center"
          />

          <div className="absolute inset-0 bg-[#102d49]/45" />

          <div className="absolute inset-0 bg-gradient-to-r from-[#102d49]/85 via-[#102d49]/55 to-transparent" />
        </div>

        <div className="relative z-10 max-w-[1500px] mx-auto px-8 sm:px-12 lg:px-20 xl:px-28 py-24 lg:py-28">
          <div className="max-w-[760px]">
            <div className="flex items-center gap-5 mb-8">
              <span className="h-px w-10 bg-[#d2a14b]" />

              <span className="text-[11px] tracking-[0.35em] uppercase text-[#d2a14b]">
                OUR SERVICES
              </span>
            </div>

            <h2 className="font-serif text-white text-[48px] sm:text-[58px] lg:text-[68px] leading-[1.05] tracking-[-0.025em]">
              Comprehensive Legal
              <br />
              Support
              <br />
              for Every Need.
            </h2>

            <p className="mt-10 max-w-[680px] text-[17px] sm:text-[18px] leading-[1.8] text-white/90">
              From understanding an incident to exploring relevant
              BNS provisions, LawAid helps make essential legal
              information easier to access and understand.
            </p>

            <div className="mt-10">
              <Link
                href="/login"
                onClick={handleProtectedAction}
                className="inline-flex items-center gap-5 rounded-full bg-[#b98528] px-8 py-4 text-sm font-semibold text-white transition hover:bg-[#a8751e] hover:-translate-y-0.5"
              >
                Get Started
                <span className="text-xl">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer
        id="contact"
        className="bg-[#102d49] text-white px-8 sm:px-12 lg:px-20 xl:px-28 py-10"
      >
        <div className="max-w-[1500px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-5">
          <div className="flex items-center gap-3">
            <span className="text-[#d2a14b] text-2xl">⚖</span>

            <span className="text-xl font-semibold">
              LawAid
            </span>
          </div>

          <p className="text-sm text-white/60 text-center">
            AI-powered legal assistance for a more informed India.
          </p>

          <p className="text-xs text-white/50">
            © {new Date().getFullYear()} LawAid
          </p>
        </div>
      </footer>
    </main>
  )
}

function FeatureCard({
  icon,
  title,
  description,
  href,
}: {
  icon: React.ReactNode
  title: string
  description: React.ReactNode
  href: string
}) {
  return (
    <Link
      href={href}
      className="group min-h-[300px] flex flex-col items-center justify-center text-center px-8 py-14 border-b lg:border-b-0 lg:border-r border-[#d9d4ca] last:border-r-0 transition hover:bg-white"
    >
      <div className="text-[#b98528] mb-8 transition-transform duration-300 group-hover:-translate-y-1">
        {icon}
      </div>

      <h3 className="font-serif text-[27px] text-[#12335B]">
        {title}
      </h3>

      <p className="mt-5 text-[16px] leading-7 text-[#315b82]">
        {description}
      </p>

      <div className="mt-7 flex h-11 w-11 items-center justify-center rounded-full border border-[#b98528] text-[#b98528] transition group-hover:bg-[#b98528] group-hover:text-white">
        <span className="text-lg">→</span>
      </div>
    </Link>
  )
}

function Principle({
  icon,
  text,
}: {
  icon: React.ReactNode
  text: React.ReactNode
}) {
  return (
    <div className="flex items-start gap-4 text-[#315b82]">
      <div className="text-[#b98528] flex-shrink-0">
        {icon}
      </div>

      <span className="text-[15px] leading-6">
        {text}
      </span>
    </div>
  )
}

function Stat({
  number,
  label,
  border = false,
}: {
  number: string
  label: string
  border?: boolean
}) {
  return (
    <div className="relative flex items-center justify-center">
      {border && (
        <span className="absolute right-0 top-1/2 -translate-y-1/2 h-32 w-px bg-[#b9b4aa]" />
      )}

      <div className="text-center">
        <div className="font-serif text-[42px] sm:text-[48px] leading-none text-[#12335B]">
          {number}
        </div>

        <div className="mt-3 text-[15px] sm:text-[16px] text-[#12335B]">
          {label}
        </div>
      </div>
    </div>
  )
}

function DocumentIcon() {
  return (
    <svg
      width="38"
      height="38"
      viewBox="0 0 38 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M9 3.5H23L29 9.5V34.5H9V3.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M23 3.5V10H29"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M13.5 17H24.5M13.5 22H24.5M13.5 27H21"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function DocumentSearchIcon() {
  return (
    <svg
      width="38"
      height="38"
      viewBox="0 0 38 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M8 3.5H22L28 9.5V26"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M22 3.5V10H28"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M8 3.5V31H20"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M12 16H22M12 21H18"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <circle
        cx="25"
        cy="25"
        r="5"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M29 29L33 33"
        stroke="currentColor"
        strokeWidth="1.7"
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
        d="M6 6.5C6 4.84 7.34 3.5 9 3.5H31C32.66 3.5 34 4.84 34 6.5V22.5C34 24.16 32.66 25.5 31 25.5H19L12 32V25.5H9C7.34 25.5 6 24.16 6 22.5V6.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <circle
        cx="13"
        cy="14.5"
        r="1.3"
        fill="currentColor"
      />

      <circle
        cx="20"
        cy="14.5"
        r="1.3"
        fill="currentColor"
      />

      <circle
        cx="27"
        cy="14.5"
        r="1.3"
        fill="currentColor"
      />
    </svg>
  )
}

function BookIcon() {
  return (
    <svg
      width="42"
      height="38"
      viewBox="0 0 42 38"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M5 6C10 3 16 3 21 6V34C16 31 10 31 5 34V6Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M37 6C32 3 26 3 21 6V34C26 31 32 31 37 34V6Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M21 6V34"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function PeopleIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="16"
        cy="9"
        r="4"
        stroke="currentColor"
        strokeWidth="1.6"
      />

      <path
        d="M8 27V23C8 19.69 10.69 17 14 17H18C21.31 17 24 19.69 24 23V27"
        stroke="currentColor"
        strokeWidth="1.6"
      />

      <path
        d="M8.5 16C5.74 16 3.5 18.24 3.5 21V25"
        stroke="currentColor"
        strokeWidth="1.6"
      />

      <path
        d="M23.5 16C26.26 16 28.5 18.24 28.5 21V25"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M16 3L27 7V14.5C27 21.5 22.5 26.5 16 29C9.5 26.5 5 21.5 5 14.5V7L16 3Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M11 16L14.5 19.5L21.5 12.5"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function ScaleIcon() {
  return (
    <svg
      width="34"
      height="32"
      viewBox="0 0 34 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M17 4V27"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M9 27H25"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M17 4H28"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M6 8L11 8"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M6 8L2.5 17C2.5 19.2 4.5 20.5 8.5 20.5C12.5 20.5 14.5 19.2 14.5 17L11 8"
        stroke="currentColor"
        strokeWidth="1.7"
      />

      <path
        d="M28 8L31.5 17C31.5 19.2 29.5 20.5 25.5 20.5C21.5 20.5 19.5 19.2 19.5 17L23 8"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  )
}