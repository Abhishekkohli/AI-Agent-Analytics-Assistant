import { useEffect, useId, useRef } from 'react'
import { useChat } from '../app/ChatContext'
import ChatTurn from '../components/ChatTurn'
import Composer from '../components/Composer'

export default function AskPage() {
  const { draft, setDraft, turns, busy, examples, runQuestion } = useChat()
  const feedRef = useRef(null)
  const titleId = useId()

  useEffect(() => {
    const el = feedRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [turns])

  return (
    <div className="page page--ask">
      <header className="workspace__top workspace__top--inline">
        <div>
          <h1 id={titleId} className="workspace__brand">
            Ask
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
              Ask about products, orders, customers, or reviews. You’ll get a clear
              answer table — no SQL to dig through.
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
    </div>
  )
}
