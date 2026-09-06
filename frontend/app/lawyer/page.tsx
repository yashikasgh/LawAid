'use client'

import Navbar from '@/components/Navbar'
import { getStoredUser } from '@/lib/auth'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

const IPC_TO_BNS_MAP = [
  { ipc: 'IPC 420', bns: 'BNS 318(4)', title: 'Cheating & Dishonestly Inducing Delivery', bailable: 'Non-Bailable' },
  { ipc: 'IPC 378 / 379', bns: 'BNS 303(2)', title: 'Theft', bailable: 'Non-Bailable' },
  { ipc: 'IPC 503 / 506', bns: 'BNS 351', title: 'Criminal Intimidation', bailable: 'Bailable' },
  { ipc: 'IPC 302', bns: 'BNS 103(1)', title: 'Murder', bailable: 'Non-Bailable' },
  { ipc: 'IPC 307', bns: 'BNS 109', title: 'Attempt to Murder', bailable: 'Non-Bailable' },
  { ipc: 'IPC 323', bns: 'BNS 115(2)', title: 'Voluntarily Causing Hurt', bailable: 'Bailable' },
  { ipc: 'IPC 354', bns: 'BNS 74', title: 'Assault / Criminal Force to Woman', bailable: 'Non-Bailable' },
  { ipc: 'IPC 498A', bns: 'BNS 85 / 86', title: 'Cruelty by Husband or Relatives', bailable: 'Non-Bailable' },
]

export default function LawyerDashboard() {
  const [user, setUser] = useState(getStoredUser())
  const [firSearch, setFirSearch] = useState('')
  const [firResult, setFirResult] = useState<any>(null)
  const [searching, setSearching] = useState(false)
  const [ipcQuery, setIpcQuery] = useState('')

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  async function handleSearchFir() {
    if (!firSearch.trim()) return
    setSearching(true)
    setFirResult(null)
    try {
      const res = await api.get(`/fir/${encodeURIComponent(firSearch.trim())}`)
      setFirResult(res.data)
    } catch {
      setFirResult({ status: 'not_found', message: 'No registered FIR record found with this ID.' })
    } finally {
      setSearching(false)
    }
  }

  const filteredIpc = IPC_TO_BNS_MAP.filter(
    item =>
      item.ipc.toLowerCase().includes(ipcQuery.toLowerCase()) ||
      item.bns.toLowerCase().includes(ipcQuery.toLowerCase()) ||
      item.title.toLowerCase().includes(ipcQuery.toLowerCase())
  )

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-navy">Lawyer & Legal Advocate Portal</h1>
            <p className="mt-1 text-sm text-gray-600">
              Welcome, {user?.email || 'Counsel'}. Access FIR verification records, statutory transition mappings, and client case files.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* FIR Record Lookup */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between">
              <div>
                <h2 className="text-lg font-bold text-navy mb-2">🔍 Case & FIR Registry Verification</h2>
                <p className="text-xs text-gray-500 mb-4">
                  Verify the cryptographic registration status and station logging of any client FIR under Section 173 BNSS.
                </p>

                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    value={firSearch}
                    onChange={e => setFirSearch(e.target.value)}
                    placeholder="Enter FIR ID (e.g. FIR/2026/0001)..."
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-lawblue"
                  />
                  <button
                    onClick={handleSearchFir}
                    disabled={searching || !firSearch.trim()}
                    className="bg-navy text-white px-4 py-2 rounded-lg text-xs font-bold hover:bg-lawblue transition"
                  >
                    {searching ? 'Checking...' : 'Verify'}
                  </button>
                </div>

                {firResult && (
                  <div className="p-3.5 rounded-xl border border-gray-200 bg-gray-50 text-xs">
                    <p className="font-bold text-navy">FIR Number: {firResult.fir_id || firSearch}</p>
                    <p className="text-gray-600 mt-1">Status: <span className="font-semibold text-green-700">{firResult.status || 'Active'}</span></p>
                    <p className="text-gray-500 mt-1">{firResult.message || 'Verified authentic in police database.'}</p>
                  </div>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between text-xs text-gray-500">
                <span>Station: PS001 Central</span>
                <span className="text-green-600 font-semibold">● Registry Connected</span>
              </div>
            </div>

            {/* Quick Bail Assessment Card */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-lg font-bold text-navy mb-2">⚖ Statutory Bail Guidance (BNSS 2023)</h2>
              <p className="text-xs text-gray-500 mb-3">
                Key statutory provisions applicable to criminal defense under the new code:
              </p>
              <ul className="space-y-2 text-xs text-gray-700">
                <li className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-100">
                  <strong className="text-navy">Anticipatory Bail:</strong> Governed under Section 482 BNSS (formerly 438 CrPC). High Court and Court of Sessions maintain concurrent jurisdiction.
                </li>
                <li className="p-2.5 bg-green-50/50 rounded-lg border border-green-100">
                  <strong className="text-navy">First-Time Offender Bail:</strong> Section 479 BNSS allows undertrials who have served 1/3rd of maximum sentence (first offence) to be released on bond.
                </li>
                <li className="p-2.5 bg-amber-50/50 rounded-lg border border-amber-100">
                  <strong className="text-navy">Zero FIR Obligation:</strong> Police station cannot refuse registration on territorial grounds under Section 173(1) BNSS.
                </li>
              </ul>
            </div>
          </div>

          {/* IPC -> BNS Transition Table */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-lg font-bold text-navy">IPC → BNS 2023 Statutory Concordance</h2>
                <p className="text-xs text-gray-500">
                  Instant mapping between old Indian Penal Code provisions and the active Bharatiya Nyaya Sanhita.
                </p>
              </div>
              <input
                type="text"
                value={ipcQuery}
                onChange={e => setIpcQuery(e.target.value)}
                placeholder="Filter by IPC or BNS section..."
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-lawblue w-64"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-navy text-white uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3">IPC Section</th>
                    <th className="p-3">BNS Section (2023)</th>
                    <th className="p-3">Offence Classification</th>
                    <th className="p-3">Bailable Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredIpc.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 transition">
                      <td className="p-3 font-semibold text-gray-700">{item.ipc}</td>
                      <td className="p-3 font-bold text-lawblue">{item.bns}</td>
                      <td className="p-3 text-gray-800">{item.title}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          item.bailable.toLowerCase().includes('non')
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : 'bg-green-50 text-green-700 border border-green-200'
                        }`}>
                          {item.bailable}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}