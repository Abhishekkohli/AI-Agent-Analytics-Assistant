import { useState } from 'react'

export default function SqlBlock({ sql }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(sql)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1400)
    } catch {
      // Clipboard can fail in non-secure contexts; ignore quietly
    }
  }

  return (
    <div className="sql-block">
      <div className="sql-block__bar">
        <span className="sql-block__label">Generated SQL</span>
        <button type="button" className="ghost-btn" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="sql-block__code">
        <code>{sql}</code>
      </pre>
    </div>
  )
}
