import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const ROLE_FOR_PATH: Record<string, string> = {
  '/citizen': 'citizen',
  '/police': 'police',
  '/lawyer': 'lawyer',
}

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('lawaid_token')?.value
  const { pathname } = request.nextUrl

  const matchedPrefix = Object.keys(ROLE_FOR_PATH).find((prefix) =>
    pathname.startsWith(prefix)
  )

  // Public route
  if (!matchedPrefix) {
    return NextResponse.next()
  }

  // No authentication token
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  try {
    // Ask the backend to validate the JWT and return the real user role.
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    const response = await fetch(`${apiUrl}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: 'no-store',
    })

    // Invalid/expired token
    if (!response.ok) {
      const response = NextResponse.redirect(
        new URL('/login', request.url)
      )

      response.cookies.delete('lawaid_token')
      response.cookies.delete('lawaid_role')

      return response
    }

    const user = await response.json()
    const actualRole = user.role?.toLowerCase()
    const requiredRole = ROLE_FOR_PATH[matchedPrefix]

    // Backend role is authoritative.
    if (actualRole !== requiredRole) {
      return NextResponse.redirect(
        new URL('/unauthorized', request.url)
      )
    }

    return NextResponse.next()
  } catch {
    // Backend unavailable → don't allow protected access.
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = {
  matcher: [
    '/citizen/:path*',
    '/police/:path*',
    '/lawyer/:path*',
  ],
}