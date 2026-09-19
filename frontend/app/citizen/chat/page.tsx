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

function parseInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  const regex = /(\*\*|__)(.*?)\1|(\*|_)(.*?)\3/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    if (match[1]) {
      parts.push(
        <strong key={match.index} className="font-semibold text-[#12335B]">
          {match[2]}
        </strong>
      )
    } else if (match[3]) {
      parts.push(
        <em key={match.index} className="italic text-[#315b82]">
          {match[4]}
        </em>
      )
    }
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts
}

function renderStatusBadge(statusText: string) {
  const cleanStatus = statusText.replace(/\*/g, '').trim()
  const s = cleanStatus.toLowerCase()
  if (s.includes('established')) {
    return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium px-2 py-0.5 rounded text-xs inline-block">{cleanStatus}</span>
  } else if (s.includes('potential') || s.includes('material fact') || s.includes('missing')) {
    return <span className="bg-amber-50 text-amber-700 border border-amber-200 font-medium px-2 py-0.5 rounded text-xs inline-block">{cleanStatus}</span>
  } else if (s.includes('insufficient') || s.includes('uncertain')) {
    return <span className="bg-blue-50 text-blue-700 border border-blue-200 font-medium px-2 py-0.5 rounded text-xs inline-block">{cleanStatus}</span>
  } else {
    return <span className="bg-slate-100 text-slate-700 border border-slate-200 font-medium px-2 py-0.5 rounded text-xs inline-block">{cleanStatus}</span>
  }
}

