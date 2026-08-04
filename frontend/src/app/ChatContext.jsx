import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { askQuestion, fetchExamples, fetchHealth } from '../api'

const FALLBACK_EXAMPLES = [
  'What are the top 5 products by total revenue?',
  'How many orders were placed in each city?',
  'Which customers have spent more than $500?',
  'What is the average product rating by category?',
]

const ChatContext = createContext(null)

let turnSeq = 0

export function ChatProvider({ children }) {
  const [draft, setDraft] = useState('')
  const [turns, setTurns] = useState([])
  const [busy, setBusy] = useState(false)
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES)
  const [online, setOnline] = useState(false)
  const [model, setModel] = useState('')
  const [provider, setProvider] = useState('')

  useEffect(() => {
    let cancelled = false

    async function boot() {
      try {
        const [health, ex] = await Promise.all([
          fetchHealth(),
          fetchExamples().catch(() => ({ examples: FALLBACK_EXAMPLES })),
        ])
        if (cancelled) return
        setOnline(health.status === 'ok')
        setModel(health.model || '')
        setProvider(health.provider || '')
        if (ex.examples?.length) setExamples(ex.examples)
      } catch {
        if (!cancelled) setOnline(false)
      }
    }

    boot()
    const id = window.setInterval(boot, 20000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const runQuestion = useCallback(async (question) => {
    const q = question.trim()
    if (!q || busy) return null

    const id = `t-${++turnSeq}`
    setBusy(true)
    setDraft('')
    setTurns((prev) => [...prev, { id, question: q, status: 'loading', createdAt: Date.now() }])

    try {
      const result = await askQuestion(q)
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, status: 'done', result } : t)),
      )
      return id
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, status: 'error', error: err.message || 'Something went wrong' }
            : t,
        ),
      )
      return id
    } finally {
      setBusy(false)
    }
  }, [busy])

  const clearHistory = useCallback(() => setTurns([]), [])

  const value = useMemo(
    () => ({
      draft,
      setDraft,
      turns,
      busy,
      examples,
      online,
      model,
      provider,
      runQuestion,
      clearHistory,
    }),
    [draft, turns, busy, examples, online, model, provider, runQuestion, clearHistory],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
