// app/page.tsx
import Link from 'next/link'
import Navbar from '@/components/Navbar'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      {/* Hero Section */}
      <section className="bg-navy text-white py-20 px-8">
        <div className="max-w-4xl">
          <h1 className="text-5xl font-bold mb-4">Justice Made Simple.</h1>
          <p className="text-xl text-blue-200 mb-2">
            AI-powered legal guidance for every Indian citizen.
          </p>
          <p className="text-blue-300 mb-8">
            Understand your FIR. Know your rights. Get help instantly.
          </p>
          <div className="flex gap-4">
            <Link
              href="/citizen/complaint"
              className="bg-white text-navy px-6 py-3 rounded-xl font-bold hover:bg-gray-100"
            >
              Get Legal Help
            </Link>
            <Link
              href="/citizen/understand"
              className="bg-gold text-navy px-6 py-3 rounded-xl font-bold hover:opacity-90"
            >
              Upload Your FIR
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="py-12 px-8">
        <h2 className="text-2xl font-bold text-navy text-center mb-8">What can LawAid do for you?</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
          {[
            { icon: '⚖', title: 'File a Complaint', desc: 'Describe your incident. Get BNS sections instantly.', href: '/citizen/complaint', color: 'bg-lawblue' },
            { icon: '📄', title: 'Understand FIR', desc: 'Upload FIR and get plain-language explanation.', href: '/citizen/understand', color: 'bg-lawblue' },
            { icon: '💬', title: 'Legal Chat', desc: 'Ask any legal question, get AI-powered answers.', href: '/citizen/chat', color: 'bg-navy' },
            { icon: '🔍', title: 'BNS Search', desc: 'Search all 358 BNS sections instantly.', href: '/bns-search', color: 'bg-lawblue' },
          ].map(card => (
            <Link
              key={card.title}
              href={card.href}
              className="bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl transition hover:-translate-y-1"
            >
              <div className={`${card.color} text-white p-4`}>
                <span className="text-3xl">{card.icon}</span>
              </div>
              <div className="p-4">
                <h3 className="font-bold text-navy mb-2">{card.title}</h3>
                <p className="text-sm text-gray-500">{card.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}