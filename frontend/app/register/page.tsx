// app/register/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { completeLogin, getStoredUser, ROLE_ROUTES } from '@/lib/auth'

const ROLES = ['Citizen', 'Police', 'Lawyer']

export default function RegisterPage() {
  const router = useRouter()
  const [role, setRole] = useState('Citizen')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const user = getStoredUser()
      if (user) {
        try {
          await authAPI.me()
          router.replace(ROLE_ROUTES[user.role.toLowerCase()] || "/")
        } catch {
          localStorage.removeItem('lawaid_token')
          localStorage.removeItem('lawaid_role')
          localStorage.removeItem('lawaid_user')
        }
      }
    }
    checkAuth()
  }, [router])

  async function handleRegister() {
    setError('')

    if (!name.trim()) {
      setError('Please enter your full name.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setLoading(true)

    try {
      await authAPI.register(email, password, role)

      // Save name on frontend using the normalized email as the key
      localStorage.setItem(
        `lawaid_name_${email.toLowerCase()}`,
        name.trim()
      )

      // Registration succeeded — log the user in right away
      const loginRes = await authAPI.login(email, password, role)
      const user = await completeLogin(loginRes.data.access_token)

      router.push(ROLE_ROUTES[user.role] || '/')
    } catch (err: any) {
      if (err?.response?.status === 400) {
        setError('That email is already registered. Try logging in instead.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f8f6f1]">

      {/* BACKGROUND IMAGE */}
      <div className="absolute inset-0">
        <img
          src="/images/lawaid-register.png"
          alt="LawAid legal background"
          className="h-full w-full object-cover object-center"
        />
      </div>

      {/* SOFT OVERLAY */}
      <div className="absolute inset-0 bg-white/10" />

      {/* CONTENT */}
      <div className="relative z-10 min-h-screen">

        {/* LOGO */}
        <div className="absolute left-8 top-8 sm:left-12 sm:top-8 lg:left-20 lg:top-8">
          <div className="flex flex-col leading-none">
            <span className="font-serif text-[38px] sm:text-[42px] tracking-[-0.04em] text-[#12335B]">
              Law
              <span className="text-[#b98528]">Aid</span>
            </span>

            <span className="mt-1 text-[6px] sm:text-[7px] tracking-[0.22em] uppercase text-[#56718f]">
              KNOW • UNDERSTAND • GET HELP
            </span>
          </div>
        </div>

        <div className="min-h-screen flex items-center">

          {/* LEFT CONTENT */}
          <div className="w-full lg:w-[58%] px-8 sm:px-12 lg:pl-[27%] lg:pr-10 pt-28 lg:pt-0">

            <div className="flex items-center gap-5 mb-8">
              <span className="h-px w-12 bg-[#b98528]" />

              <span className="text-[11px] sm:text-[12px] tracking-[0.35em] uppercase text-[#56718f] font-medium">
                JOIN LAWAID
              </span>
            </div>

            <h1 className="font-serif text-[#12335B] text-[48px] sm:text-[58px] lg:text-[62px] leading-[1.08] tracking-[-0.03em] max-w-[430px]">
              Create your
              <br />
              account to
              <br />
              get started.
            </h1>

          </div>

          {/* REGISTER CARD */}
          <div className="w-full lg:w-[42%] px-6 sm:px-10 lg:px-0 lg:pr-[8%] py-28 lg:py-0">

            <div className="w-full max-w-[470px] ml-auto rounded-[20px] border border-white/70 bg-white/75 backdrop-blur-md shadow-[0_20px_50px_rgba(18,51,91,0.15)] px-8 sm:px-10 py-9">

              <h2 className="font-serif text-[34px] sm:text-[38px] leading-none tracking-[-0.025em] text-[#12335B] mb-7">
                Create Account
              </h2>

              {/* ROLE BUTTONS */}
              <div className="flex gap-2 mb-7">

                {ROLES.map(r => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`flex-1 py-3 rounded-[10px] text-[15px] font-semibold transition-all duration-200 border ${
                      role === r
                        ? 'bg-[#15539a] text-white border-[#15539a] shadow-sm'
                        : 'bg-white/60 text-[#56718f] border-white/70 hover:bg-white/90 hover:border-[#15539a]/30 hover:text-[#12335B] hover:shadow-sm'
                    }`}
                  >
                    {r}
                  </button>
                ))}

              </div>

              <div className="flex flex-col gap-2">

                {/* FULL NAME */}
                <div>
                  <label className="text-[15px] font-semibold text-[#173f67]">
                    Full Name
                  </label>

                  <input
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Enter your full name"
                    type="text"
                    className="w-full border border-[#cbd4df] bg-white/75 rounded-[10px] px-4 py-3.5 mt-1.5 text-[15px] text-[#12335B] placeholder:text-gray-400 focus:border-[#15539a] focus:ring-2 focus:ring-[#15539a]/20 outline-none"
                  />
                </div>

                {/* EMAIL */}
                <div>
                  <label className="text-[15px] font-semibold text-[#173f67]">
                    Email Address
                  </label>

                  <input
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    type="email"
                    className="w-full border border-[#cbd4df] bg-white/75 rounded-[10px] px-4 py-3.5 mt-1.5 text-[15px] text-[#12335B] placeholder:text-gray-400 focus:border-[#15539a] focus:ring-2 focus:ring-[#15539a]/20 outline-none"
                  />
                </div>

                {/* PASSWORD */}
                <div>
                  <label className="text-[15px] font-semibold text-[#173f67]">
                    Password
                  </label>

                  <input
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    type="password"
                    className="w-full border border-[#cbd4df] bg-white/75 rounded-[10px] px-4 py-3.5 mt-1.5 text-[15px] text-[#12335B] placeholder:text-gray-400 focus:border-[#15539a] focus:ring-2 focus:ring-[#15539a]/20 outline-none"
                  />
                </div>

                {/* CONFIRM PASSWORD */}
                <div>
                  <label className="text-[15px] font-semibold text-[#173f67]">
                    Confirm Password
                  </label>

                  <input
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    type="password"
                    className="w-full border border-[#cbd4df] bg-white/75 rounded-[10px] px-4 py-3.5 mt-1.5 text-[15px] text-[#12335B] placeholder:text-gray-400 focus:border-[#15539a] focus:ring-2 focus:ring-[#15539a]/20 outline-none"
                  />
                </div>

                {/* ERROR */}
                {error && (
                  <p className="text-red-500 text-sm">
                    {error}
                  </p>
                )}

                {/* CREATE ACCOUNT */}
                <button
                  onClick={handleRegister}
                  disabled={loading}
                  className="w-full bg-[#b98528] text-white py-3.5 rounded-[12px] font-bold text-[16px] hover:bg-[#a8751e] transition disabled:opacity-60"
                >
                  {loading ? 'Creating account...' : 'Create Account →'}
                </button>

                {/* BACK TO LOGIN */}
                <button
                  onClick={() => router.push('/login')}
                  className="w-full border border-[#12335B] bg-white/40 text-[#12335B] py-3.5 rounded-[12px] font-semibold text-[16px] hover:bg-white/70 transition"
                >
                  Back to Login
                </button>

              </div>

            </div>

          </div>

        </div>
      </div>
    </div>
  )
}