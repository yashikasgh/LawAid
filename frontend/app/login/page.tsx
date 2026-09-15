// app/login/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { completeLogin, ROLE_ROUTES } from '@/lib/auth'

const ROLES = ['Citizen', 'Police', 'Lawyer'] // UI labels only — capitalized

export default function LoginPage() {
  const router = useRouter()
  const [role, setRole] = useState('Citizen')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    setLoading(true)
    setError('')

    try {
      const res = await authAPI.login(email, password, role)
      const user = await completeLogin(res.data.access_token)
      router.push(ROLE_ROUTES[user.role] || '/')
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Invalid email or password. Please try again.')
      } else if (err?.response?.status === 422) {
        setError('Something is missing from the request — check role/email/password.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen relative overflow-hidden">
      {/* BACKGROUND IMAGE */}
      <div className="absolute inset-0" >
        <img
          src="/images/lawaid-register.png"
          alt="LawAid legal background"
          className="h-full w-full object-cover object-center"
        />
      </div>

      {/* LIGHT OVERLAY */}
      <div className="absolute inset-0 bg-white/10" />

      {/* LAWAID LOGO */}
      <div className="absolute top-8 left-8 sm:top-10 sm:left-12 z-20">
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

      {/* LOGIN CONTENT */}
      <div className="relative z-10 min-h-screen flex items-center justify-center px-5 py-8">
        <div className="w-full max-w-[500px] bg-white/85 backdrop-blur-[4px] border border-white/80 rounded-[26px] px-10 py-7 sm:px-12 sm:py-8 shadow-[0_20px_60px_rgba(18,51,91,0.12)]">

          <h2 className="font-serif text-[42px] sm:text-[46px] leading-tight tracking-[-0.025em] text-[#12335B] mb-7">
            Welcome Back
          </h2>

          {/* ROLE SELECTOR */}
          <div className="flex gap-2.5 mb-7">
            {ROLES.map(r => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`flex-1 py-3 rounded-xl text-[17px] font-semibold border transition-all duration-200 ${
  role === r
    ? 'bg-[#1d5da5] text-white border-[#1d5da5] shadow-sm'
    : 'bg-white/70 text-[#56718f] border-[#cbd5e1] hover:bg-white hover:border-[#b98528] hover:text-[#12335B] hover:shadow-sm'
}`}
              >
                {r}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-5">

            {/* EMAIL */}
            <div>
              <label className="text-[17px] font-semibold text-[#12335B]">
                Email Address
              </label>

              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                type="email"
                className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] focus:ring-2 focus:ring-[#1d5da5]/30 focus:border-[#1d5da5] outline-none"
              />
            </div>

            {/* PASSWORD */}
            <div>
              <label className="text-[17px] font-semibold text-[#12335B]">
                Password
              </label>

              <input
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                type="password"
                className="w-full border border-[#cbd5e1] rounded-xl px-5 py-3.5 mt-2 text-[17px] text-[#12335B] bg-white/80 placeholder:text-[#9aa7b8] focus:ring-2 focus:ring-[#1d5da5]/30 focus:border-[#1d5da5] outline-none"
              />
            </div>

            {/* ERROR */}
            {error && (
              <p className="text-red-500 text-sm">
                {error}
              </p>
            )}

            {/* LOGIN BUTTON */}
            <button
              onClick={handleLogin}
              disabled={loading}
              className="w-full bg-[#c18a25] text-white py-3.5 rounded-xl text-[17px] font-bold hover:bg-[#ad781b] transition disabled:opacity-60"
            >
              {loading ? 'Logging in...' : 'Login →'}
            </button>

            {/* REGISTER BUTTON */}
            <button
              onClick={() => router.push('/register')}
              className="w-full border border-[#12335B] text-[#12335B] py-3.5 rounded-xl text-[17px] font-semibold bg-white/20 hover:bg-white/50 transition"
            >
              Register New Account
            </button>
          </div>

        </div>
      </div>
    </main>
  )
}