export default function Sidebar({
  examples,
  history,
  online,
  model,
  onExample,
  onSelectHistory,
  onClear,
  open,
  onClose,
}) {
  return (
    <aside className={`sidebar ${open ? 'sidebar--open' : ''}`}>
      <div className="sidebar__brand">
        <div className="brand-mark" aria-hidden="true">
          A
        </div>
        <div>
          <p className="brand-name">Analytics Assistant</p>
          <p className="brand-tag">NL → SQL → answers</p>
        </div>
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Close menu">
          ×
        </button>
      </div>

      <div className="status-pill" data-online={online}>
        <span className="status-pill__dot" />
        {online ? (model ? `Ready · ${model}` : 'Ready') : 'API offline'}
      </div>

      <section className="sidebar__section">
        <h2>Try asking</h2>
        <ul className="chip-list">
          {examples.map((q) => (
            <li key={q}>
              <button type="button" onClick={() => onExample(q)}>
                {q}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="sidebar__section sidebar__section--grow">
        <div className="sidebar__heading-row">
          <h2>Session</h2>
          {history.length > 0 && (
            <button type="button" className="text-btn" onClick={onClear}>
              Clear
            </button>
          )}
        </div>
        {history.length === 0 ? (
          <p className="sidebar__empty">Your questions will appear here.</p>
        ) : (
          <ul className="history-list">
            {history.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => onSelectHistory(item.id)}>
                  {item.question}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="sidebar__foot">E-commerce sample DB · Chroma retrieval</p>
    </aside>
  )
}
