// components/Navbar.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Navbar() {
  const path = usePathname()
  const links = [
    { href: '/', label: 'Home' },
    { href: '/bns-search', label: 'BNS Search' },
    { href: '/citizen', label: 'Citizen' },
    { href: '/police', label: 'Police' },
    { href: '/lawyer', label: 'Lawyer' },
  ]

  return (
    <nav className="bg-navy text-white px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-lg">
      <Link href="/" className="text-xl font-bold flex items-center gap-2">
        <span className="text-gold">⚖</span> LawAid
      </Link>
      <div className="flex gap-8">
        {links.map(l => (
          <Link
            key={l.href}
            href={l.href}
            className={`text-sm font-medium hover:text-gold transition ${
              path === l.href ? 'text-gold border-b-2 border-gold' : 'text-white'
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>
      <Link href="/login" className="bg-gold text-navy px-4 py-2 rounded-lg font-bold text-sm hover:opacity-90">
        Login
      </Link>
    </nav>
  )
}