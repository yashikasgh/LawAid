'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getStoredUser, logout, ROLE_ROUTES } from '@/lib/auth'

export default function Navbar() {
  const path = usePathname()
  const router = useRouter()

  const [user, setUser] = useState<ReturnType<typeof getStoredUser>>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setUser(getStoredUser())
  }, [path])

  const role = user?.role?.toLowerCase()

  const links = [
    { href: '/', label: 'Home' },
    { href: '/bns-search', label: 'BNS Search' },
    { href: '/citizen', label: 'Citizen' },
    { href: '/police', label: 'Police' },
    { href: '/lawyer', label: 'Lawyer' },
  ]

  async function handleLogout() {
    await logout()
    setUser(null)
    setMenuOpen(false)

    // Replace prevents browser Back from returning to the dashboard.
    router.replace('/login')
    router.refresh()
  }

  return (
    <nav className="bg-navy text-white px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-lg">
      <Link
        href="/"
        className="text-xl font-bold flex items-center gap-2"
      >
        <span className="text-gold">⚖</span> LawAid
      </Link>

      <div className="flex gap-8">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`text-sm font-medium hover:text-gold transition ${
              path === l.href
                ? 'text-gold border-b-2 border-gold'
                : 'text-white'
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>

      {user ? (
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="bg-gold text-navy px-4 py-2 rounded-lg font-bold text-sm hover:opacity-90"
          >
            {role ? role.charAt(0).toUpperCase() + role.slice(1) : 'Account'} ▾
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-lg bg-white shadow-lg overflow-hidden">
              <Link
                href={ROLE_ROUTES[role || 'citizen'] || '/'}
                onClick={() => setMenuOpen(false)}
                className="block px-4 py-3 text-sm text-navy hover:bg-gray-100"
              >
                My Dashboard
              </Link>

              <button
                onClick={handleLogout}
                className="block w-full text-left px-4 py-3 text-sm text-red-600 hover:bg-gray-100"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      ) : (
        <Link
          href="/login"
          className="bg-gold text-navy px-4 py-2 rounded-lg font-bold text-sm hover:opacity-90"
        >
          Login
        </Link>
      )}
    </nav>
  )
}