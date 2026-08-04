import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useSearchParams } from 'react-router-dom'
import { ChatProvider, useChat } from './app/ChatContext'
import Sidebar from './components/Sidebar'
import AskPage from './pages/AskPage'
import HistoryPage from './pages/HistoryPage'
import ExplorePage from './pages/ExplorePage'
import AboutPage from './pages/AboutPage'

function AskWithFocus() {
  const [params, setParams] = useSearchParams()
  const focus = params.get('focus')

  useEffect(() => {
    if (!focus) return
    const node = document.getElementById(`turn-${focus}`)
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setParams({}, { replace: true })
    }
  }, [focus, setParams])

  return <AskPage />
}

function Shell() {
  const { online } = useChat()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-shell">
      <div className="atmosphere" aria-hidden="true" />

      <Sidebar
        online={online}
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

      <main className="workspace">
        <button
          type="button"
          className="menu-btn menu-btn--float"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
        >
          ☰
        </button>

        <Routes>
          <Route path="/" element={<AskWithFocus />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ChatProvider>
      <Shell />
    </ChatProvider>
  )
}
