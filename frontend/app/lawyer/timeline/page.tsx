
'use client'

import { useCallback, useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'
import {
  CalendarDays,
  Clock3,
  FileText,
  ListFilter,
  RotateCcw,
  Save,
} from 'lucide-react'

type Event = {
  id: string
  date: string
  time?: string | null
  title: string
  description: string
  event_type: string
  source_document_name?: string | null
  source_document_id?: string | null
  is_edited?: boolean
}

const types = [
  'Incident',
  'Police Complaint',
  'FIR',
  'Medical',
  'Witness Statement',
  'Investigation',
  'Charge Sheet',
  'Court Proceedings',
]

export default function TimelinePage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [selected, setSelected] = useState<Event | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [eventType, setEventType] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(
    async (id: string, filters = true) => {
      setLoading(true)
      setError('')

      try {
        const r = await lawyerCaseAPI.getTimeline(
          id,
          filters
            ? {
                event_type: eventType || undefined,
                date_from: dateFrom || undefined,
                date_to: dateTo || undefined,
              }
            : undefined,
        )

        setEvents(r.data)
        setSelected(
          (current) => r.data.find((e: Event) => e.id === current?.id) || null,
        )
      } catch (e) {
        setError(apiError(e, 'Could not load timeline.'))
      } finally {
        setLoading(false)
      }
    },
    [dateFrom, dateTo, eventType],
  )

  useEffect(() => {
    lawyerDocumentsAPI
      .workspace()
      .then((r) => {
        setCaseId(r.data.id)
        return load(r.data.id, false)
      })
      .catch((e) => {
        setError(apiError(e, 'Could not load your case workspace.'))
        setLoading(false)
      })
  }, [load])

  async function save() {
    if (!caseId || !selected) return

    setError('')
    setSuccess('')

    try {
      const r = await lawyerCaseAPI.updateTimeline(caseId, selected.id, {
        date: selected.date,
        time: selected.time || null,
        title: selected.title,
        description: selected.description,
        event_type: selected.event_type,
      })

      setSelected(r.data)
      setSuccess('Timeline event saved.')
      await load(caseId)
    } catch (e) {
      setError(apiError(e, 'Could not save timeline event.'))
    }
  }

  return (
    <>
      <Navbar />

      <main className="relative min-h-screen overflow-hidden">
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-feature-bg.png"
            alt=""
            className="h-full w-full object-cover object-center"
          />
        </div>

        <div className="fixed inset-0 -z-10 bg-[#f8f6f1]/10" />

        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <header className="mb-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white">
              Lawyer Portal
            </p>

            <h1 className="mt-3 font-serif text-4xl font-semibold tracking-tight text-[#cc8427] md:text-5xl">
              Case Timeline
            </h1>

            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#dca45a] md:text-base">
              Review important case events in chronological order, filter the
              timeline, and update event details.
            </p>
          </header>

          <ApiMessage error={error} success={success} />

          <section className="mb-6 rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                <ListFilter size={22} />
              </div>

              <div>
                <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                  Filter Case Events
                </h2>
                <p className="mt-1 text-sm text-[#64748b]">
                  Narrow the timeline by date or event type.
                </p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.2fr_auto_auto] lg:items-end">
              <label className="block text-sm font-medium text-[#36516e]">
                From
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                />
              </label>

              <label className="block text-sm font-medium text-[#36516e]">
                To
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                />
              </label>

              <label className="block text-sm font-medium text-[#36516e]">
                Event type
                <select
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                  className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                >
                  <option value="">All types</option>
                  {types.map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                onClick={() => caseId && load(caseId)}
                disabled={!caseId || loading}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0f305b] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#173f70] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ListFilter size={16} />
                Apply filters
              </button>

              <button
                type="button"
                onClick={() => {
                  setDateFrom('')
                  setDateTo('')
                  setEventType('')
                  if (caseId) load(caseId, false)
                }}
                disabled={!caseId || loading}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#d6c9aa] bg-white/90 px-4 py-2.5 text-sm font-semibold text-[#0f305b] transition hover:bg-[#f8f6f1] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RotateCcw size={16} />
                Clear
              </button>
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-[1fr_0.85fr]">
            <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-6">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                  <CalendarDays size={22} />
                </div>

                <div>
                  <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                    Case Events
                  </h2>
                  <p className="mt-1 text-sm text-[#64748b]">
                    Select an event to view or edit its details.
                  </p>
                </div>
              </div>

              {loading ? (
                <div className="rounded-xl border border-dashed border-[#d9d3c6] bg-white/70 px-4 py-10 text-center">
                  <p className="text-sm text-[#64748b]">
                    Loading timeline…
                  </p>
                </div>
              ) : events.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#d9d3c6] bg-white/70 px-4 py-10 text-center">
                  <CalendarDays
                    className="mx-auto text-[#b0a58e]"
                    size={30}
                  />
                  <p className="mt-3 font-semibold text-[#0f305b]">
                    No timeline events found
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#64748b]">
                    No events match these filters. Run analysis after documents
                    are parsed.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {events.map((e) => (
                    <button
                      type="button"
                      key={e.id}
                      onClick={() => setSelected(e)}
                      aria-pressed={selected?.id === e.id}
                      className={`block w-full rounded-xl border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-[#c28b19]/50 ${
                        selected?.id === e.id
                          ? 'border-[#c28b19] bg-[#fbf4e6] shadow-sm'
                          : 'border-[#e6e0d4] bg-white/90 hover:border-[#d2a14b] hover:bg-[#faf8f2]'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#f4f0e6] text-[#0f305b]">
                          <CalendarDays size={18} />
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="font-semibold leading-6 text-[#0f305b]">
                            {e.date}
                            {e.time ? ` · ${e.time}` : ''} — {e.title}
                          </p>

                          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-[#98701f]">
                            {e.event_type}
                          </p>

                          <p className="mt-1 flex items-center gap-1.5 text-xs text-[#718096]">
                            <FileText size={13} />
                            <span className="break-words">
                              {e.source_document_name || 'No source document'}
                            </span>
                          </p>

                          <p className="mt-3 line-clamp-2 text-sm leading-6 text-[#475569]">
                            {e.description}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="h-fit rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-6">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                  <Clock3 size={22} />
                </div>

                <div>
                  <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                    Event Details
                  </h2>
                  <p className="mt-1 text-sm text-[#64748b]">
                    Review and update the selected event.
                  </p>
                </div>
              </div>

              {!selected ? (
                <div className="rounded-xl border border-dashed border-[#d9d3c6] bg-white/70 px-4 py-10 text-center">
                  <FileText
                    className="mx-auto text-[#b0a58e]"
                    size={30}
                  />
                  <p className="mt-3 font-semibold text-[#0f305b]">
                    No event selected
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#64748b]">
                    Select an event from the timeline to inspect or edit it.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <label className="block text-sm font-medium text-[#36516e]">
                    Date
                    <input
                      type="date"
                      value={selected.date}
                      onChange={(e) =>
                        setSelected({ ...selected, date: e.target.value })
                      }
                      className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                    />
                  </label>

                  <label className="block text-sm font-medium text-[#36516e]">
                    Time
                    <input
                      value={selected.time || ''}
                      onChange={(e) =>
                        setSelected({ ...selected, time: e.target.value })
                      }
                      className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                    />
                  </label>

                  <label className="block text-sm font-medium text-[#36516e]">
                    Title
                    <input
                      value={selected.title}
                      onChange={(e) =>
                        setSelected({ ...selected, title: e.target.value })
                      }
                      className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                    />
                  </label>

                  <label className="block text-sm font-medium text-[#36516e]">
                    Type
                    <select
                      value={selected.event_type}
                      onChange={(e) =>
                        setSelected({
                          ...selected,
                          event_type: e.target.value,
                        })
                      }
                      className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                    >
                      {types.map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </label>

                  <label className="block text-sm font-medium text-[#36516e]">
                    Description
                    <textarea
                      value={selected.description}
                      onChange={(e) =>
                        setSelected({
                          ...selected,
                          description: e.target.value,
                        })
                      }
                      className="mt-1.5 block min-h-32 w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm leading-6 text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                    />
                  </label>

                  <div className="rounded-xl border border-[#e6e0d4] bg-[#faf8f2]/85 p-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-[#98701f]">
                      Source document
                    </p>
                    <p className="mt-1 break-words text-sm text-[#64748b]">
                      {selected.source_document_name || 'Not available'} (read-only)
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={save}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#c28b19] px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#a97512] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2"
                  >
                    <Save size={17} />
                    Save Event
                  </button>
                </div>
              )}
            </section>
          </div>
        </div>
      </main>
    </>
  )
}
