// app/citizen/understand/page.tsx
'use client'
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import { firAPI } from '@/lib/api'

export default function UnderstandPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await firAPI.understand(files[0])
      setResult(res.data)
    } catch {
      setError('Upload failed. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': [] },
  })

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex">
        <CitizenSidebar />
        <main className="flex-1 p-8">
          <h1 className="text-2xl font-bold text-navy mb-6">Understand Your FIR</h1>

          <div className="flex gap-6">
            {/* Upload box */}
            <div
              {...getRootProps()}
              className={`w-96 border-2 border-dashed rounded-2xl p-8 flex flex-col items-center cursor-pointer transition ${
                isDragActive ? 'border-lawblue bg-lblue' : 'border-gray-300 hover:border-lawblue bg-white'
              }`}
            >
              <input {...getInputProps()} />
              <div className="text-5xl mb-4">📄</div>
              <p className="text-center font-semibold text-gray-600 mb-2">
                {isDragActive ? 'Drop it here!' : 'Drag & drop your FIR here'}
              </p>
              <p className="text-sm text-gray-400">or click to browse files</p>
              <p className="text-xs text-gray-400 mt-2">Supports: PDF, JPG, PNG</p>
            </div>

            {/* Results */}
            {loading && <div className="flex-1 animate-pulse bg-gray-200 rounded-2xl h-96" />}
            {error && <p className="text-red-500 text-sm">{error}</p>}
            {result && (
              <div className="flex-1 bg-white rounded-2xl p-6 shadow-md space-y-4">
                <span className="bg-lgreen text-green-700 text-sm font-bold px-3 py-1 rounded-full">
                  ✓ File Uploaded
                </span>

                {result._mocked && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3">
                    <p className="text-xs text-yellow-800 font-semibold">
                      ⚠ Development note: FIR explanation is not yet built on the backend.
                      This is placeholder text, not a real AI-generated explanation.
                    </p>
                  </div>
                )}

                <div className="bg-lgreen rounded-xl p-4">
                  <h3 className="font-bold text-navy mb-2">Summary</h3>
                  <p className="text-sm text-gray-700 whitespace-pre-line">{result.explanation}</p>
                </div>

                <p className="text-xs text-gray-400">File ID: {result.file_id}</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}