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
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Generate or restore session ID
    let sid = sessionStorage.getItem('lawaid_chat_session')
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 9)
      sessionStorage.setItem('lawaid_chat_session', sid)
    }
    setSessionId(sid)
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim()
    if (!query || loading) return

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
                className="text-xs bg-white border border-gray-200 hover:border-lawblue hover:bg-lblue text-gray-700 px-3 py-1.5 rounded-full whitespace-nowrap transition shrink-0 shadow-sm"
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

          {/* Chat input box */}
          <div className="bg-white rounded-2xl p-2 shadow-sm border border-gray-200 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Ask a legal question or describe a situation (e.g. 'Is bail available for Section 318?')..."
              className="flex-1 px-4 py-2 text-xs outline-none text-gray-800"
              disabled={loading}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="bg-lawblue text-white px-5 py-2 rounded-xl text-xs font-bold hover:bg-navy transition disabled:opacity-50"
            >
              Send →
            </button>
          </div>
        </main>
      </div>
    </div>
  )
}