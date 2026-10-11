'use client'

import Link from 'next/link'

const pages = [
  ['Documents', '/lawyer/documents'],
  ['AI Analysis', '/lawyer/analysis'],
  ['Timeline', '/lawyer/timeline'],
  ['Summary & Export', '/lawyer/summary'],
]

export default function LawyerTestHeader({ title, caseId }: { title: string; caseId?: string | null }) {
  return (
    <header className="mb-7 border-b border-[#d9cfbb] pb-5">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#a67518]">Lawyer portal · integration test UI</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="font-serif text-3xl font-bold text-[#0f305b]">{title}</h1><p className="mt-1 text-sm text-slate-600">Real backend data only. {caseId ? `Case: ${caseId}` : 'Loading case workspace…'}</p></div>
        <Link href="/lawyer" className="text-sm font-semibold text-[#0f305b] hover:text-[#c28b19]">← Dashboard</Link>
      </div>
      <nav className="mt-5 flex flex-wrap gap-2" aria-label="Lawyer workflow">
        {pages.map(([label, href]) => <Link key={href} href={href} className="rounded-lg border border-[#d6c9aa] bg-white px-3 py-2 text-sm font-medium text-[#0f305b] hover:border-[#c28b19]">{label}</Link>)}
      </nav>
    </header>
  )
}
