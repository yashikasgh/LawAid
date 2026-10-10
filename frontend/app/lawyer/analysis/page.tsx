'use client'

import { useCallback, useEffect, useState } from 'react'
import LawyerCaseLayout from '@/components/LawyerCaseLayout'
import StepProgress from '@/components/StepProgress'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'
import { FileText, FileUp, ShieldAlert, FileSearch, Edit3, Image as ImageIcon, MapPin, Calendar, CheckCircle2, User, Users, FileCheck, CircleDollarSign } from 'lucide-react'

type AnalysisResponse = { status: string; analysis: Record<string, unknown> | null; error?: string | null }
type CaseDocument = { id: string; name: string; type: string; size_bytes: number; status: string; pages: number }

export default function LawyerAnalysisPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [documents, setDocuments] = useState<CaseDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [activeTab, setActiveTab] = useState('Timeline of Events')
  const [showEditor, setShowEditor] = useState(false)
  const [draft, setDraft] = useState('')

  const load = useCallback(async (id: string) => {
    setLoading(true); setError('')
    try { 
      const [analysisRes, docsRes] = await Promise.all([
        lawyerCaseAPI.getAnalysis(id),
        lawyerDocumentsAPI.list(id)
      ]);
      setResult(analysisRes.data); 
      setDocuments(docsRes.data);
      if (analysisRes.data.analysis) {
        setDraft(JSON.stringify(analysisRes.data.analysis, null, 2))
      }
    }
    catch (e) { setError(apiError(e, 'Could not load case analysis.')) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { 
    lawyerDocumentsAPI.workspace().then((r) => { 
      setCaseId(r.data.id); 
      return load(r.data.id) 
    }).catch((e) => { 
      setError(apiError(e, 'Could not load your case workspace.')); 
      setLoading(false) 
    }) 
  }, [load])

  async function runAnalysis() {
    if (!caseId) return
    setWorking(true); setError(''); setSuccess('')
    try { await lawyerCaseAPI.analyze(caseId); setSuccess('Analysis completed. Information updated.'); await load(caseId) }
    catch (e) { setError(apiError(e, 'Analysis could not be completed.')) }
    finally { setWorking(false) }
  }

  async function save() {
    if (!caseId) return
    let payload: unknown
    try { payload = JSON.parse(draft) } catch { setError('Analysis edits must be valid JSON.'); return }
    setWorking(true); setError(''); setSuccess('')
    try { 
      const response = await lawyerCaseAPI.saveAnalysis(caseId, payload); 
      setResult({ status: response.data.status, analysis: response.data.analysis }); 
      setSuccess('Corrections saved.'); 
      setDraft(JSON.stringify(response.data.analysis, null, 2))
      setShowEditor(false)
    }
    catch (e) { setError(apiError(e, 'Could not save analysis corrections.')) }
    finally { setWorking(false) }
  }

  const analysis = result?.analysis || {}
  const list = (key: string) => Array.isArray(analysis[key]) ? analysis[key] as Array<Record<string, unknown>> : []
  
  const parties = list('parties')
  const complainant = parties.find(p => String(p.role).toLowerCase().includes('complainant') || String(p.role).toLowerCase().includes('victim'))
  const accused = parties.find(p => String(p.role).toLowerCase().includes('accused'))
  
  const locations = list('locations')
  const mainLocation = locations[0]
  
  const bnsSections = list('bns_sections')
  const evidence = list('evidence')
  const keyFacts = list('key_facts')
  const timeline = list('timeline_events')

  const formatSize = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`

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
            AI Case Analysis
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-[#36516e]">
            Extracting key information, facts, and entities from your documents.
          </p>
          <div className="absolute right-0 top-6">
            <button className="flex items-center gap-2 rounded-xl border border-[#d6c9aa] bg-white px-4 py-2 text-sm font-semibold text-[#0f305b] hover:bg-slate-50 transition">
              <FileText size={16} className="text-[#d2a14b]" />
              View Original Documents
            </button>
          </div>
        </header>

        <StepProgress 
          steps={['Upload Documents', 'AI Case Analysis', 'Case Timeline', 'Legal Research', 'Draft Petition']} 
          current={1} 
        />

        <ApiMessage error={error} success={success} />
        
        <div className="grid gap-6 lg:grid-cols-[280px_1fr] items-start">
          
          {/* Uploaded Documents Sidebar */}
          <aside className="rounded-2xl border border-white/80 bg-white/90 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.08)] backdrop-blur-xl">
            <div className="flex items-center gap-3 mb-5 border-b border-[#eee8dd] pb-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#f8f6f1] text-[#c28b19]">
                <FileText size={20} />
              </div>
              <div>
                <h2 className="font-serif text-lg font-bold text-[#0f305b]">Uploaded Documents</h2>
                <p className="text-xs text-[#64748b] mt-0.5">{documents.length} documents processed successfully</p>
              </div>
            </div>
            
            <div className="space-y-3">
              {documents.length === 0 && !loading && (
                <p className="text-sm text-slate-500 py-4 text-center">No documents uploaded</p>
              )}
              {documents.map(doc => (
                <div key={doc.id} className="rounded-xl border border-[#e6e0d4] bg-white p-3 flex items-center justify-between shadow-sm">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white font-bold text-[10px] ${
                      doc.type.includes('pdf') ? 'bg-[#ff5a36]' : 
                      doc.type.includes('doc') ? 'bg-[#2368c4]' : 'bg-[#9845d4]'
                    }`}>
                      {doc.type.includes('pdf') ? 'PDF' : doc.type.includes('doc') ? 'DOC' : 'IMG'}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-[#0f305b] truncate">{doc.name}</p>
                      <p className="text-[10px] text-[#64748b] mt-0.5">{doc.pages || '?'} pages &bull; {formatSize(doc.size_bytes)}</p>
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-[#148c5f]">
                    Processed
                  </span>
                </div>
              ))}
            </div>
          </aside>

          {/* Main Content Area */}
          <div className="space-y-6">
            
            {loading ? (
              <div className="flex h-64 items-center justify-center rounded-2xl border border-white/80 bg-white/90 shadow-[0_15px_40px_rgba(18,51,91,0.08)]">
                <p className="text-[#36516e]">Loading analysis…</p>
              </div>
            ) : !result?.analysis ? (
              <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-[#cdbd97] bg-white p-8 text-center shadow-[0_15px_40px_rgba(18,51,91,0.08)]">
                <ShieldAlert className="text-[#d2a14b] mb-3" size={40} />
                <p className="font-semibold text-[#0f305b]">No analysis saved yet.</p>
                <p className="mt-2 text-sm text-[#64748b] mb-4">Upload and parse documents first, then run AI analysis.</p>
                <button onClick={runAnalysis} disabled={working} className="rounded-xl bg-[#0f305b] px-6 py-2.5 font-semibold text-white transition hover:bg-[#173f70] disabled:opacity-50">
                  {working ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </div>
            ) : (
              <>
                <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.08)]">
                  <div className="flex items-center justify-between mb-5 border-b border-[#eee8dd] pb-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f8f6f1] text-[#c28b19]">
                        <FileSearch size={20} />
                      </div>
                      <div>
                        <h2 className="font-serif text-xl font-bold text-[#0f305b]">Extracted Case Information</h2>
                        <p className="text-xs text-[#64748b] mt-0.5">Key facts and entities identified from your documents using AI.</p>
                      </div>
                    </div>
                    <button onClick={() => setShowEditor(!showEditor)} className="flex items-center gap-1.5 rounded-lg border border-[#e2d8c3] px-3 py-1.5 text-xs font-semibold text-[#64748b] hover:bg-slate-50 transition">
                      <Edit3 size={14} /> Edit Information
                    </button>
                  </div>
                  
                  {showEditor ? (
                    <div className="mt-4">
                      <p className="mb-2 text-sm text-[#64748b]">Edit persisted analysis payload directly. Ensure valid JSON.</p>
                      <textarea value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} className="min-h-[400px] w-full rounded-xl border border-[#e2d8c3] bg-slate-50 p-4 font-mono text-xs leading-5 focus:outline-none focus:ring-2 focus:ring-[#d2a14b]" />
                      <div className="mt-3 flex gap-2">
                        <button onClick={save} disabled={working} className="rounded-xl bg-[#0f305b] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#173f70] disabled:opacity-50">Save changes</button>
                        <button onClick={() => setShowEditor(false)} className="rounded-xl border border-slate-300 px-5 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {/* Grid Items */}
                      <div className="rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><User size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Complainant</p>
                          <p className="text-sm font-bold text-[#36516e] leading-snug">{complainant ? String(complainant.name) : 'Not mentioned'}</p>
                          <p className="text-[10px] text-[#64748b] mt-1">{complainant?.description ? String(complainant.description) : '-'}</p>
                        </div>
                      </div>
                      
                      <div className="rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><Users size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Accused</p>
                          <p className="text-sm font-bold text-[#36516e] leading-snug">{accused ? String(accused.name) : 'Not mentioned'}</p>
                          <p className="text-[10px] text-[#64748b] mt-1">{accused?.description ? String(accused.description) : '-'}</p>
                        </div>
                      </div>
                      
                      <div className="rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><Calendar size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Incident Date</p>
                          <p className="text-sm font-bold text-[#36516e] leading-snug">{timeline.length ? String(timeline[0].date || timeline[0].time || 'Unknown') : 'Not mentioned'}</p>
                          <p className="text-[10px] text-[#64748b] mt-1">Approx.</p>
                        </div>
                      </div>
                      
                      <div className="rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><MapPin size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Incident Location</p>
                          <p className="text-sm font-bold text-[#36516e] leading-snug line-clamp-2">{mainLocation ? String(mainLocation.text) : 'Not mentioned'}</p>
                          <p className="text-[10px] text-[#64748b] mt-1">{mainLocation?.type ? String(mainLocation.type) : '-'}</p>
                        </div>
                      </div>
                      
                      <div className="col-span-1 md:col-span-2 rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><ShieldAlert size={18} /></div>
                        <div className="flex-1">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Offence Type</p>
                          <p className="text-sm font-bold text-[#36516e]">{String(analysis.offence_type || 'Not mentioned')}</p>
                          <span className="inline-block mt-2 rounded bg-slate-100 px-2 py-0.5 text-[10px] text-[#64748b]">Physical Assault</span>
                        </div>
                      </div>
                      
                      <div className="col-span-1 md:col-span-2 rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><FileCheck size={18} /></div>
                        <div className="flex-1">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Relevant BNS Sections (Initial)</p>
                          <div className="flex flex-wrap gap-1.5 mt-1.5">
                            {bnsSections.slice(0, 3).map((sec, i) => (
                              <span key={i} className="rounded-full bg-blue-50 border border-blue-100 px-2 py-1 text-[10px] font-bold text-[#2368c4]">
                                Section {String(sec.section_number)}
                              </span>
                            ))}
                            {bnsSections.length > 3 && (
                              <span className="rounded-full bg-slate-50 border border-slate-200 px-2 py-1 text-[10px] font-bold text-[#64748b]">
                                +{bnsSections.length - 3} more
                              </span>
                            )}
                            {bnsSections.length === 0 && <span className="text-sm text-[#36516e]">None identified</span>}
                          </div>
                        </div>
                      </div>
                      
                      <div className="col-span-1 md:col-span-2 rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><CircleDollarSign size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Financial Details</p>
                          <p className="text-sm font-bold text-[#36516e]">Not mentioned</p>
                          <p className="text-[10px] text-[#64748b] mt-1">-</p>
                        </div>
                      </div>
                      
                      <div className="col-span-1 md:col-span-2 rounded-xl border border-[#e6e0d4] bg-[#fdfdfb] p-4 flex gap-3 shadow-sm">
                        <div className="mt-0.5 text-[#c28b19]"><FileText size={18} /></div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-[#0f305b] mb-1">Key Evidence</p>
                          <p className="text-sm font-bold text-[#36516e]">{evidence.slice(0, 2).map(e => String(e.name || e.type)).join(', ') || 'Not mentioned'}</p>
                          <p className="text-[10px] text-[#64748b] mt-1">{evidence.length > 2 ? `+${evidence.length - 2} more items` : '-'}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </section>

                <section className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_15px_40px_rgba(18,51,91,0.08)]">
                  <div className="flex items-center justify-between mb-5 border-b border-[#eee8dd] pb-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f8f6f1] text-[#c28b19]">
                        <Calendar size={20} />
                      </div>
                      <div>
                        <h2 className="font-serif text-xl font-bold text-[#0f305b]">Key Facts Extracted</h2>
                        <p className="text-xs text-[#64748b] mt-0.5">Important facts, events and entities identified from all documents.</p>
                      </div>
                    </div>
                    <button className="flex items-center gap-1.5 rounded-lg border border-[#e2d8c3] px-3 py-1.5 text-xs font-semibold text-[#c28b19] hover:bg-slate-50 transition bg-white">
                      <FileText size={14} /> View Full Extracted Text
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2 border-b border-[#eee8dd] pb-3 mb-5">
                    {[
                      { name: 'Timeline of Events', count: timeline.length },
                      { name: 'Parties', count: parties.length },
                      { name: 'Locations', count: locations.length },
                      { name: 'Objects', count: 1 },
                      { name: 'Financial Details', count: 0 },
                      { name: 'Key Facts', count: keyFacts.length }
                    ].map(tab => (
                      <button 
                        key={tab.name}
                        onClick={() => setActiveTab(tab.name === 'Parties' ? 'Parties' : tab.name === 'Locations' ? 'Locations' : tab.name === 'Key Facts' ? 'Key Facts' : 'Timeline of Events')}
                        className={`rounded-lg px-4 py-2 text-[11px] font-bold transition flex items-center gap-1.5 ${
                          activeTab === tab.name || (activeTab === 'Timeline of Events' && tab.name === 'Timeline of Events')
                            ? 'bg-[#c28b19] text-white' 
                            : 'border border-[#e2d8c3] text-[#36516e] hover:bg-slate-50 bg-white'
                        }`}
                      >
                        {tab.name === 'Timeline of Events' && <Calendar size={14} />}
                        {tab.name === 'Parties' && <Users size={14} />}
                        {tab.name === 'Locations' && <MapPin size={14} />}
                        {tab.name === 'Objects' && <ImageIcon size={14} />}
                        {tab.name === 'Financial Details' && <CircleDollarSign size={14} />}
                        {tab.name === 'Key Facts' && <FileText size={14} />}
                        {tab.name === 'Timeline of Events' ? 'Timeline of Events' : `${tab.name} (${tab.count})`}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-6">
                    {activeTab === 'Timeline of Events' && (
                      <div className="relative pl-6 space-y-6 before:absolute before:inset-0 before:ml-2 before:-translate-x-px before:bg-[#e6e0d4] before:w-[2px]">
                        {timeline.length > 0 ? timeline.map((event, idx) => (
                          <div key={idx} className="relative">
                            <div className="absolute left-[-29px] top-1 h-3 w-3 rounded-full border-[3px] border-[#c28b19] bg-white"></div>
                            <div className="flex gap-4">
                              <div className="w-24 shrink-0">
                                <p className="text-[11px] font-bold text-[#0f305b]">{String(event.date || 'Unknown Date')}</p>
                                <p className="text-[10px] text-[#64748b]">{String(event.time || '')}</p>
                              </div>
                              <div className="flex-1 pb-4">
                                <p className="text-sm font-bold text-[#0f305b] mb-1">{String(event.title || 'Event')}</p>
                                <p className="text-xs text-[#36516e] leading-relaxed">{String(event.description || event.text || '')}</p>
                              </div>
                            </div>
                          </div>
                        )) : <p className="text-sm text-slate-500">No events extracted.</p>}
                      </div>
                    )}
                    
                    {activeTab === 'Parties' && (
                      <ul className="list-disc pl-5 space-y-2 text-sm text-[#36516e]">
                        {parties.map((p, i) => <li key={i}><strong>{String(p.name)}</strong>: {String(p.role || p.description || '')}</li>)}
                      </ul>
                    )}
                    
                    {activeTab === 'Locations' && (
                      <ul className="list-disc pl-5 space-y-2 text-sm text-[#36516e]">
                        {locations.map((l, i) => <li key={i}>{String(l.text)}</li>)}
                      </ul>
                    )}
                    
                    {activeTab === 'Key Facts' && (
                      <ul className="list-disc pl-5 space-y-2 text-sm text-[#36516e]">
                        {keyFacts.map((f, i) => <li key={i}>{String(f.text)}</li>)}
                      </ul>
                    )}
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      </div>
    </LawyerCaseLayout>
  )
}
