// app/citizen/chat/page.tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import Navbar from '@/components/Navbar'
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

const PREVIOUS_CONVERSATIONS = [
  {
    id: 1,
    title: 'Rights when police refuse FIR',
  },
  {
    id: 2,
    title: 'Online cheating and cyber fraud',
  },
  {
    id: 3,
    title: 'Criminal intimidation and bail',
  },
  {
    id: 4,
    title: 'Understanding Zero FIR',
  },
  {
    id: 5,
    title: 'BNS Section 318',
  },
  {
    id: 6,
    title: 'FIR filing procedure',
  },
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
  const [sessions, setSessions] = useState<any[]>([])

  const chatEndRef = useRef<HTMLDivElement>(null)
  
  async function loadSessions() {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch("http://localhost:8000/api/chat/sessions", {
        headers: { "Authorization": `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSessions(data)
      }
    } catch(e) {
      console.error(e)
    }
  }

  useEffect(() => {
    loadSessions()
    
    // Generate or restore session ID
    let sid = sessionStorage.getItem('lawaid_chat_session')
    if (!sid) {
      startNewChat()
    } else {
      setSessionId(sid)
      loadHistory(sid)
    }
  }, [])
  
  async function startNewChat() {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch("http://localhost:8000/api/chat/session", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSessionId(data.session_id)
        sessionStorage.setItem('lawaid_chat_session', data.session_id)
        setMessages([
          {
            role: 'assistant',
            content: 'Hello! I am your LawAid Legal Assistant. How can I help you today?',
          },
        ])
        loadSessions()
      }
    } catch(e) {
      console.error(e)
    }
  }
  
  async function loadHistory(sid: string) {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`http://localhost:8000/api/chat/history/${sid}`, {
        headers: { "Authorization": `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        if (data.messages && data.messages.length > 0) {
           setMessages(data.messages)
        }
      }
    } catch(e) {
      console.error(e)
    }
  }

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
      const token = localStorage.getItem('access_token')
      const res = await fetch("http://localhost:8000/api/chat/message", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, message: query })
      })
      
      const data = await res.json()
      
      const botReply = data.reply || 'I received your query but could not retrieve specific sections.'
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: botReply },
      ])
      
      loadSessions() // Refresh sidebar
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
    <div className="min-h-screen text-[#12335B]">
      <Navbar />

      <main className="relative min-h-[calc(100vh-64px)] overflow-hidden">

        {/* Background */}
        <div className="fixed inset-0 -z-10">
          <img
            src="/images/lawaid-feature-bg.png"
            alt="LawAid legal background"
            className="h-full w-full object-cover object-center"
          />
        </div>

        {/* Light overlay */}
        <div className="fixed inset-0 -z-10 bg-[#f8f6f1]/10" />

        <div className="flex min-h-[calc(100vh-64px)]">

          {/* =========================
              CONVERSATION SIDEBAR
          ========================== */}
          <aside className="w-64 shrink-0 bg-[#12335B]/95 text-white flex flex-col border-r border-white/10 backdrop-blur-md">

            {/* New Chat */}
            <div className="p-4 border-b border-white/10">
              <button
                type="button"
                onClick={startNewChat}
                className="w-full flex items-center justify-center gap-2 rounded-full border border-[#d2a14b]/60 bg-[#b98528] px-4 py-3 text-sm font-semibold text-white hover:bg-[#9f7020] transition"
              >
                <span className="text-lg leading-none">+</span>
                New Chat
              </button>
            </div>

            {/* Conversation heading */}
            <div className="px-5 pt-6 pb-3">
              <div className="flex items-center gap-3">
                <span className="h-px w-8 bg-[#b98528]" />

                <p className="text-[10px] uppercase tracking-[0.25em] text-white/60 font-semibold">
                  Previous Conversations
                </p>
              </div>
            </div>

            {/* Conversation list */}
            <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1">

              {sessions.map((conversation) => (
                <button
                  key={conversation.session_id}
                  type="button"
                  onClick={() => {
                    setSessionId(conversation.session_id)
                    sessionStorage.setItem('lawaid_chat_session', conversation.session_id)
                    loadHistory(conversation.session_id)
                  }}
                  className={`w-full text-left px-3 py-3 rounded-xl text-sm transition ${
                    sessionId === conversation.session_id
                      ? 'bg-white/15 text-white shadow-sm'
                      : 'text-white/70 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">

                    <span
                      className={`text-sm shrink-0 ${
                        sessionId === conversation.session_id
                          ? 'text-[#d2a14b]'
                          : 'text-white/45'
                      }`}
                    >
                      💬
                    </span>

                    <span className="truncate">
                      {conversation.preview}
                    </span>

                  </div>
                </button>
              ))}

            </div>

            {/* Sidebar footer */}
            <div className="border-t border-white/10 p-4">
              <p className="text-[11px] text-white/40 leading-relaxed">
                Your conversations will appear here.
              </p>
            </div>

          </aside>

          {/* =========================
              MAIN CHAT
          ========================== */}
          <section className="flex-1 min-w-0">

            <main className="max-w-6xl mx-auto px-6 sm:px-8 py-10 flex flex-col h-[calc(100vh-64px)] min-h-0">

              {/* Header */}
              <div className="mb-6">

                <div className="flex items-center gap-3 mb-4">
                  <span className="h-px w-10 bg-[#b98528]" />

                  <span className="text-[11px] tracking-[0.3em] uppercase text-white font-medium">
                    LEGAL ASSISTANCE
                  </span>
                </div>

                <h1 className="font-serif text-4xl md:text-5xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                  Legal Assistant
                </h1>

                <p className="mt-3 text-[#dca45a] text-sm md:text-base">
                  Interactive guidance grounded in the Bharatiya Nyaya Sanhita
                  (BNS) 2023.
                </p>

              </div>

              {/* Quick prompts */}
              <div className="flex gap-2 overflow-x-auto pb-3 mb-3 scrollbar-none">

                {QUICK_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="text-xs bg-white/80 border border-[#d9d4ca] hover:border-[#b98528] hover:bg-white text-[#315b82] px-4 py-2 rounded-full whitespace-nowrap transition shrink-0 shadow-sm backdrop-blur-sm"
                  >
                    💡 {q}
                  </button>
                ))}

              </div>

              {/* Chat message box */}
              <div className="flex-1 bg-white/80 backdrop-blur-md rounded-[20px] p-5 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 overflow-y-auto space-y-5 mb-4 min-h-0">

                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 ${
                      m.role === 'user'
                        ? 'justify-end'
                        : 'justify-start'
                    }`}
                  >

                    {m.role === 'assistant' && (
                      <div className="w-9 h-9 rounded-full bg-[#12335B] text-[#d2a14b] flex items-center justify-center font-bold text-xs shrink-0 border border-[#b98528]/60">
                        ⚖
                      </div>
                    )}

                    <div
                      className={`max-w-2xl px-5 py-3.5 rounded-[16px] text-sm leading-relaxed ${
                        m.role === 'user'
                          ? 'bg-[#12335B] text-white rounded-br-none'
                          : 'bg-[#f8f6f1]/90 text-[#315b82] border border-[#d9d4ca] rounded-bl-none whitespace-pre-line'
                      }`}
                    >
                      {m.content}
                    </div>

                    {m.role === 'user' && (
                      <div className="w-9 h-9 rounded-full bg-[#e8e4dc] text-[#12335B] flex items-center justify-center font-bold text-xs shrink-0 border border-[#d9d4ca]">
                        👤
                      </div>
                    )}

                  </div>
                ))}

                {loading && (
                  <div className="flex gap-3 items-center">

                    <div className="w-9 h-9 rounded-full bg-[#12335B] text-[#d2a14b] flex items-center justify-center font-bold text-xs border border-[#b98528]/60">
                      ⚖
                    </div>

                    <div className="bg-[#f8f6f1]/90 border border-[#d9d4ca] px-5 py-3.5 rounded-[16px] text-sm text-[#7890a8] italic animate-pulse">
                      Consulting BNS legal corpus & drafting guidance...
                    </div>

                  </div>
                )}

                <div ref={chatEndRef} />

              </div>

              {/* Chat input box */}
              <div className="bg-white/85 backdrop-blur-md rounded-[18px] p-2 shadow-[0_15px_40px_rgba(18,51,91,0.10)] border border-white/70 flex gap-2">

                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e =>
                    e.key === 'Enter' && handleSend()
                  }
                  placeholder="Ask a legal question or describe a situation (e.g. 'Is bail available for Section 318?')..."
                  className="flex-1 px-4 py-3 text-sm outline-none text-[#315b82] bg-transparent placeholder:text-[#7890a8]"
                  disabled={loading}
                />

                <button
                  onClick={() => handleSend()}
                  disabled={loading || !input.trim()}
                  className="bg-[#b98528] text-white px-6 py-3 rounded-[14px] text-sm font-semibold hover:bg-[#9f7020] transition disabled:opacity-50"
                >
                  Send →
                </button>

              </div>

            </main>

          </section>
        </div>
      </main>
    </div>
  )
}