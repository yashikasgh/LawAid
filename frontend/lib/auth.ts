import { authAPI } from './api'

export type LawAidUser = {
  id: number
  email: string
  role: string
}

export async function completeLogin(
  accessToken: string
): Promise<LawAidUser> {
  localStorage.setItem('lawaid_token', accessToken)

  document.cookie = `lawaid_token=${accessToken}; path=/; max-age=86400; SameSite=Lax`

  const res = await authAPI.me()
  const user: LawAidUser = res.data

  const role = user.role.toLowerCase()

  localStorage.setItem('lawaid_role', role)
  localStorage.setItem('lawaid_user', JSON.stringify(user))

  document.cookie = `lawaid_role=${role}; path=/; max-age=86400; SameSite=Lax`

  return user
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