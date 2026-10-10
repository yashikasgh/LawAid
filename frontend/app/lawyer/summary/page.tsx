'use client'

import { useCallback, useEffect, useState } from 'react'
import LawyerCaseLayout from '@/components/LawyerCaseLayout'
import StepProgress from '@/components/StepProgress'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'
import { BookOpen, CheckCircle2, Download,Check, FileText, ChevronRight, Scale, Clock, Users } from 'lucide-react'

type Summary = { case_id: string; case_number: string; current_stage?: string | null; executive_summary: string; key_facts: Array<{ text?: string }>; bns_sections: Array<{ section_number?: string; title?: string | null }>; timeline_preview: Array<{ id: string; date: string; title: string; description: string }> }

export default function SummaryPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [activeTab, setActiveTab] = useState('Overview')
  
  const [options, setOptions] = useState({ 
    include_legal_analysis: true, 
    include_timeline: true, 
    include_evidence: true,
    include_original_documents: false
  })

  const load = useCallback(async (id: string) => { 
    setLoading(true); setError(''); 
    try { 
      const r = await lawyerCaseAPI.getSummary(id); 
      setSummary(r.data); 
    } 
    catch (e) { setError(apiError(e, 'Could not load case summary.')) } 
    finally { setLoading(false) } 
  }, [])

  useEffect(() => { 
    lawyerDocumentsAPI.workspace().then(r => { 
      setCaseId(r.data.id); 
      return load(r.data.id) 
    }).catch(e => { 
      setError(apiError(e, 'Could not load your case workspace.')); 
      setLoading(false) 
    }) 
  }, [load])

  async function exportPackage() { 
    if (!caseId) return; 
    setWorking(true); setError(''); setSuccess(''); 
    try { 
      // Map UI options to backend API parameters
      const exportPayload = {
        include_executive_summary: true, // Always include overview
        include_key_facts: true,
        include_bns_sections: options.include_legal_analysis,
        include_timeline: options.include_timeline,
        include_original_documents: options.include_original_documents
      }
      const r = await lawyerCaseAPI.export(caseId, exportPayload); 
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' })); 
      const a = document.createElement('a'); 
      a.href = url; 
      a.download = `LawAid_Case_${caseId.substring(0,8)}.pdf`; 
      a.click(); 
      URL.revokeObjectURL(url); 
      setSuccess('PDF generated successfully.') 
    } 
    catch (e) { setError(apiError(e, 'Could not generate the PDF package.')) } 
    finally { setWorking(false) } 
  }

  const tabs = [
    { id: 'Overview', icon: FileText },
    { id: 'Complainant & Accused', icon: Users },
    { id: 'Incident Timeline', icon: Clock },
    { id: 'Legal Analysis', icon: Scale }
  ]

  return (
    <LawyerCaseLayout caseId={caseId}>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Header */}
        <header className="mb-8 text-center relative">
          <div className="flex items-center justify-center gap-4 mb-4">
            <div className="h-[1px] w-12 bg-[#d2a14b]/60"></div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d2a14b]">
              Lawyer Portal
            </p>
            <div className="h-[1px] w-12 bg-[#d2a14b]/60"></div>
          </div>
          <h1 className="font-serif text-4xl font-bold tracking-tight text-[#0f305b] sm:text-5xl">
            Case Summary & Export
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-[#36516e]">
            Review the final case summary and export it to a formatted PDF.
          </p>
        </header>

        <StepProgress 
          steps={['Upload Documents', 'AI Case Analysis', 'Case Timeline', 'Legal Research', 'Draft Petition']} 
          current={4} 
        />

        <ApiMessage error={error} success={success} />

        <div className="grid gap-6 lg:grid-cols-[1fr_320px] items-start mt-8">
          
          {/* Main Content Area - Tabs & Details */}
          <section className="rounded-2xl border border-white/80 bg-white/90 shadow-[0_15px_40px_rgba(18,51,91,0.06)] backdrop-blur-xl flex flex-col min-h-[600px] overflow-hidden">
            <div className="flex border-b border-[#eee8dd] overflow-x-auto bg-[#fdfdfc]">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-bold transition-all border-b-2 whitespace-nowrap ${
                    activeTab === tab.id 
                      ? 'border-[#0f305b] text-[#0f305b] bg-white' 
                      : 'border-transparent text-[#64748b] hover:text-[#0f305b] hover:bg-slate-50'
                  }`}
                >
                  <tab.icon size={16} className={activeTab === tab.id ? 'text-[#c28b19]' : 'text-slate-400'} />
                  {tab.id}
                </button>
              ))}
            </div>

            <div className="p-8 flex-1">
              {loading ? (
                <p className="text-center py-10 text-[#64748b]">Loading summary…</p>
              ) : activeTab === 'Overview' ? (
                <div className="space-y-8 max-w-3xl">
                  <div>
                    <h3 className="font-serif text-xl font-bold text-[#0f305b] mb-4 flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-[#c28b19]"></div>
                      Key Case Facts
                    </h3>
                    {summary?.key_facts?.length ? (
                      <ul className="space-y-3">
                        {summary.key_facts.map((fact, i) => (
                          <li key={i} className="flex gap-3 text-sm text-[#36516e] leading-relaxed">
                            <ChevronRight size={16} className="text-[#c28b19] shrink-0 mt-0.5" />
                            <span>{fact.text}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-[#64748b] italic ml-5">No key facts extracted.</p>
                    )}
                  </div>

                  <div>
                    <h3 className="font-serif text-xl font-bold text-[#0f305b] mb-4 flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-[#c28b19]"></div>
                      Relevant BNS Sections
                    </h3>
                    {summary?.bns_sections?.length ? (
                      <div className="grid gap-3 sm:grid-cols-2">
                        {summary.bns_sections.map((sec, i) => (
                          <div key={i} className="rounded-xl border border-[#e6e0d4] p-4 bg-[#fdfdfb]">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="rounded-md bg-blue-50 text-[#1c64f2] px-2 py-0.5 text-xs font-bold border border-blue-100">
                                Section {sec.section_number}
                              </span>
                            </div>
                            <p className="text-sm font-semibold text-[#0f305b] line-clamp-2">
                              {sec.title || 'Description not available'}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-[#64748b] italic ml-5">No BNS sections identified.</p>
                    )}
                  </div>
                </div>
              ) : activeTab === 'Incident Timeline' ? (
                <div>
                  <h3 className="font-serif text-xl font-bold text-[#0f305b] mb-6 flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#c28b19]"></div>
                    Timeline Preview
                  </h3>
                  {summary?.timeline_preview?.length ? (
                    <div className="relative pl-6 space-y-6 before:absolute before:inset-0 before:ml-2 before:-translate-x-px before:bg-[#e6e0d4] before:w-[2px] max-w-2xl">
                      {summary.timeline_preview.map((e, idx) => (
                        <div key={e.id || idx} className="relative">
                          <div className="absolute left-[-29px] top-1 h-3 w-3 rounded-full border-[3px] border-[#c28b19] bg-white"></div>
                          <div className="flex gap-4">
                            <div className="w-24 shrink-0">
                              <p className="text-[11px] font-bold text-[#0f305b]">{e.date}</p>
                            </div>
                            <div className="flex-1 pb-4">
                              <p className="text-sm font-bold text-[#0f305b] mb-1">{e.title}</p>
                              <p className="text-xs text-[#36516e] leading-relaxed">{e.description}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[#64748b] italic ml-5">No timeline events extracted.</p>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-[#64748b]">
                  <p className="text-center font-medium">Content for this tab is compiled in the final PDF.</p>
                  <p className="text-sm mt-2">Check the Export Options panel to include it.</p>
                </div>
              )}
            </div>
          </section>

          {/* Right Sidebar - Export Options */}
          <aside className="space-y-6">
            <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.06)] backdrop-blur-xl">
              <div className="flex items-center gap-2 text-[#0f305b] mb-4">
                <Download size={20} />
                <h3 className="font-serif text-xl font-bold">Export Options</h3>
              </div>
              
              <div className="mb-6 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
                <div className="flex items-center gap-2 text-emerald-600 mb-1.5">
                  <CheckCircle2 size={16} className="fill-emerald-100" />
                  <span className="text-sm font-bold">Ready for Export</span>
                </div>
                <p className="text-xs text-emerald-700/80 leading-relaxed">
                  The case summary has been compiled successfully. Select sections to include in the final PDF export.
                </p>
              </div>
              
              <div className="space-y-3 mb-6">
                {[
                  { id: 'include_legal_analysis', label: 'Include Legal Analysis' },
                  { id: 'include_timeline', label: 'Include Full Timeline' },
                  { id: 'include_evidence', label: 'Include Extracted Evidence' }
                ].map(opt => (
                  <label key={opt.id} className="flex items-center gap-3 cursor-pointer group p-2 rounded-lg hover:bg-slate-50 transition -mx-2">
                    <div className={`relative flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${
                      options[opt.id as keyof typeof options] 
                        ? 'border-[#0f305b] bg-[#0f305b]' 
                        : 'border-[#cbd5e1] bg-white group-hover:border-[#94a3b8]'
                    }`}>
                      {options[opt.id as keyof typeof options] && <Check size={14} className="text-white" strokeWidth={3} />}
                    </div>
                    <span className="text-sm font-semibold text-[#0f305b]">{opt.label}</span>
                  </label>
                ))}
              </div>
              
              <button 
                onClick={exportPackage} 
                disabled={working} 
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#c28b19] py-3.5 font-bold text-white shadow-sm transition hover:bg-[#a87815] hover:shadow disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {working ? (
                  'Generating PDF...'
                ) : (
                  <>
                    <Download size={18} />
                    Generate PDF
                  </>
                )}
              </button>
            </section>
          </aside>
          
        </div>
      </div>
    </LawyerCaseLayout>
  )
}
