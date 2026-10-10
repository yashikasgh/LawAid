'use client'

import { useCallback, useEffect, useState, useMemo } from 'react'
import LawyerCaseLayout from '@/components/LawyerCaseLayout'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'
import { Calendar, CalendarDays, FileText, Filter, Edit3, ChevronDown } from 'lucide-react'

type Event = { id: string; date: string; time?: string | null; title: string; description: string; event_type: string; source_document_name?: string | null; source_document_id?: string | null; is_edited?: boolean }
const types = ['Incident', 'Police Complaint', 'FIR', 'Medical', 'Witness Statement', 'Investigation', 'Charge Sheet', 'Court Proceedings']

export default function TimelinePage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [selected, setSelected] = useState<Event | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [sortOrder, setSortOrder] = useState('Oldest First')

  const load = useCallback(async (id: string) => {
    setLoading(true); setError(''); 
    try { 
      const r = await lawyerCaseAPI.getTimeline(id);
      let sortedEvents = [...r.data]
      if (sortOrder === 'Oldest First') {
        sortedEvents.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      } else {
        sortedEvents.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      }
      setEvents(sortedEvents); 
      setSelected((current) => sortedEvents.find((e: Event) => e.id === current?.id) || null) 
    } 
    catch (e) { setError(apiError(e, 'Could not load timeline.')) } 
    finally { setLoading(false) } 
  }, [sortOrder])

  useEffect(() => { 
    lawyerDocumentsAPI.workspace().then((r) => { 
      setCaseId(r.data.id); 
      return load(r.data.id)
    }).catch((e) => { 
      setError(apiError(e, 'Could not load your case workspace.')); 
      setLoading(false) 
    }) 
  }, [load])

  async function save() { 
    if (!caseId || !selected) return; 
    setError(''); setSuccess(''); 
    try { 
      const r = await lawyerCaseAPI.updateTimeline(caseId, selected.id, { date: selected.date, time: selected.time || null, title: selected.title, description: selected.description, event_type: selected.event_type }); 
      setSelected(r.data); 
      setSuccess('Timeline event saved.'); 
      await load(caseId) 
    } 
    catch (e) { setError(apiError(e, 'Could not save timeline event.')) } 
  }

  // Derive stats
  const uniqueSources = useMemo(() => Array.from(new Set(events.map(e => e.source_document_name).filter(Boolean))), [events])
  const dateRange = useMemo(() => {
    if (events.length === 0) return 'Not available'
    const dates = events.map(e => new Date(e.date).getTime()).filter(t => !isNaN(t))
    if (dates.length === 0) return 'Not available'
    const min = new Date(Math.min(...dates)).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    const max = new Date(Math.max(...dates)).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    return min === max ? min : `${min} - ${max}`
  }, [events])

  const typeColorMap: Record<string, string> = {
    'Incident': 'bg-[#fff4e6] text-[#c26a19] border-[#fce3c5]',
    'Police Complaint': 'bg-[#eef5fe] text-[#1c64f2] border-[#d4e4fc]',
    'FIR': 'bg-[#f8ebfe] text-[#9030d2] border-[#ecd3fb]',
    'Medical': 'bg-[#e5fcf3] text-[#0e9f6e] border-[#c1f5e0]',
    'Witness Statement': 'bg-[#fdf3fd] text-[#c72eb8] border-[#fbe0fa]',
    'Investigation': 'bg-[#eef5fe] text-[#1c64f2] border-[#d4e4fc]',
    'Charge Sheet': 'bg-[#eef5fe] text-[#1c64f2] border-[#d4e4fc]',
    'Court Proceedings': 'bg-[#fff1f2] text-[#e02424] border-[#ffe4e6]'
  }

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
            Case Timeline
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-[#36516e]">
            Chronological timeline of key events extracted from your documents.
          </p>
        </header>

        <ApiMessage error={error} success={success} />

        {/* Stats Bar */}
        <div className="mb-6 rounded-2xl border border-white/80 bg-white/90 p-3 shadow-[0_15px_40px_rgba(18,51,91,0.06)] backdrop-blur-xl flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6 px-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f8f6f1] text-[#c28b19]">
                <CalendarDays size={18} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">Total Events</p>
                <p className="text-lg font-bold text-[#0f305b] leading-tight">{events.length}</p>
              </div>
            </div>
            <div className="h-8 w-[1px] bg-[#e6e0d4]"></div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f8f6f1] text-[#c28b19]">
                <Calendar size={18} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">Date Range</p>
                <p className="text-sm font-bold text-[#0f305b] leading-tight mt-0.5">{dateRange}</p>
              </div>
            </div>
            <div className="h-8 w-[1px] bg-[#e6e0d4]"></div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f8f6f1] text-[#c28b19]">
                <FileText size={18} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748b]">Sources</p>
                <p className="text-sm font-bold text-[#0f305b] leading-tight mt-0.5">{uniqueSources.length} Documents</p>
              </div>
            </div>
          </div>
          
          <button 
            onClick={() => setIsEditing(!isEditing)}
            className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition mr-2 ${
              isEditing ? 'border-[#c28b19] bg-[#fcf9f2] text-[#c28b19]' : 'border-[#e2d8c3] bg-white text-[#c28b19] hover:bg-slate-50'
            }`}
          >
            <Edit3 size={16} />
            {isEditing ? 'Editing Timeline' : 'Edit Timeline'}
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_320px] items-start">
          
          {/* Main Timeline View */}
          <section className="rounded-2xl border border-white/80 bg-white/90 shadow-[0_15px_40px_rgba(18,51,91,0.06)] backdrop-blur-xl flex flex-col min-h-[600px]">
            <div className="p-5 border-b border-[#eee8dd] flex items-center justify-between">
              <div className="flex items-center gap-2 text-[#0f305b]">
                <CalendarDays size={20} />
                <h2 className="font-serif text-xl font-bold">Timeline of Events</h2>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[#64748b]">Sort:</span>
                <select 
                  value={sortOrder} 
                  onChange={(e) => {
                    setSortOrder(e.target.value)
                    load(caseId!)
                  }}
                  className="font-bold text-[#0f305b] bg-transparent focus:outline-none appearance-none pr-4 cursor-pointer"
                >
                  <option>Oldest First</option>
                  <option>Newest First</option>
                </select>
              </div>
            </div>
            
            <div className="p-6 relative flex-1">
              {loading ? (
                <p className="text-center py-10 text-[#64748b]">Loading timeline…</p>
              ) : events.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#d6c9aa] bg-[#fcfaf7] p-10 text-center">
                  <p className="font-bold text-[#0f305b]">No timeline events yet.</p>
                  <p className="text-sm text-[#64748b] mt-1">Run analysis after documents are parsed.</p>
                </div>
              ) : (
                <div className="relative before:absolute before:left-[19px] before:top-4 before:bottom-4 before:w-[2px] before:bg-[#e6e0d4] space-y-6">
                  {events.map((e, index) => (
                    <div key={e.id} className="relative flex items-stretch cursor-pointer group" onClick={() => setSelected(e)}>
                      <div className="absolute left-[13px] top-4 h-3.5 w-3.5 rounded-full border-[3px] border-[#c28b19] bg-white z-10 transition-transform group-hover:scale-125"></div>
                      
                      <div className={`ml-[46px] flex-1 rounded-xl border p-4 transition-all ${
                        selected?.id === e.id 
                          ? 'border-[#c28b19] bg-[#fdfaf5] shadow-sm' 
                          : 'border-[#eee8dd] bg-white hover:border-[#d6c9aa] hover:shadow-sm'
                      }`}>
                        <div className="flex gap-4">
                          <div className="w-[100px] shrink-0 pt-1">
                            <p className="text-[13px] font-bold text-[#0f305b]">
                              {new Date(e.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                            </p>
                            <p className="text-[11px] font-medium text-[#64748b] mt-0.5">{e.time || 'Time unknown'}</p>
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <h3 className="font-bold text-[#0f305b] text-[15px]">{e.title}</h3>
                            <p className="text-sm text-[#36516e] mt-1.5 leading-relaxed">{e.description}</p>
                            
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-bold ${typeColorMap[e.event_type] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                                {e.event_type}
                              </span>
                            </div>
                          </div>
                          
                          <div className="shrink-0">
                            <div className="inline-flex items-center gap-1.5 rounded-lg border border-[#e2effd] bg-[#f0f6ff] px-2.5 py-1.5 text-xs font-semibold text-[#1c64f2]">
                              <FileText size={14} />
                              <span className="max-w-[120px] truncate">{e.source_document_name || 'No Source'}</span>
                              <ChevronDown size={14} className="ml-1 opacity-50" />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Right Sidebar - Filters & Details */}
          <aside className="space-y-6">
            

            {/* Event Details / Editor */}
            <section className="rounded-2xl border border-white/80 bg-white/90 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.06)] backdrop-blur-xl">
              <div className="flex items-center gap-2 text-[#c28b19] mb-4">
                <FileText size={18} />
                <h3 className="font-serif text-lg font-bold text-[#0f305b]">Event Details</h3>
              </div>
              
              {!selected ? (
                <div className="py-6 text-center text-sm text-[#64748b]">
                  <p>Select an event from the timeline to view or edit its details.</p>
                </div>
              ) : isEditing ? (
                <div className="space-y-3 mt-4 text-sm">
                  <label className="block">
                    <span className="text-xs font-bold text-[#0f305b]">Date</span>
                    <input type="date" value={selected.date} onChange={e => setSelected({ ...selected, date: e.target.value })} className="mt-1 w-full rounded-xl border border-[#e2d8c3] p-2" />
                  </label>
                  <label className="block">
                    <span className="text-xs font-bold text-[#0f305b]">Time</span>
                    <input type="time" value={selected.time || ''} onChange={e => setSelected({ ...selected, time: e.target.value })} className="mt-1 w-full rounded-xl border border-[#e2d8c3] p-2" />
                  </label>
                  <label className="block">
                    <span className="text-xs font-bold text-[#0f305b]">Title</span>
                    <input value={selected.title} onChange={e => setSelected({ ...selected, title: e.target.value })} className="mt-1 w-full rounded-xl border border-[#e2d8c3] p-2" />
                  </label>
                  <label className="block">
                    <span className="text-xs font-bold text-[#0f305b]">Type</span>
                    <select value={selected.event_type} onChange={e => setSelected({ ...selected, event_type: e.target.value })} className="mt-1 w-full rounded-xl border border-[#e2d8c3] p-2">
                      {types.map(t => <option key={t}>{t}</option>)}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-bold text-[#0f305b]">Description</span>
                    <textarea value={selected.description} onChange={e => setSelected({ ...selected, description: e.target.value })} className="mt-1 min-h-[100px] w-full rounded-xl border border-[#e2d8c3] p-2" />
                  </label>
                  <button onClick={save} className="w-full mt-2 rounded-xl bg-[#c28b19] px-4 py-2.5 font-bold text-white hover:bg-[#a87815]">Save event</button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-start border-b border-[#eee8dd] pb-3">
                    <span className="text-xs font-bold text-[#64748b]">Title</span>
                    <span className="text-sm font-bold text-[#0f305b]">{selected.title}</span>
                  </div>
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-start border-b border-[#eee8dd] pb-3">
                    <span className="text-xs font-bold text-[#64748b]">Date & Time</span>
                    <span className="text-sm text-[#36516e]">
                      {new Date(selected.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                      {selected.time ? `, ${selected.time}` : ''}
                    </span>
                  </div>
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-start border-b border-[#eee8dd] pb-3">
                    <span className="text-xs font-bold text-[#64748b]">Description</span>
                    <span className="text-sm text-[#36516e] leading-relaxed">{selected.description}</span>
                  </div>
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-center border-b border-[#eee8dd] pb-3">
                    <span className="text-xs font-bold text-[#64748b]">Event Type</span>
                    <span className={`inline-flex w-fit items-center rounded-md border px-2 py-0.5 text-[10px] font-bold ${typeColorMap[selected.event_type] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                      {selected.event_type}
                    </span>
                  </div>
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-center border-b border-[#eee8dd] pb-3">
                    <span className="text-xs font-bold text-[#64748b]">Related BNS</span>
                    <span className="text-xs text-[#36516e]">None specified</span>
                  </div>
                  <div className="grid grid-cols-[100px_1fr] gap-2 items-start">
                    <span className="text-xs font-bold text-[#64748b]">Source</span>
                    <div>
                      <div className="inline-flex items-center gap-1.5 rounded-lg border border-[#e2effd] bg-[#f0f6ff] px-3 py-1.5 text-xs font-bold text-[#1c64f2]">
                        <FileText size={14} />
                        {selected.source_document_name || 'No Source'}
                      </div>
                      {selected.source_document_name && (
                        <button className="mt-2 text-[11px] font-bold text-[#c28b19] flex items-center gap-1 hover:underline">
                          View Document <Filter size={10} className="rotate-[-90deg]" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          </aside>
        </div>
      </div>
    </LawyerCaseLayout>
  )
}
