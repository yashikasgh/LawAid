// app/citizen/chat/page.tsx
'use client'
import { useState, useEffect, useRef } from 'react'
import Navbar from '@/components/Navbar'
import CitizenSidebar from '@/components/CitizenSidebar'
import { chatAPI } from '@/lib/api'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

const QUICK_QUESTIONS = [
  "What are my rights if the police refuse to file an FIR?",
  "What is the punishment for online cheating or cyber fraud under BNS?",
  "Is criminal intimidation a bailable offence in India?",
  "What is a 'Zero FIR' and where can I file it?",
]

export default function CitizenChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am your LawAid Legal Assistant. You can ask me questions about Indian Criminal Law (Bharatiya Nyaya Sanhita - BNS 2023), citizen rights, FIR procedures, or bailable vs non-bailable offences. How can I help you today?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [speechNotice, setSpeechNotice] = useState('')

  const chatEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)

  const baseTextRef = useRef<string>('')
  const hasCapturedSpeechRef = useRef<boolean>(false)

  useEffect(() => {
    // Generate or restore session ID
    let sid = sessionStorage.getItem('lawaid_chat_session')
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 9)
      sessionStorage.setItem('lawaid_chat_session', sid)
    }
    setSessionId(sid)

    // Check Speech Recognition browser support
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (SpeechRecognition) {
        setSpeechSupported(true)
      }
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleToggleSpeech() {
    if (typeof window === 'undefined') return
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      setSpeechNotice('Voice input is not supported in this browser.')
      setTimeout(() => setSpeechNotice(''), 4000)
      return
    }

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {
          // ignore error if already stopped
        }
      }
      setIsListening(false)
      return
    }

    // Save existing typed text as base and reset captured speech flag before starting recognition
    baseTextRef.current = input.trim()
    hasCapturedSpeechRef.current = false

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-IN'

      recognition.onstart = () => {
        setIsListening(true)
        setSpeechNotice('')
      }

      recognition.onresult = (event: any) => {
        let finalTranscript = ''
        let interimTranscript = ''

        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i]
          const text = result[0].transcript
          if (result.isFinal) {
            finalTranscript += text + ' '
          } else {
            interimTranscript += text
          }
        }

        const base = baseTextRef.current
        const finalPart = finalTranscript.trim()
        const interimPart = interimTranscript.trim()

        if (finalPart || interimPart) {
          hasCapturedSpeechRef.current = true
        }

        let combined = base
        if (finalPart) {
          combined = combined ? `${combined} ${finalPart}` : finalPart
        }
        if (interimPart) {
          combined = combined ? `${combined} ${interimPart}` : interimPart
        }

        setInput(combined)
      }

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error event:', event.error)
        setIsListening(false)

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setSpeechNotice('Microphone permission was denied. Please allow microphone access in your browser.')
          setTimeout(() => setSpeechNotice(''), 5000)
        } else if (event.error === 'no-speech' || event.error === 'aborted') {
          // Normal timeout or manual stop - silently finish without error banner
        } else if (event.error === 'network') {
          // If speech was successfully captured, network stream closing is normal - suppress misleading error notice!
          if (!hasCapturedSpeechRef.current) {
            setSpeechNotice('Speech recognition network service unavailable.')
            setTimeout(() => setSpeechNotice(''), 4000)
          }
        } else {
          // Only show notice for other errors if no speech was captured
          if (!hasCapturedSpeechRef.current) {
            setSpeechNotice(`Speech recognition notice: ${event.error || 'Stopped.'}`)
            setTimeout(() => setSpeechNotice(''), 4000)
          }
        }
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (err) {
      console.error('Failed to start speech recognition:', err)
      setIsListening(false)
      setSpeechNotice('Failed to start voice input.')
      setTimeout(() => setSpeechNotice(''), 4000)
    }
  }

  async function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim()
    if (!query || loading) return

    // Stop active speech recognition if user clicks send while recording
    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {}
      setIsListening(false)
    }

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setLoading(true)

    try {
      const res = await chatAPI.sendMessage(sessionId, query)
      const botReply = res.data.reply || 'I received your query but could not retrieve specific sections.'
      setMessages(prev => [...prev, { role: 'assistant', content: botReply }])
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I am unable to connect to the legal knowledge server right now. Please ensure the backend is running.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Navbar />
      <div className="flex flex-1">
        <CitizenSidebar />
        <main className="flex-1 p-6 max-w-5xl flex flex-col h-[calc(100vh-64px)]">
          <div className="mb-4">
            <h1 className="text-2xl font-bold text-navy">Legal Assistant Chat</h1>
            <p className="text-xs text-gray-500">
              Interactive guidance grounded in the Bharatiya Nyaya Sanhita (BNS) 2023.
            </p>
          </div>

          {/* Quick prompts */}
          <div className="flex gap-2 overflow-x-auto pb-2 mb-3 scrollbar-none">
            {QUICK_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="text-xs bg-white border border-gray-200 hover:border-lawblue hover:bg-lblue text-gray-700 px-3 py-1.5 rounded-full whitespace-nowrap transition shrink-0 shadow-sm focus:outline-none focus:ring-2 focus:ring-lawblue"
              >
                💡 {q}
              </button>
            ))}
          </div>

          {/* Chat message box */}
          <div className="flex-1 bg-white rounded-2xl p-4 shadow-sm border border-gray-100 overflow-y-auto space-y-4 mb-4">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-lawblue text-white flex items-center justify-center font-bold text-xs shrink-0">
                    ⚖
                  </div>
                )}
                <div
                  className={`max-w-2xl px-4 py-3 rounded-2xl text-xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-navy text-white rounded-br-none'
                      : 'bg-gray-50 text-gray-800 border border-gray-100 rounded-bl-none whitespace-pre-line'
                  }`}
                >
                  {m.content}
                </div>
                {m.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-700 flex items-center justify-center font-bold text-xs shrink-0">
                    👤
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 items-center">
                <div className="w-8 h-8 rounded-full bg-lawblue text-white flex items-center justify-center font-bold text-xs">
                  ⚖
                </div>
                <div className="bg-gray-50 border border-gray-100 px-4 py-3 rounded-2xl text-xs text-gray-500 italic animate-pulse">
                  Consulting BNS legal corpus & drafting guidance...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Speech notice notification banner if present */}
          {speechNotice && (
            <div className="text-xs text-amber-800 bg-amber-50 px-3 py-2 rounded-xl border border-amber-200 mb-2 flex items-center justify-between shadow-sm">
              <span>⚠️ {speechNotice}</span>
              <button
                onClick={() => setSpeechNotice('')}
                className="text-amber-600 hover:text-amber-900 font-bold text-xs px-1"
                title="Dismiss"
              >
                ✕
              </button>
            </div>
          )}

          {/* Chat input box */}
          <div className="bg-white rounded-2xl p-2 shadow-sm border border-gray-200 flex items-center gap-2">
            <button
              type="button"
              onClick={handleToggleSpeech}
              disabled={loading}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              title={
                !speechSupported
                  ? 'Voice input is not supported in this browser'
                  : isListening
                  ? 'Click to stop listening'
                  : 'Click to speak your legal question'
              }
              className={`p-2 sm:px-3 sm:py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shrink-0 focus:outline-none focus:ring-2 focus:ring-lawblue ${
                isListening
                  ? 'bg-rose-500 text-white animate-pulse shadow-md shadow-rose-200'
                  : speechSupported
                  ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed opacity-60'
              }`}
            >
              <span className="text-sm">{isListening ? '🛑' : '🎙️'}</span>
              <span className="hidden sm:inline">
                {isListening ? 'Listening...' : 'Voice'}
              </span>
            </button>

            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder={
                isListening
                  ? 'Listening to your speech... Speak now or edit below.'
                  : "Ask a legal question or describe a situation (e.g. 'Is bail available for Section 318?')..."
              }
              className={`flex-1 px-3 py-2 text-xs outline-none text-gray-800 rounded-lg transition-colors ${
                isListening ? 'bg-rose-50/50 placeholder-rose-400' : ''
              }`}
              disabled={loading}
            />

            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="bg-lawblue text-white px-4 sm:px-5 py-2 rounded-xl text-xs font-bold hover:bg-navy transition disabled:opacity-50 shrink-0 focus:outline-none focus:ring-2 focus:ring-lawblue"
            >
              Send →
            </button>
          </div>
        </main>
      </div>
    </div>
  )
}