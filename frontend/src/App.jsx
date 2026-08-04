import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './app/AuthContext'
import { ChatProvider, useChat } from './app/ChatContext'
import Sidebar from './components/Sidebar'
import AskPage from './pages/AskPage'
import AuthPage from './pages/AuthPage'
import HistoryPage from './pages/HistoryPage'
import ExplorePage from './pages/ExplorePage'
import AboutPage from './pages/AboutPage'

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
          <Route path="/" element={<AskPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function Gate() {
  const { user, checking } = useAuth()

  if (checking) {
    return (
      <div className="auth-screen">
        <div className="atmosphere" aria-hidden="true" />
        <p className="empty-note">Loading…</p>
      </div>
    )
  }

  if (!user) return <AuthPage />

  return (
    <ChatProvider>
      <Shell />
    </ChatProvider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
