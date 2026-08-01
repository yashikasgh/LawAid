// app/citizen/page.tsx
'use client'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import { getStoredUser } from '@/lib/auth'

export default function CitizenDashboard() {
  const user = getStoredUser()

  const cards = [
    { icon: '📝', title: 'File a Complaint', desc: 'Describe your incident. Get BNS sections instantly.', href: '/citizen/complaint', color: 'bg-lawblue' },
    { icon: '📄', title: 'Understand FIR', desc: 'Upload FIR and get plain-language explanation.', href: '/citizen/understand', color: 'bg-lawblue' },
    { icon: '💬', title: 'Legal Chat', desc: 'Ask any legal question, get AI-powered answers.', href: '/citizen/chat', color: 'bg-navy' },
    { icon: '🔍', title: 'BNS Search', desc: 'Search all BNS sections instantly.', href: '/bns-search', color: 'bg-lawblue' },
  ]

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8">
          <h1 className="text-3xl font-bold text-navy mb-1">
            Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''} 👋
          </h1>
          <p className="text-gray-500 mb-8">What would you like to do today?</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {cards.map(card => (
              <Link
                key={card.title}
                href={card.href}
                className="bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl transition hover:-translate-y-1"
              >
                <div className={`${card.color} text-white p-4`}>
                  <span className="text-3xl">{card.icon}</span>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-navy mb-2">{card.title}</h3>
                  <p className="text-sm text-gray-500">{card.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </main>
      </div>
    </div>
  )
}