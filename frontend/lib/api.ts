// lib/api.ts
import axios from 'axios'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// This connects to the backend server. Authentication is carried by the
// backend-issued HttpOnly session cookie, so every request must include
// credentials; no token is ever read from or written to browser storage.
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// Endpoints whose 401 responses are handled by the calling page itself
// (login form errors, session probes) and must never trigger a redirect.
const AUTH_PROBE_PATHS = ['/auth/login', '/auth/register', '/auth/me', '/auth/logout', '/auth/forgot-password', '/auth/reset-password']

function redirectToLoginOnExpiredSession(requestPath: string | undefined) {
  if (typeof window === 'undefined') return
  if (requestPath && AUTH_PROBE_PATHS.some((p) => requestPath.includes(p))) return
  const { pathname, search } = window.location
  if (pathname.startsWith('/login') || pathname.startsWith('/register')) return
  localStorage.removeItem('lawaid_user')
  localStorage.removeItem('lawaid_role')
  window.location.assign(`/login?next=${encodeURIComponent(pathname + search)}`)
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      redirectToLoginOnExpiredSession(error.config?.url)
    }
    return Promise.reject(error)
  }
)

// fetch() wrapper for pages that use the Fetch API directly. Uses the same
// configured backend URL and sends the session cookie.
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: 'include' })
  if (res.status === 401) redirectToLoginOnExpiredSession(path)
  return res
}

// UI shows 'Citizen' / 'Police' / 'Lawyer' (capitalized tabs), but backend
// stores role as lowercase. Always convert before sending to the API.
export const toApiRole = (uiRole: string) => uiRole.toLowerCase()

// ── Auth ─────────────────────────────────────────────────────
export const authAPI = {
  login: (email: string, password: string, role: string) =>
    api.post('/auth/login', { email, password, role: toApiRole(role) }),

  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password, role: 'citizen' }),

  me: () => api.get('/auth/me'),

  logout: () => api.post('/auth/logout'),

  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    api.post('/auth/reset-password', { token, new_password: newPassword }),
}

// ── FIR ──────────────────────────────────────────────────────
export const firAPI = {
  generate: (complaint: string) =>
    api.post('/fir/generate', { complaint }),

  understand: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/fir/understand', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  verify: (firId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/fir/verify?fir_id=${encodeURIComponent(firId)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  checkDuplicate: (complaintText: string) =>
    api.post('/fir/check-duplicate', { complaint_text: complaintText }),

  saveFIR: (payload: any) =>
    api.post('/fir/saved', payload),

  getSavedFIRs: () =>
    api.get('/fir/saved'),

  getSavedFIR: (savedId: number | string) =>
    api.get(`/fir/saved/${savedId}`),

  deleteSavedFIR: (savedId: number | string) =>
    api.delete(`/fir/saved/${savedId}`),
}

// ── BNS Search & Legal Analysis ─────────────────────────────
export const bnsAPI = {
  search: (query: string) =>
    api.get(`/fir/bns/search?query=${encodeURIComponent(query)}`),

  analyze: (incident: string) =>
    api.post('/fir/analyze', { incident }),
}

// ── Chat ─────────────────────────────────────────────────────
export const chatAPI = {
  sendMessage: (sessionId: string, message: string) =>
    api.post('/chat/message', { session_id: sessionId, message }),

  getHistory: (sessionId: string) =>
    api.get(`/chat/history/${sessionId}`),
}

// ── Lawyer case documents ───────────────────────────────────
export const lawyerDocumentsAPI = {
  workspace: () => api.post('/lawyer/cases/workspace'),
  list: (caseId: string) => api.get(`/lawyer/cases/${caseId}/documents`),
  metrics: (caseId: string) => api.get(`/lawyer/cases/${caseId}/documents/metrics`),
  upload: (caseId: string, files: File[], onProgress?: (percent: number) => void) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return api.post(`/lawyer/cases/${caseId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total && onProgress) onProgress(Math.round((event.loaded / event.total) * 100))
      },
    })
  },
  remove: (caseId: string, documentId: string) =>
    api.delete(`/lawyer/cases/${caseId}/documents/${documentId}`),
  retry: (caseId: string, documentId: string) =>
    api.post(`/lawyer/cases/${caseId}/documents/${documentId}/retry`),
  analyze: (caseId: string) => api.post(`/lawyer/cases/${caseId}/documents/analyze`),
}

// ── Lawyer case workflow ───────────────────────────────────
// Keep Lawyer-module request details here so the temporary testing screens can
// be replaced later without copying API knowledge into presentation components.
export const lawyerCaseAPI = {
  get: (caseId: string) => api.get(`/lawyer/cases/${caseId}`),
  analyze: (caseId: string) => api.post(`/lawyer/cases/${caseId}/analyze`),
  getAnalysis: (caseId: string) => api.get(`/lawyer/cases/${caseId}/analysis`),
  saveAnalysis: (caseId: string, payload: unknown) =>
    api.patch(`/lawyer/cases/${caseId}/analysis`, { payload }),
  getTimeline: (caseId: string, params?: { event_type?: string; source_document_id?: string; date_from?: string; date_to?: string; order?: 'oldest' | 'newest' }) =>
    api.get(`/lawyer/cases/${caseId}/timeline`, { params }),
  updateTimeline: (caseId: string, eventId: string, payload: unknown) =>
    api.patch(`/lawyer/cases/${caseId}/timeline/${eventId}`, payload),
  getSummary: (caseId: string) => api.get(`/lawyer/cases/${caseId}/summary`),
  saveSummary: (caseId: string, payload: { executive_summary: string; current_stage?: string | null }) =>
    api.patch(`/lawyer/cases/${caseId}/summary`, payload),
  export: (caseId: string, options: Record<string, boolean>) =>
    api.post(`/lawyer/cases/${caseId}/export`, options, { responseType: 'blob' }),
}

// ── Police ───────────────────────────────────────────────────
export const policeAPI = {
  transcribe: (audio: File) => {
    const form = new FormData()
    form.append('audio', audio)
    return api.post('/police/transcribe', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  extractStatement: (statement: string) =>
    api.post('/police/extract-statement', { statement }),
  generateFir: (incident: string) =>
    api.post('/police/generate-fir', { incident }),
  renderFirPdf: (fir_data: any) =>
    api.post('/police/render-fir-pdf', { fir_data }),
  validateFir: (payload: unknown) => api.post('/police/validate-fir', payload),
  requestFirApprovalOtp: (approvalId: string) =>
    api.post('/police/request-fir-approval-otp', { approval_id: approvalId }),
  approveFir: (payload: {
    fir_draft_id?: string
    approval_id: string
    station_code?: string
    officer_name?: string
    summary?: string
    fir_data: unknown
    otp_code: string
  }) => api.post('/police/approve-fir', payload),
}

// ── FIR Drafts ──────────────────────────────────────────────
export const firDraftsAPI = {
  saveDraft: (payload: any) => api.post('/fir/drafts', payload),
  getDrafts: () => api.get('/fir/drafts'),
  getDraft: (draftId: string) => api.get(`/fir/drafts/${draftId}`),
  deleteDraft: (draftId: string) => api.delete(`/fir/drafts/${draftId}`),
}

