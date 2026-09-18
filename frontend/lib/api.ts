// lib/api.ts
import axios from 'axios'

// This connects to the backend server
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Automatically attach the login token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('lawaid_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// UI shows 'Citizen' / 'Police' / 'Lawyer' (capitalized tabs), but backend
// stores role as lowercase. Always convert before sending to the API.
export const toApiRole = (uiRole: string) => uiRole.toLowerCase()

// ── Auth ─────────────────────────────────────────────────────
// NOTE: backend's /auth/login and /auth/register both use the same
// UserCreate schema (email, password, role — role is REQUIRED), so
// login must send role even though that's a little unusual.
export const authAPI = {
  login: (email: string, password: string, role: string) =>
    api.post('/auth/login', { email, password, role: toApiRole(role) }),

  register: (email: string, password: string, role: string) =>
    api.post('/auth/register', { email, password, role: toApiRole(role) }),

  me: () => api.get('/auth/me'),

  logout: () => api.post('/auth/logout'),
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
  approveFir: (draftId: string) =>
    api.post('/police/approve-fir', { fir_draft_id: draftId }),
}