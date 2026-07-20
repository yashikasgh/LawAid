// lib/auth.ts
import { authAPI } from './api'

export type LawAidUser = {
  id: number
  email: string
  role: string // lowercase: citizen / police / lawyer / admin
}

// Call this right after a successful login. Stores the token, then
// fetches /auth/me to get the real role from the backend — don't trust
// the role tab the user clicked, since that's just UI state.
export async function completeLogin(accessToken: string): Promise<LawAidUser> {
  localStorage.setItem('lawaid_token', accessToken)
  const res = await authAPI.me()
  const user: LawAidUser = res.data
  localStorage.setItem('lawaid_role', user.role)
  localStorage.setItem('lawaid_user', JSON.stringify(user))
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
}

export const ROLE_ROUTES: Record<string, string> = {
  citizen: '/citizen',
  police: '/police',
  lawyer: '/lawyer',
  admin: '/admin',
}