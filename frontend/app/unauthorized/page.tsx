'use client'

import { useRouter } from 'next/navigation'

export default function UnauthorizedPage() {
  const router = useRouter()

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-100 px-6">
      <div className="w-full max-w-lg rounded-2xl bg-white p-10 text-center shadow-lg">
        <div className="mb-5 text-5xl">🔒</div>

        <h1 className="text-3xl font-bold text-[#12335B]">
          Access Denied
        </h1>

        <p className="mt-4 text-gray-600">
          You do not have permission to access this dashboard.
        </p>

        <button
          onClick={() => router.back()}
          className="mt-8 rounded-lg bg-[#12335B] px-6 py-3 font-semibold text-white hover:opacity-90"
        >
          Go Back
        </button>
      </div>
    </main>
  )
}