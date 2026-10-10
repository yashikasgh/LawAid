'use client'

export function ApiMessage({ error, success }: { error?: string; success?: string }) {
  if (!error && !success) return null
  return <p role={error ? 'alert' : 'status'} className={`mb-4 rounded-lg border p-3 text-sm ${error ? 'border-red-300 bg-red-50 text-red-800' : 'border-emerald-300 bg-emerald-50 text-emerald-800'}`}>{error || success}</p>
}

export function apiError(error: unknown, fallback: string) {
  const value = error as { response?: { status?: number; data?: { detail?: string } }; message?: string }
  if (value.response?.status === 401) return 'Your session has expired. Redirecting to login.'
  return value.response?.data?.detail || value.message || fallback
}
