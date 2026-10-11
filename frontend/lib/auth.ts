import { authAPI } from './api'

export type LawAidUser = {
  id: number
  email: string
  role: string
}

export async function completeLogin(
  _accessToken?: string
): Promise<LawAidUser> {
  const res = await authAPI.me()
  const user: LawAidUser = res.data
  localStorage.setItem('lawaid_user', JSON.stringify(user))
  return user
}

export async function restoreSession(): Promise<LawAidUser | null> {
  try {
    return await completeLogin()
  } catch {
    clearClientSession()
    return null
  }
}

export function clearClientSession() {
  if (typeof window === 'undefined') return
  localStorage.removeItem('lawaid_role')
  localStorage.removeItem('lawaid_user')
}

export function getStoredUser(): LawAidUser | null {
  if (typeof window === 'undefined') return null

  const raw = localStorage.getItem('lawaid_user')

  if (!raw) return null

  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export async function logout() {
  try {
    await authAPI.logout()
  } catch {
    // Continue with client-side logout even if the backend request fails.
  }

  clearClientSession()
}

export const ROLE_ROUTES: Record<string, string> = {
  citizen: '/citizen',
  police: '/police',
  lawyer: '/lawyer',
  admin: '/admin',
}