function RenderMarkdown({ content }: { content: string }) {
  if (!content) return null

  const rawLines = content.split('\n')
  const elements: React.ReactNode[] = []
  let currentList: { type: 'ul' | 'ol'; items: React.ReactNode[] } | null = null
  let currentTable: string[] | null = null

  const flushList = (keyPrefix: string) => {
    if (!currentList) return
    if (currentList.type === 'ul') {
      elements.push(
        <ul key={`${keyPrefix}-ul`} className="list-disc list-outside ml-5 space-y-1.5 my-2 text-slate-800">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="leading-relaxed pl-1">
              {item}
            </li>
          ))}
        </ul>
      )
    } else {
      elements.push(
        <ol key={`${keyPrefix}-ol`} className="list-decimal list-outside ml-5 space-y-1.5 my-2 text-slate-800">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="leading-relaxed pl-1">
              {item}
            </li>
          ))}
        </ol>
      )
    }
    currentList = null
  }

  const flushTable = (keyPrefix: string) => {
    if (!currentTable || currentTable.length === 0) return
    const tableLines = [...currentTable]
    currentTable = null

    const parsedRows = tableLines
      .map(line => {
        const parts = line.split('|').map(cell => cell.trim())
        if (parts.length >= 3 && parts[0] === '' && parts[parts.length - 1] === '') {
          return parts.slice(1, -1)
        }
        return parts.filter(c => c !== '')
      })
      .filter(row => row.length > 0 && !row.every(cell => /^[\-:]+$/.test(cell)))

    if (parsedRows.length === 0) return

    const headerRow = parsedRows[0]
    const dataRows = parsedRows.slice(1)

    elements.push(
      <div key={`${keyPrefix}-tbl`} className="my-3 overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs md:text-sm border-collapse">
          <thead>
            <tr className="bg-[#12335B] text-white">
              {headerRow.map((col, idx) => (
                <th key={idx} className="px-3 py-2.5 font-semibold tracking-wide border-b border-[#12335B]">
                  {parseInlineMarkdown(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {dataRows.map((row, rIdx) => (
              <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2.5 text-slate-800 leading-relaxed align-top break-words">
                    {cIdx === 0 ? (
                      <span className="font-bold text-[#12335B]">{parseInlineMarkdown(cell)}</span>
                    ) : cIdx === row.length - 1 && (row.length === 4 || row.length === 5) ? (
                      renderStatusBadge(cell)
                    ) : (
                      parseInlineMarkdown(cell)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  rawLines.forEach((rawLine, idx) => {
    const line = rawLine.trim()
    if (!line) {
      flushList(`flush-${idx}`)
      flushTable(`tbl-flush-${idx}`)
      return
    }

    const isTableLine = line.includes('|') && (line.startsWith('|') || line.endsWith('|'))

    if (isTableLine) {
      flushList(`tbl-b-${idx}`)
      if (!currentTable) {
        currentTable = []
      }
      currentTable.push(line)
      return
    } else {
      flushTable(`p-tbl-${idx}`)
    }

    const bulletMatch = line.match(/^[\-\*•]\s+(.*)/)
    const numMatch = line.match(/^(\d+)\.\s+(.*)/)
    const headingMatch = line.match(/^(#{1,6})\s+(.*)/)

    if (headingMatch) {
      flushList(`h-${idx}`)
      const level = headingMatch[1].length
      const titleText = headingMatch[2]
      elements.push(
        <div key={`h-${idx}`} className={`font-bold text-[#12335B] mt-3 mb-1 ${level === 1 ? 'text-lg' : 'text-base'}`}>
          {parseInlineMarkdown(titleText)}
        </div>
      )
    } else if (bulletMatch) {
      if (!currentList || currentList.type !== 'ul') {
        flushList(`b-${idx}`)
        currentList = { type: 'ul', items: [] }
      }
      currentList.items.push(parseInlineMarkdown(bulletMatch[1]))
    } else if (numMatch) {
      if (!currentList || currentList.type !== 'ol') {
        flushList(`n-${idx}`)
        currentList = { type: 'ol', items: [] }
      }
      currentList.items.push(parseInlineMarkdown(numMatch[2]))
    } else {
      flushList(`p-${idx}`)
      elements.push(
        <p key={`p-${idx}`} className="leading-relaxed my-1 text-slate-800">
          {parseInlineMarkdown(line)}
        </p>
      )
    }
  })

  flushList('final')
  flushTable('final-tbl')

  return <div className="space-y-1.5 text-sm md:text-base text-slate-800">{elements}</div>
}

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
  const [isListening, setIsListening] = useState(false)
  const [deleteModalSessionId, setDeleteModalSessionId] = useState<string | null>(null)

  const chatEndRef = useRef<HTMLDivElement>(null)

  async function confirmDeleteSession(sid: string) {
    try {
      const token = localStorage.getItem('lawaid_token')
      const res = await fetch(`http://localhost:8000/api/chat/session/${sid}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      })
      if (res.ok) {
        setDeleteModalSessionId(null)
        if (sessionId === sid) {
          startNewChat()
        } else {
          loadSessions()
        }
      }
    } catch(e) {
      console.error(e)
    }
  }

  function startVoiceInput() {
    if (typeof window === 'undefined') return
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Please type your legal query.")
      return
    }

    if (isListening) return

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = true
      recognition.lang = 'en-IN'

      recognition.onstart = () => {
        setIsListening(true)
      }

      recognition.onresult = (event: any) => {
        let transcript = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript
        }
        if (transcript) {
          setInput(prev => {
            const trimmed = prev.trim()
            return trimmed ? `${trimmed} ${transcript}` : transcript
          })
        }
      }

      recognition.onerror = (event: any) => {
        setIsListening(false)
        if (event.error === 'not-allowed') {
          alert("Microphone permission was denied. Please enable microphone access in your browser settings.")
        }
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognition.start()
    } catch (err) {
      console.error(err)
      setIsListening(false)
    }
  }
  
  async function loadSessions() {
    try {
      const token = localStorage.getItem('lawaid_token')
      const res = await fetch("http://localhost:8000/api/chat/sessions", {
        headers: { "Authorization": `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSessions(data)
        return data
      }
    } catch(e) {
      console.error(e)
    }
    return []
  }

  async function initChat() {
    const existingSessions = await loadSessions()
    const storedSid = sessionStorage.getItem('lawaid_chat_session')

    if (storedSid && existingSessions.some((s: any) => s.session_id === storedSid)) {
      setSessionId(storedSid)
      loadHistory(storedSid)
    } else if (existingSessions.length > 0) {
      const latestSid = existingSessions[0].session_id
      setSessionId(latestSid)
      sessionStorage.setItem('lawaid_chat_session', latestSid)
      loadHistory(latestSid)
    } else {
      startNewChat()
    }
  }

  useEffect(() => {
    initChat()
  }, [])
  
  async function startNewChat() {
    try {
      const token = localStorage.getItem('lawaid_token')
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
            content: 'Hello! I am your LawAid Legal Assistant. You can ask me questions about Indian Criminal Law (Bharatiya Nyaya Sanhita - BNS 2023), citizen rights, FIR procedures, or bailable vs non-bailable offences. How can I help you today?',
          },
        ])
      }
    } catch(e) {
      console.error(e)
    }
  }
  
  async function loadHistory(sid: string) {
    try {
      const token = localStorage.getItem('lawaid_token')
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
      const token = localStorage.getItem('lawaid_token')
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

  const isConversationActive = messages.some(m => m.role === 'user')

  return (
    <div className="min-h-screen text-[#12335B]">
      <Navbar />

      <main className="relative h-[calc(100vh-64px)] max-h-[calc(100vh-64px)] overflow-hidden">

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

        <div className="flex h-full w-full overflow-hidden">

          {/* =========================
              CONVERSATION SIDEBAR
          ========================== */}
          <aside className="w-64 shrink-0 h-full bg-[#12335B]/95 text-white flex flex-col border-r border-white/10 backdrop-blur-md overflow-hidden">

            {/* New Chat */}
            <div className="p-4 border-b border-white/10 shrink-0">
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
            <div className="px-5 pt-6 pb-3 shrink-0">
              <div className="flex items-center gap-3">
                <span className="h-px w-8 bg-[#b98528]" />

                <p className="text-[10px] uppercase tracking-[0.25em] text-white/60 font-semibold">
                  Previous Conversations
                </p>
              </div>
            </div>

            {/* Conversation list */}
            <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-1 min-h-0">

              {sessions.map((conversation) => (
                <div
                  key={conversation.session_id}
                  className={`group relative flex items-center justify-between w-full rounded-xl text-sm transition ${
                    sessionId === conversation.session_id
                      ? 'bg-white/15 text-white shadow-sm'
                      : 'text-white/70 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setSessionId(conversation.session_id)
                      sessionStorage.setItem('lawaid_chat_session', conversation.session_id)
                      loadHistory(conversation.session_id)
                    }}
                    className="flex-1 text-left px-3 py-3 flex items-center gap-3 min-w-0 pr-8"
                  >
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
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteModalSessionId(conversation.session_id)
                    }}
                    title="Delete conversation"
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-white/40 hover:text-red-400 opacity-0 group-hover:opacity-100 transition rounded-lg hover:bg-white/10"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}

            </div>

            {/* Sidebar footer */}
            <div className="border-t border-white/10 p-4 shrink-0">
              <p className="text-[11px] text-white/40 leading-relaxed">
                Your conversations will appear here.
              </p>
            </div>

          </aside>

          {/* Delete Confirmation Modal */}
          {deleteModalSessionId && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
              <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-gray-100 text-[#12335B]">
                <h3 className="font-semibold text-lg text-gray-900 mb-2">Delete this conversation?</h3>
                <p className="text-sm text-gray-600 mb-6 leading-relaxed">
                  This conversation and its messages will be permanently deleted.
                </p>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setDeleteModalSessionId(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => confirmDeleteSession(deleteModalSessionId)}
                    className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl transition shadow-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* =========================
              MAIN CHAT
          ========================== */}
          <section className="flex-1 min-w-0 h-full flex flex-col overflow-hidden">

            <main className={`max-w-5xl mx-auto px-4 sm:px-6 flex flex-col h-[calc(100vh-64px)] min-h-0 ${isConversationActive ? 'py-4' : 'py-6'}`}>

              {/* Header (Shown only before first user message) */}
              {!isConversationActive && (
                <div className="mb-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="h-px w-8 bg-[#b98528]" />
                    <span className="text-[11px] tracking-[0.25em] uppercase text-white font-medium">
                      LEGAL ASSISTANCE
                    </span>
                  </div>

                  <h1 className="font-serif text-3xl sm:text-4xl font-semibold text-[#cc8427] tracking-[-0.025em]">
                    Legal Assistant
                  </h1>

                  <p className="mt-1 text-[#dca45a] text-xs sm:text-sm font-medium">
                    Interactive guidance grounded in the Bharatiya Nyaya Sanhita (BNS) 2023.
                  </p>
                </div>
              )}

              {/* Quick prompts (Shown only before first user message) */}
              {!isConversationActive && (
                <div className="flex gap-2 overflow-x-auto pb-2 mb-3 scrollbar-none">
                  {QUICK_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(q)}
                      className="text-xs bg-white/90 border border-[#d9d4ca] hover:border-[#b98528] hover:bg-white text-[#315b82] px-3.5 py-1.5 rounded-full whitespace-nowrap transition shrink-0 shadow-sm backdrop-blur-sm font-medium"
                    >
                      💡 {q}
                    </button>
                  ))}
                </div>
              )}

              {/* Chat message box */}
              <div className="flex-1 bg-white/85 backdrop-blur-md rounded-[20px] p-4 sm:p-6 shadow-[0_15px_40px_rgba(18,51,91,0.12)] border border-white/70 overflow-y-auto space-y-5 mb-3 min-h-0">

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
                      className={`max-w-3xl sm:max-w-4xl px-5 py-3.5 rounded-[16px] text-sm leading-relaxed ${
                        m.role === 'user'
                          ? 'bg-[#12335B] text-white rounded-br-none whitespace-pre-line'
                          : 'bg-[#f8f6f1]/90 text-[#315b82] border border-[#d9d4ca] rounded-bl-none'
                      }`}
                    >
                      {m.role === 'assistant' ? (
                        <RenderMarkdown content={m.content} />
                      ) : (
                        m.content
                      )}
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
              <div className="bg-white/90 backdrop-blur-md rounded-[18px] p-2 shadow-[0_15px_40px_rgba(18,51,91,0.10)] border border-white/70 flex gap-2 items-center shrink-0">

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
                  type="button"
                  onClick={startVoiceInput}
                  disabled={loading}
                  title={isListening ? "Listening..." : "Click to speak"}
                  className={`p-3 rounded-[14px] text-sm transition flex items-center justify-center border ${
                    isListening
                      ? 'bg-red-500 text-white border-red-600 animate-pulse'
                      : 'bg-[#f8f6f1] text-[#315b82] border-[#d9d4ca] hover:border-[#b98528] hover:text-[#b98528]'
                  }`}
                >
                  🎙️
                </button>

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