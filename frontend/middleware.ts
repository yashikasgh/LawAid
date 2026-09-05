// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const ROLE_FOR_PATH: Record<string, string> = {
  '/citizen': 'citizen',
  '/police': 'police',
  '/lawyer': 'lawyer',
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get('lawaid_token')?.value
  const role = request.cookies.get('lawaid_role')?.value
  const { pathname } = request.nextUrl

  const matchedPrefix = Object.keys(ROLE_FOR_PATH).find(p => pathname.startsWith(p))

  if (matchedPrefix) {
    // Not logged in at all → send to login
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url))
    }
    // Logged in, but wrong role for this section → send to their own dashboard
    const requiredRole = ROLE_FOR_PATH[matchedPrefix]
    if (role !== requiredRole) {
      return NextResponse.redirect(new URL(`/${role}`, request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/citizen/:path*', '/police/:path*', '/lawyer/:path*'],
}