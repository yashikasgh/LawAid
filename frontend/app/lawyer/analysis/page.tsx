
'use client'

import { useCallback, useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'

type AnalysisResponse = {
  status: string
  analysis: Record<string, unknown> | null
  error?: string | null
}

export default function LawyerAnalysisPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async (id: string) => {
    setLoading(true)
    setError('')
    try {
      const response = await lawyerCaseAPI.getAnalysis(id)
      setResult(response.data)
      setDraft(
        response.data.analysis
          ? JSON.stringify(response.data.analysis, null, 2)
          : '',
      )
    } catch (e) {
      setError(apiError(e, 'Could not load case analysis.'))
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

  async function runAnalysis() {
    if (!caseId) return
    setWorking(true)
    setError('')
    setSuccess('')
    try {
      await lawyerCaseAPI.analyze(caseId)
      setSuccess(
        'Analysis completed from parsed documents. Review and save corrections below.',
      )
      await load(caseId)
    } catch (e) {
      setError(apiError(e, 'Analysis could not be completed.'))
    } finally {
      setWorking(false)
    }
  }

  async function save() {
    if (!caseId) return

    let payload: unknown
    try {
      payload = JSON.parse(draft)
    } catch {
      setError('Analysis edits must be valid JSON.')
      return
    }

    setWorking(true)
    setError('')
    setSuccess('')
    try {
      const response = await lawyerCaseAPI.saveAnalysis(caseId, payload)
      setResult({
        status: response.data.status,
        analysis: response.data.analysis,
      })
      setSuccess('Corrections saved.')
      setDraft(JSON.stringify(response.data.analysis, null, 2))
    } catch (e) {
      setError(apiError(e, 'Could not save analysis corrections.'))
    } finally {
      setWorking(false)
    }
  }

  const analysis = result?.analysis
  const list = (key: string) =>
    Array.isArray(analysis?.[key])
      ? (analysis?.[key] as Array<Record<string, unknown>>)
      : []

  return (
    <>
      <Navbar />

      <main className="relative min-h-screen overflow-hidden">
        {/* Match the Case Documents background */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-feature-bg.png"
            alt=""
            className="h-full w-full object-cover object-center"
          />
        </div>

        <div className="fixed inset-0 -z-10 bg-[#f8f6f1]/10" />

        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {/* Page heading */}
          <header className="mb-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white">
              Lawyer Portal
            </p>

            <h1 className="mt-3 font-serif text-4xl font-semibold tracking-tight text-[#cc8427] md:text-5xl">
              AI Case Analysis
            </h1>

            <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#dca45a] md:text-base">
              Review extracted case information, examine potential legal
              sections, and refine the saved analysis.
            </p>
          </header>

          <ApiMessage error={error} success={success} />

          {/* Existing actions, with matching button styling */}
          <div className="mb-6 flex flex-wrap gap-3">
            <button
              onClick={runAnalysis}
              disabled={!caseId || working}
              className="inline-flex items-center justify-center rounded-xl bg-[#0f305b] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#173f70] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {working ? 'Working…' : 'Run analysis'}
            </button>

            <button
              onClick={() => caseId && load(caseId)}
              disabled={loading || working}
              className="inline-flex items-center justify-center rounded-xl border border-[#d2a14b]/60 bg-white/85 px-5 py-3 text-sm font-semibold text-[#0f305b] transition hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Refresh
            </button>
          </div>

          {loading ? (
            <section className="rounded-2xl border border-white/80 bg-white/85 p-8 text-center shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl">
              <p className="text-sm text-[#64748b]">
                Loading analysis…
              </p>
            </section>
          ) : !analysis ? (
            <section className="rounded-2xl border border-white/80 bg-white/85 p-8 text-center shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-12">
              <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                No analysis saved yet.
              </h2>
              <p className="mt-3 text-sm leading-6 text-[#64748b]">
                Upload and parse documents first, then run analysis.
              </p>
            </section>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Extracted case information */}
              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-8">
                <div className="mb-6 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <span className="text-xl" aria-hidden="true">
                      ⚖
                    </span>
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Extracted Case Information
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Review the information identified from the case documents.
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <Field
                    label="Offence type"
                    value={String(analysis.offence_type || 'Not mentioned')}
                  />

                  <List
                    label="Parties"
                    items={list('parties')}
                    primary="name"
                  />

                  <List
                    label="Locations"
                    items={list('locations')}
                    primary="text"
                  />

                  <List
                    label="Potential BNS sections"
                    items={list('bns_sections')}
                    primary="section_number"
                  />

                  <List
                    label="Evidence"
                    items={list('evidence')}
                    primary="name"
                  />

                  <List
                    label="Key facts"
                    items={list('key_facts')}
                    primary="text"
                  />
                </div>

                <p className="mt-6 border-t border-[#e6e0d4] pt-4 text-sm text-[#64748b]">
                  Status:{' '}
                  <span className="font-semibold text-[#0f305b]">
                    {result?.status}
                  </span>
                  . Source links and review flags are retained in the payload.
                </p>
              </section>

              {/* Existing analysis editor */}
              <section className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-[0_15px_40px_rgba(18,51,91,0.10)] backdrop-blur-xl sm:p-8">
                <div className="mb-6 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#d2a14b]/40 bg-[#f8f6f1] text-[#0f305b]">
                    <span className="text-xl" aria-hidden="true">
                      ✎
                    </span>
                  </div>

                  <div>
                    <h2 className="font-serif text-2xl font-semibold text-[#0f305b]">
                      Edit Analysis
                    </h2>
                    <p className="mt-1 text-sm text-[#64748b]">
                      Review and correct the saved analysis payload.
                    </p>
                  </div>
                </div>

                <p className="mb-4 text-sm leading-6 text-[#64748b]">
                  This editor saves the exact backend payload. Keep source
                  references and uncertainty fields when correcting values.
                </p>

                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  spellCheck={false}
                  className="min-h-[550px] w-full rounded-xl border border-[#d6c9aa] bg-[#faf8f2]/85 p-4 font-mono text-xs leading-5 text-[#183b62] outline-none transition focus:border-[#c28b19] focus:ring-2 focus:ring-[#c28b19]/20"
                />

                <button
                  onClick={save}
                  disabled={working}
                  className="mt-4 inline-flex items-center justify-center rounded-xl bg-[#c28b19] px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#a97512] focus:outline-none focus:ring-2 focus:ring-[#c28b19] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Save corrections
                </button>
              </section>
            </div>
          )}
        </div>
      </main>
    </>
  )
}

function Field({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-[#718096]">
        {label}
      </p>
      <p className="mt-1 text-sm leading-6 text-[#183b62]">{value}</p>
    </div>
  )
}

function List({
  label,
  items,
  primary,
}: {
  label: string
  items: Array<Record<string, unknown>>
  primary: string
}) {
  return (
    <div className="rounded-xl border border-[#e6e0d4] bg-white/90 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-[#718096]">
        {label}
      </p>

      {items.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-[#183b62]">
          {items.map((item, index) => (
            <li key={index}>
              {String(item[primary] || 'Not mentioned')}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#64748b]">Not mentioned</p>
      )}
    </div>
  )
}
