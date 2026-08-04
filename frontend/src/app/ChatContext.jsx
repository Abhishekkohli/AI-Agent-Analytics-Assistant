import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { askQuestion, fetchExamples, fetchHealth } from '../api'
import { useAuth } from './AuthContext'

const FALLBACK_EXAMPLES = [
  'What are the top 5 products by total revenue?',
  'How many orders were placed in each city?',
  'Which customers have spent more than $500?',
  'What is the average product rating by category?',
]

const ChatContext = createContext(null)

let turnSeq = 0

export function ChatProvider({ children }) {
  const { user } = useAuth()
  const [draft, setDraft] = useState('')
  const [turns, setTurns] = useState([])
  const [busy, setBusy] = useState(false)
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES)
  const [online, setOnline] = useState(false)

  // Answers belong to whoever is signed in, so reset when the account changes
  useEffect(() => {
    setTurns([])
    setDraft('')
  }, [user?.id])

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
  }, [user?.id])

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

  const clearTurns = useCallback(() => setTurns([]), [])

  const value = useMemo(
    () => ({
      draft,
      setDraft,
      turns,
      busy,
      examples,
      online,
      runQuestion,
      clearTurns,
    }),
    [draft, turns, busy, examples, online, runQuestion, clearTurns],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
