// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('lawaid_token')?.value
  const { pathname } = request.nextUrl

  const protectedPaths = ['/citizen', '/police', '/lawyer']
  const isProtected = protectedPaths.some(p => pathname.startsWith(p))

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/citizen/:path*', '/police/:path*', '/lawyer/:path*'],
}