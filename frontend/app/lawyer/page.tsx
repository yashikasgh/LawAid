'use client'

import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'
import { useEffect, useState } from 'react'

export default function LawyerDashboard() {
  const [user, setUser] = useState(getStoredUser())

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-navy">
            Lawyer Dashboard
          </h1>

          <p className="mt-2 text-gray-600">
            Welcome, {user?.email || 'Lawyer'}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            <div className="bg-white rounded-xl p-6 shadow">
              <h2 className="text-lg font-bold text-navy">
                My Cases
              </h2>
              <p className="mt-2 text-gray-600">
                View and manage assigned cases.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow">
              <h2 className="text-lg font-bold text-navy">
                Case Research
              </h2>
              <p className="mt-2 text-gray-600">
                Review case documents and legal information.
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow">
              <h2 className="text-lg font-bold text-navy">
                IPC → BNS
              </h2>
              <p className="mt-2 text-gray-600">
                Convert IPC sections to corresponding BNS sections.
              </p>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}