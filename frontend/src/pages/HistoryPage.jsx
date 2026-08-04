import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { clearHistory, fetchHistory } from '../api'
import { useAuth } from '../app/AuthContext'
import { useChat } from '../app/ChatContext'

function resultLabel(item) {
  if (!item.succeeded) return 'No answer'
  return item.row_count === 1 ? '1 result' : `${item.row_count} results`
}

function formatWhen(iso) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function HistoryPage() {
  const { user } = useAuth()
  const { runQuestion, busy } = useChat()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setItems(await fetchHistory())
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load your history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load, user?.id])

  async function handleClear() {
    await clearHistory()
    setItems([])
  }

  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">History</h1>
          <p className="workspace__sub">Questions you’ve already asked</p>
        </div>
        {items.length > 0 && (
          <button type="button" className="secondary-btn" onClick={handleClear}>
            Clear all
          </button>
        )}
      </header>

      {loading && <p className="empty-note">Loading…</p>}

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="empty-panel">
          <p>No questions yet.</p>
          <button type="button" className="send-btn" onClick={() => navigate('/')}>
            Ask something
          </button>
        </div>
      )}

      {items.length > 0 && (
        <ul className="history-panel">
          {items.map((item) => (
            <li key={item.id} className="history-panel__item">
              <div>
                <p className="history-panel__q">{item.question}</p>
                <p className="history-panel__meta">
                  {formatWhen(item.created_at)} · {resultLabel(item)}
                </p>
              </div>
              <div className="history-panel__actions">
                <button
                  type="button"
                  className="ghost-btn ghost-btn--ink"
                  disabled={busy}
                  onClick={async () => {
                    navigate('/')
                    await runQuestion(item.question)
                  }}
                >
                  Ask again
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
