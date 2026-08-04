import { useNavigate } from 'react-router-dom'
import { useChat } from '../app/ChatContext'

function statusLabel(turn) {
  if (turn.status === 'loading') return 'Running'
  if (turn.status === 'error') return 'Failed'
  if (turn.result?.error) return 'Failed'
  const n = turn.result?.row_count ?? 0
  return n === 1 ? '1 result' : `${n} results`
}

export default function HistoryPage() {
  const { turns, clearHistory, runQuestion, busy } = useChat()
  const navigate = useNavigate()

  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">History</h1>
          <p className="workspace__sub">Questions you’ve already asked</p>
        </div>
        {turns.length > 0 && (
          <button type="button" className="secondary-btn" onClick={clearHistory}>
            Clear all
          </button>
        )}
      </header>

      {turns.length === 0 ? (
        <div className="empty-panel">
          <p>No questions yet.</p>
          <button type="button" className="send-btn" onClick={() => navigate('/')}>
            Ask something
          </button>
        </div>
      ) : (
        <ul className="history-panel">
          {[...turns].reverse().map((turn, index) => (
            <li key={turn.id} className="history-panel__item">
              <div>
                <p className="history-panel__q">{turn.question}</p>
                <p className="history-panel__meta">
                  #{turns.length - index} · {statusLabel(turn)}
                </p>
              </div>
              <div className="history-panel__actions">
                <button
                  type="button"
                  className="ghost-btn ghost-btn--ink"
                  onClick={() => navigate(`/?focus=${turn.id}`)}
                >
                  View
                </button>
                <button
                  type="button"
                  className="ghost-btn ghost-btn--ink"
                  disabled={busy}
                  onClick={async () => {
                    await runQuestion(turn.question)
                    navigate('/')
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
