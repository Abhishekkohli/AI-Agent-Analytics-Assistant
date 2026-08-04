import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { askQuestion, fetchExamples, fetchHealth } from './api'
import Sidebar from './components/Sidebar'
import ChatTurn from './components/ChatTurn'
import Composer from './components/Composer'

const FALLBACK_EXAMPLES = [
  'What are the top 5 products by total revenue?',
  'How many orders were placed in each city?',
  'Which customers have spent more than $500?',
  'What is the average product rating by category?',
]

let turnSeq = 0

export default function App() {
  const [draft, setDraft] = useState('')
  const [turns, setTurns] = useState([])
  const [busy, setBusy] = useState(false)
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES)
  const [online, setOnline] = useState(false)
  const [model, setModel] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const feedRef = useRef(null)
  const titleId = useId()

  useEffect(() => {
    let cancelled = false

    async function boot() {
      try {
        const [health, ex] = await Promise.all([
          fetchHealth(),
          fetchExamples().catch(() => ({ examples: FALLBACK_EXAMPLES })),
        ])
        if (cancelled) return
        setOnline(true)
        setModel(health.model || '')
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

  useEffect(() => {
    const el = feedRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [turns])

  const runQuestion = useCallback(async (question) => {
    const q = question.trim()
    if (!q || busy) return

    const id = `t-${++turnSeq}`
    setBusy(true)
    setDraft('')
    setMenuOpen(false)
    setTurns((prev) => [...prev, { id, question: q, status: 'loading' }])

    try {
      const result = await askQuestion(q)
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, status: 'done', result } : t)),
      )
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, status: 'error', error: err.message || 'Something went wrong' }
            : t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }, [busy])

  function scrollToTurn(id) {
    const node = document.getElementById(`turn-${id}`)
    node?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setMenuOpen(false)
  }

  return (
    <div className="app-shell">
      <div className="atmosphere" aria-hidden="true" />

      <Sidebar
        examples={examples}
        history={turns.map(({ id, question }) => ({ id, question }))}
        online={online}
        model={model}
        onExample={(q) => runQuestion(q)}
        onSelectHistory={scrollToTurn}
        onClear={() => setTurns([])}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />

      {menuOpen && (
        <button
          type="button"
          className="scrim"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <main className="workspace" aria-labelledby={titleId}>
        <header className="workspace__top">
          <button
            type="button"
            className="menu-btn"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
          >
            ☰
          </button>
          <div>
            <h1 id={titleId} className="workspace__brand">
              Analytics Assistant
            </h1>
            <p className="workspace__sub">Ask the business database in plain English</p>
          </div>
        </header>

        <div className="feed" ref={feedRef}>
          {turns.length === 0 ? (
            <section className="hero-empty">
              <p className="hero-empty__eyebrow">E-commerce analytics</p>
              <h2 className="hero-empty__title">Analytics Assistant</h2>
              <p className="hero-empty__copy">
                Type a question about products, orders, customers, or reviews.
                The agent retrieves schema context, writes SQL, and returns a table.
              </p>
              <div className="hero-empty__prompts">
                {examples.slice(0, 3).map((q) => (
                  <button key={q} type="button" onClick={() => runQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </section>
          ) : (
            turns.map((turn) => (
              <div key={turn.id} id={`turn-${turn.id}`}>
                <ChatTurn turn={turn} />
              </div>
            ))
          )}
        </div>

        <Composer
          value={draft}
          onChange={setDraft}
          onSubmit={() => runQuestion(draft)}
          disabled={busy}
        />
      </main>
    </div>
  )
}
