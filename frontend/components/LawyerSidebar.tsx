'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  ArrowLeft,
  FileText,
  FolderOpen,
  Sparkles,
  CalendarDays,
  Search,
  FileSignature,
  BookOpen,
  CheckCircle2,
} from 'lucide-react'

const navItems = [
  { href: '/lawyer/overview', label: 'Case Overview', icon: FileText, completed: true },
  { href: '/lawyer/documents', label: 'Documents', icon: FolderOpen, completed: true },
  { href: '/lawyer/analysis', label: 'AI Analysis', icon: Sparkles, completed: true },
  { href: '/lawyer/timeline', label: 'Case Timeline', icon: CalendarDays, completed: false },
  { href: '/lawyer/research', label: 'Legal Research', icon: Search, completed: false },
  { href: '/lawyer/draft', label: 'Draft Petition', icon: FileSignature, completed: false },
  { href: '/lawyer/summary', label: 'Case Summary', icon: BookOpen, completed: false },
]

export default function LawyerSidebar({ caseId }: { caseId: string | null }) {
  const pathname = usePathname()

  // Find the index of the active tab
  const activeIndex = navItems.findIndex(item => pathname.startsWith(item.href))

  return (
    <aside className="fixed left-0 top-[64px] bottom-0 w-[260px] flex-col bg-[#0b274a] shadow-xl z-10 hidden lg:flex">
      <div className="p-5">
        <Link 
          href="/lawyer" 
          className="flex items-center justify-center gap-2 rounded-full bg-[#d2a14b] px-4 py-2.5 text-sm font-bold text-[#0b274a] transition hover:bg-[#e4b55c] w-full"
        >
          <ArrowLeft size={18} />
          Back to Case
        </Link>
      </div>

      <div className="px-5 mt-2">
        <div className="flex items-center gap-3">
          <div className="h-[1px] flex-1 bg-[#d2a14b]/40"></div>
          <span className="text-[10px] font-bold tracking-widest text-[#d2a14b] uppercase">Case Workflow</span>
          <div className="h-[1px] flex-1 bg-[#d2a14b]/40"></div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-5 px-3 flex flex-col gap-1">
        {navItems.map((item, index) => {
          const isActive = pathname.startsWith(item.href)
          const isCompleted = index <= activeIndex
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-all ${
                isActive 
                  ? 'bg-[#1b3d63] text-white shadow-inner relative overflow-hidden'
                  : 'text-[#8ba2ba] hover:bg-[#123152] hover:text-white'
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#d2a14b]" />
              )}
              <div className="flex items-center gap-3">
                <item.icon 
                  size={18} 
                  className={isActive ? 'text-[#d2a14b]' : 'text-[#8ba2ba] group-hover:text-white'} 
                />
                <span className={isActive ? 'font-bold' : ''}>{item.label}</span>
              </div>
              
              {/* Checkmark icon for completed states */}
              {isCompleted && item.href !== '/lawyer/summary' && (
                <CheckCircle2 size={16} className={isActive ? "text-emerald-400" : "text-emerald-500"} />
              )}
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto p-5 border-t border-white/5 bg-[#081e3a]">
        <div className="rounded-lg bg-[#0e2a4c] p-4 text-xs">
          <p className="font-bold text-white mb-1">
            {caseId ? `Case #${caseId.substring(0, 10).toUpperCase()}` : 'Loading Case...'}
          </p>
          <p className="text-[#8ba2ba]">
            Last updated<br/>
            {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}, {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute:'2-digit' })}
          </p>
        </div>
      </div>
    </aside>
  )
}
