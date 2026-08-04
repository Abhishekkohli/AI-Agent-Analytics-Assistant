import ResultsTable from './ResultsTable'

export default function ChatTurn({ turn }) {
  const { question, status, result, error } = turn

  return (
    <article className="turn">
      <div className="turn__question">
        <span className="turn__who">You</span>
        <p>{question}</p>
      </div>

      <div className="turn__answer">
        <span className="turn__who turn__who--agent">Assistant</span>

        {status === 'loading' && (
          <div className="thinking" aria-live="polite">
            <span className="thinking__dot" />
            <span className="thinking__dot" />
            <span className="thinking__dot" />
            <span className="thinking__label">Looking up your answer…</span>
          </div>
        )}

        {status === 'error' && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        {status === 'done' && result && (
          <div className="turn__body">
            {result.error ? (
              <div className="error-banner" role="alert">
                {result.blocked
                  ? result.error
                  : 'Couldn’t answer that question. Try rephrasing it.'}
              </div>
            ) : (
              <ResultsTable
                columns={result.columns}
                rows={result.rows}
                rowCount={result.row_count}
              />
            )}
          </div>
        )}
      </div>
    </article>
  )
}
