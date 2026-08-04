import { useEffect, useState } from 'react'
import { fetchSchema } from '../api'

export default function ExplorePage() {
  const [tables, setTables] = useState([])
  const [active, setActive] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchSchema()
        if (cancelled) return
        setTables(data.tables || [])
        setActive(data.tables?.[0]?.name || null)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load schema')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const selected = tables.find((t) => t.name === active)

  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">Explore</h1>
          <p className="workspace__sub">Browse the sample e-commerce schema</p>
        </div>
      </header>

      {loading && <p className="empty-note">Loading schema…</p>}
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="explore">
          <aside className="explore__list">
            <h2>Tables</h2>
            <ul>
              {tables.map((t) => (
                <li key={t.name}>
                  <button
                    type="button"
                    className={t.name === active ? 'is-active' : ''}
                    onClick={() => setActive(t.name)}
                  >
                    <span>{t.name}</span>
                    <span className="explore__count">{t.row_count.toLocaleString()}</span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <section className="explore__detail">
            {selected ? (
              <>
                <div className="explore__detail-head">
                  <h2>{selected.name}</h2>
                  <p>{selected.row_count.toLocaleString()} rows</p>
                </div>
                <div className="results__scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Column</th>
                        <th>Type</th>
                        <th>Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.columns.map((col) => (
                        <tr key={col.name}>
                          <td>{col.name}</td>
                          <td>{col.type}</td>
                          <td>
                            {[col.pk ? 'PK' : null, col.notnull ? 'NOT NULL' : null]
                              .filter(Boolean)
                              .join(', ') || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="empty-note">Select a table</p>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
