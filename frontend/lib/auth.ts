// lib/auth.ts
import { authAPI } from './api'

export type LawAidUser = {
  id: number
  email: string
  role: string // lowercase: citizen / police / lawyer / admin
}

// Call this right after a successful login. Stores the token in both
// localStorage (used by lib/api.ts for Authorization headers, browser-only)
// AND a cookie (used by middleware.ts, which runs server-side and cannot
// read localStorage at all). Both are needed — they serve different layers.
export async function completeLogin(accessToken: string): Promise<LawAidUser> {
  localStorage.setItem('lawaid_token', accessToken)
  document.cookie = `lawaid_token=${accessToken}; path=/; max-age=86400`

  const res = await authAPI.me()
  const user: LawAidUser = res.data
  localStorage.setItem('lawaid_role', user.role)
  localStorage.setItem('lawaid_user', JSON.stringify(user))
  document.cookie = `lawaid_role=${user.role}; path=/; max-age=86400`
  return user
}

export function getStoredUser(): LawAidUser | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem('lawaid_user')
  return raw ? JSON.parse(raw) : null
}

export function logout() {
  localStorage.removeItem('lawaid_token')
  localStorage.removeItem('lawaid_role')
  localStorage.removeItem('lawaid_user')
  document.cookie = 'lawaid_token=; path=/; max-age=0'
  document.cookie = 'lawaid_role=; path=/; max-age=0'
}

export const ROLE_ROUTES: Record<string, string> = {
  citizen: '/citizen',
  police: '/police',
  lawyer: '/lawyer',
  admin: '/admin',
}