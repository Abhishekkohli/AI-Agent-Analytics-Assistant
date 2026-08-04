function formatCell(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? String(value)
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(value)
}

export default function ResultsTable({ columns, rows, rowCount }) {
  if (!columns?.length) {
    return <p className="empty-note">No columns returned.</p>
  }

  if (!rows?.length) {
    return <p className="empty-note">Query ran successfully — no matching rows.</p>
  }

  const shown = rows.length
  const truncated = rowCount > shown

  return (
    <div className="results">
      <div className="results__meta">
        <span>
          {rowCount.toLocaleString()} row{rowCount === 1 ? '' : 's'}
          {truncated ? ` · showing first ${shown}` : ''}
        </span>
      </div>
      <div className="results__scroll">
        <table>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{formatCell(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
