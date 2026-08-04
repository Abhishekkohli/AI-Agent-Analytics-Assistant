import { useEffect, useRef } from 'react'

export default function Composer({ value, onChange, onSubmit, disabled }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!disabled) ref.current?.focus()
  }, [disabled])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) onSubmit()
    }
  }

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault()
        if (!disabled && value.trim()) onSubmit()
      }}
    >
      <textarea
        ref={ref}
        rows={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your store…"
        aria-label="Your question"
      />
      <button type="submit" className="send-btn" disabled={disabled || !value.trim()}>
        Ask
      </button>
    </form>
  )
}
