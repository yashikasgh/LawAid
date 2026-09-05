// components/CitizenSidebar.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/citizen', icon: '🏠', label: 'Dashboard' },
  { href: '/citizen/complaint', icon: '📝', label: 'File Complaint' },
  { href: '/citizen/understand', icon: '📄', label: 'My FIRs' },
  { href: '/citizen/chat', icon: '💬', label: 'Legal Chat' },
  { href: '/bns-search', icon: '🔍', label: 'BNS Search' },
]

export default function CitizenSidebar() {
  const path = usePathname()
  return (
    <aside className="w-48 bg-lblue h-full min-h-screen p-4 flex flex-col gap-1">
      <p className="text-xs font-bold text-navy mb-3 uppercase tracking-wider">My Dashboard</p>
      {links.map(l => (
        <Link
          key={l.href}
          href={l.href}
          className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
            path === l.href ? 'bg-lawblue text-white' : 'text-gray-700 hover:bg-white'
          }`}
        >
          <span>{l.icon}</span> {l.label}
        </Link>
      ))}
    </aside>
  )
}