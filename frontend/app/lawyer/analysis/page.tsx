'use client'

import { useCallback, useEffect, useState } from 'react'
import LawyerTestHeader from '@/components/LawyerTestHeader'
import { ApiMessage, apiError } from '@/components/LawyerTestState'
import { lawyerCaseAPI, lawyerDocumentsAPI } from '@/lib/api'

type AnalysisResponse = { status: string; analysis: Record<string, unknown> | null; error?: string | null }

export default function LawyerAnalysisPage() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async (id: string) => {
    setLoading(true); setError('')
    try { const response = await lawyerCaseAPI.getAnalysis(id); setResult(response.data); setDraft(response.data.analysis ? JSON.stringify(response.data.analysis, null, 2) : '') }
    catch (e) { setError(apiError(e, 'Could not load case analysis.')) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { lawyerDocumentsAPI.workspace().then((r) => { setCaseId(r.data.id); return load(r.data.id) }).catch((e) => { setError(apiError(e, 'Could not load your case workspace.')); setLoading(false) }) }, [load])

  async function runAnalysis() {
    if (!caseId) return
    setWorking(true); setError(''); setSuccess('')
    try { await lawyerCaseAPI.analyze(caseId); setSuccess('Analysis completed from parsed documents. Review and save corrections below.'); await load(caseId) }
    catch (e) { setError(apiError(e, 'Analysis could not be completed.')) }
    finally { setWorking(false) }
  }
  async function save() {
    if (!caseId) return
    let payload: unknown
    try { payload = JSON.parse(draft) } catch { setError('Analysis edits must be valid JSON.'); return }
    setWorking(true); setError(''); setSuccess('')
    try { const response = await lawyerCaseAPI.saveAnalysis(caseId, payload); setResult({ status: response.data.status, analysis: response.data.analysis }); setSuccess('Corrections saved.'); setDraft(JSON.stringify(response.data.analysis, null, 2)) }
    catch (e) { setError(apiError(e, 'Could not save analysis corrections.')) }
    finally { setWorking(false) }
  }
  const analysis = result?.analysis
  const list = (key: string) => Array.isArray(analysis?.[key]) ? analysis?.[key] as Array<Record<string, unknown>> : []
  return <main className="min-h-screen bg-[#f7f4ec] px-4 py-7 text-slate-800"><div className="mx-auto max-w-6xl"><LawyerTestHeader title="AI Case Analysis" caseId={caseId} /><ApiMessage error={error} success={success} />
    <div className="mb-5 flex flex-wrap gap-3"><button onClick={runAnalysis} disabled={!caseId || working} className="rounded-lg bg-[#0f305b] px-4 py-2 font-semibold text-white disabled:opacity-50">{working ? 'Working…' : 'Run analysis'}</button><button onClick={() => caseId && load(caseId)} disabled={loading || working} className="rounded-lg border border-[#bda469] bg-white px-4 py-2 font-semibold text-[#0f305b]">Refresh</button></div>
    {loading ? <p>Loading analysis…</p> : !analysis ? <div className="rounded-xl border border-dashed border-[#cdbd97] bg-white p-8 text-center"><p className="font-semibold text-[#0f305b]">No analysis saved yet.</p><p className="mt-2 text-sm text-slate-600">Upload and parse documents first, then run analysis.</p></div> : <div className="grid gap-5 lg:grid-cols-2">
      <section className="rounded-xl border border-[#ded5c1] bg-white p-5"><h2 className="font-serif text-xl font-bold text-[#0f305b]">Extracted case information</h2><p className="mt-1 text-sm text-slate-600">Status: {result?.status}. Source links and review flags are retained in the payload.</p>
        <div className="mt-4 space-y-4"><Field label="Offence type" value={String(analysis.offence_type || 'Not mentioned')} /><List label="Parties" items={list('parties')} primary="name" /><List label="Locations" items={list('locations')} primary="text" /><List label="Potential BNS sections" items={list('bns_sections')} primary="section_number" /><List label="Evidence" items={list('evidence')} primary="name" /><List label="Key facts" items={list('key_facts')} primary="text" /></div></section>
      <section className="rounded-xl border border-[#ded5c1] bg-white p-5"><h2 className="font-serif text-xl font-bold text-[#0f305b]">Edit persisted analysis payload</h2><p className="mt-1 text-sm text-slate-600">This test editor saves the exact backend payload. Keep source references and uncertainty fields when correcting values.</p><textarea value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} className="mt-4 min-h-[550px] w-full rounded-lg border border-slate-300 bg-slate-50 p-3 font-mono text-xs leading-5" /><button onClick={save} disabled={working} className="mt-3 rounded-lg bg-[#c28b19] px-4 py-2 font-semibold text-white disabled:opacity-50">Save corrections</button></section>
    </div>}</div></main>
}
function Field({ label, value }: { label: string; value: string }) { return <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1">{value}</p></div> }
function List({ label, items, primary }: { label: string; items: Array<Record<string, unknown>>; primary: string }) { return <div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>{items.length ? <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{items.map((item, index) => <li key={index}>{String(item[primary] || 'Not mentioned')}</li>)}</ul> : <p className="mt-1 text-sm text-slate-500">Not mentioned</p>}</div> }
