
'use client'

import { useCallback, useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'
import {
  BookOpen,
  CheckSquare,
  Clock3,
  Download,
  FileText,
  ListChecks,
  RefreshCw,
  Save,
  Scale,
} from 'lucide-react'

type Summary = {
  case_id: string
  case_number: string
  current_stage?: string | null
  executive_summary: string
  key_facts: Array<{ text?: string }>
  bns_sections: Array<{
    section_number?: string
    title?: string | null
  }>
  timeline_preview: Array<{
    id: string
    date: string
    title: string
    description: string
  }>
}

export default function SummaryPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [text, setText] = useState('')
  const [stage, setStage] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [options, setOptions] = useState({
    include_executive_summary: true,
    include_timeline: true,
    include_key_facts: true,
    include_bns_sections: true,
    include_original_documents: true,
  })

  const load = useCallback(async (id: string) => {
    setLoading(true)
    setError('')

    try {
      const r = await lawyerCaseAPI.getSummary(id)
      setSummary(r.data)
      setText(r.data.executive_summary || '')
      setStage(r.data.current_stage || '')
    } catch (e) {
      setError(apiError(e, 'Could not load case summary.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    lawyerDocumentsAPI
      .workspace()
      .then((r) => {
        setCaseId(r.data.id)
        return load(r.data.id)
      })
      .catch((e) => {
        setError(apiError(e, 'Could not load your case workspace.'))
        setLoading(false)
      })
  }, [load])

  async function save() {
    if (!caseId) return

    setWorking(true)
    setError('')
    setSuccess('')

    try {
      const r = await lawyerCaseAPI.saveSummary(caseId, {
        executive_summary: text,
        current_stage: stage || null,
      })

      setSummary(r.data)
      setSuccess('Summary saved.')
    } catch (e) {
      setError(apiError(e, 'Could not save summary.'))
    } finally {
      setWorking(false)
    }
  }

  async function exportPackage() {
    if (!caseId) return

    setWorking(true)
    setError('')
    setSuccess('')

    try {
      const r = await lawyerCaseAPI.export(caseId, options)
      const url = URL.createObjectURL(
        new Blob([r.data], { type: 'application/pdf' }),
      )
      const a = document.createElement('a')
      a.href = url
      a.download = `case-package-${caseId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      setSuccess('PDF package generated and downloaded.')
    } catch (e) {
      setError(apiError(e, 'Could not generate the PDF package.'))
    } finally {
      setWorking(false)
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
              Summary &amp; Export
            </h1>

            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#dca45a] md:text-base">
              Review the case summary, key facts, potential BNS sections, and
              timeline before generating a case package.
            </p>
          </header>

          <ApiMessage error={error} success={success} />

          {loading ? (
            <div className="rounded-2xl border border-white/80 bg-white/85 p-10 text-center shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl">
              <p className="text-sm text-[#64748b]">Loading summary…</p>
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-7">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <BookOpen size={22} />
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Case Summary
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Review and save the case overview.
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4">
                  <p className="text-xs font-bold uppercase tracking-wide text-[#98701f]">
                    Case number
                  </p>
                  <p className="mt-1 break-words font-semibold text-[#183b62]">
                    {summary?.case_number || 'Not available'}
                  </p>
                </div>

                <label className="mt-5 block text-sm font-medium text-[#36516e]">
                  Current stage
                  <input
                    value={stage}
                    onChange={(e) => setStage(e.target.value)}
                    placeholder="e.g. Review"
                    className="mt-1.5 block w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-2.5 text-sm text-[#183b62] outline-none transition placeholder:text-[#94a3b8] focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                  />
                </label>

                <label className="mt-5 block text-sm font-medium text-[#36516e]">
                  Executive summary
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Write a lawyer-reviewed summary…"
                    className="mt-1.5 block min-h-48 w-full rounded-xl border border-[#d6c9aa] bg-white/90 px-3 py-3 text-sm leading-6 text-[#183b62] outline-none transition placeholder:text-[#94a3b8] focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                  />
                </label>

                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={save}
                    disabled={working}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#c28b19] px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#a97512] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Save size={17} />
                    Save Summary
                  </button>

                  <button
                    type="button"
                    onClick={() => caseId && load(caseId)}
                    disabled={loading || working || !caseId}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#d6c9aa] bg-white/90 px-5 py-3 text-sm font-semibold text-[#0f305b] transition hover:bg-[#f8f6f1] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <RefreshCw size={16} />
                    Refresh
                  </button>
                </div>
              </section>

              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-7">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <Download size={22} />
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Export Case Package
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Choose the sections to include in your PDF.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {Object.entries(options).map(([key, checked]) => (
                    <label
                      key={key}
                      className="flex cursor-pointer items-start gap-3 rounded-xl border border-[#e6e0d4] bg-white/90 p-3.5 transition hover:border-[#d2a14b] hover:bg-[#faf8f2]"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) =>
                          setOptions({
                            ...options,
                            [key]: e.target.checked,
                          })
                        }
                        className="mt-0.5 h-4 w-4 shrink-0 accent-[#c28b19]"
                      />

                      <span className="text-sm font-medium capitalize text-[#36516e]">
                        {key
                          .replace('include_', '')
                          .replaceAll('_', ' ')}
                      </span>
                    </label>
                  ))}
                </div>

                <div className="mt-5 rounded-xl border border-[#e6e0d4] bg-[#faf8f2]/85 p-4">
                  <p className="text-sm leading-6 text-[#64748b]">
                    The backend returns the PDF package using the selected
                    options.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={exportPackage}
                  disabled={working || !caseId}
                  className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0f305b] px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#173f70] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Download size={17} />
                  {working ? 'Generating…' : 'Generate & Download PDF'}
                </button>
              </section>

              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-7">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <Clock3 size={22} />
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Timeline Preview
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Important events recorded for this case.
                    </p>
                  </div>
                </div>

                {summary?.timeline_preview.length ? (
                  <ul className="space-y-4">
                    {summary.timeline_preview.map((e) => (
                      <li
                        key={e.id}
                        className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4"
                      >
                        <p className="font-semibold leading-6 text-[#0f305b]">
                          {e.date} — {e.title}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[#475569]">
                          {e.description}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-xl border border-dashed border-[#d9d3c6] bg-white/70 px-4 py-8 text-center">
                    <Clock3
                      className="mx-auto text-[#b0a58e]"
                      size={28}
                    />
                    <p className="mt-3 text-sm text-[#64748b]">
                      No timeline events are saved.
                    </p>
                  </div>
                )}
              </section>

              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-7">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <Scale size={22} />
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Facts &amp; BNS Sections
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Review extracted facts and potential legal sections.
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-[#98701f]">
                    <ListChecks size={15} />
                    Key Facts
                  </h3>

                  {summary?.key_facts.length ? (
                    <ul className="mt-3 space-y-2">
                      {summary.key_facts.map((f, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 rounded-lg border border-[#e6e0d4] bg-white/90 p-3 text-sm leading-6 text-[#36516e]"
                        >
                          <CheckSquare
                            size={16}
                            className="mt-1 shrink-0 text-[#98701f]"
                          />
                          <span>{f.text || 'Not mentioned'}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-[#64748b]">
                      None extracted.
                    </p>
                  )}
                </div>

                <div className="mt-6 border-t border-[#e6e0d4] pt-5">
                  <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-[#98701f]">
                    <Scale size={15} />
                    Potential BNS Sections
                  </h3>

                  {summary?.bns_sections.length ? (
                    <ul className="mt-3 space-y-2">
                      {summary.bns_sections.map((s, i) => (
                        <li
                          key={i}
                          className="rounded-lg border border-[#e6e0d4] bg-white/90 p-3"
                        >
                          <p className="font-semibold text-[#0f305b]">
                            Section {s.section_number}
                          </p>
                          {s.title && (
                            <p className="mt-1 text-sm leading-6 text-[#64748b]">
                              {s.title}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-[#64748b]">
                      None extracted.
                    </p>
                  )}
                </div>
              </section>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
