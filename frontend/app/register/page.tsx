// app/register/page.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { completeLogin, ROLE_ROUTES } from '@/lib/auth'

const ROLES = ['Citizen', 'Police', 'Lawyer']

export default function RegisterPage() {
  const router = useRouter()
  const [role, setRole] = useState('Citizen')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRegister() {
    setError('')

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
    <div className="min-h-screen flex">
      <div className="w-1/2 bg-navy text-white p-12 flex flex-col justify-center">
        <h1 className="text-3xl font-bold mb-3">Join LawAid</h1>
        <p className="text-blue-200 mb-10">Create your account to get started.</p>
        {['⚖ FIR Guidance', '📄 BNS Section Search', '💬 Legal Chat', '🔒 Secure & Private'].map(f => (
          <p key={f} className="text-gold text-lg mb-3">{f}</p>
        ))}
      </div>

      <div className="w-1/2 flex items-center justify-center bg-white">
        <div className="w-96 p-8 shadow-xl rounded-2xl border border-gray-100">
          <h2 className="text-2xl font-bold text-navy mb-6">Create Account</h2>

          <div className="flex gap-2 mb-6">
            {ROLES.map(r => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition ${
                  role === r ? 'bg-lawblue text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-4">
            <div>
              <label className="text-sm font-semibold text-gray-600">Email Address</label>
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                type="email"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mt-1 text-sm focus:ring-2 focus:ring-lawblue outline-none"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">Password</label>
              <input
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                type="password"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mt-1 text-sm focus:ring-2 focus:ring-lawblue outline-none"
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-gray-600">Confirm Password</label>
              <input
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                type="password"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mt-1 text-sm focus:ring-2 focus:ring-lawblue outline-none"
              />
            </div>

            {error && <p className="text-red-500 text-sm">{error}</p>}

            <button
              onClick={handleRegister}
              disabled={loading}
              className="w-full bg-navy text-white py-3 rounded-lg font-bold hover:bg-lawblue transition"
            >
              {loading ? 'Creating account...' : 'Create Account →'}
            </button>
            <button
              onClick={() => router.push('/login')}
              className="w-full border border-navy text-navy py-3 rounded-lg font-semibold hover:bg-lblue transition"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}