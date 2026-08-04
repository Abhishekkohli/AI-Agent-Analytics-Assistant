import { NavLink } from 'react-router-dom'
import { useAuth } from '../app/AuthContext'

const NAV = [
  { to: '/', label: 'Ask', end: true },
  { to: '/history', label: 'History' },
  { to: '/explore', label: 'Explore' },
  { to: '/about', label: 'About' },
]

function initials(name) {
  return (name || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}

export default function Sidebar({ online, open, onClose }) {
  const { user, signOut } = useAuth()

  return (
    <aside className={`sidebar ${open ? 'sidebar--open' : ''}`}>
      <div className="sidebar__brand">
        <div className="brand-mark" aria-hidden="true">
          A
        </div>
        <div>
          <p className="brand-name">Analytics Assistant</p>
          <p className="brand-tag">Answers about your store</p>
        </div>
        <button type="button" className="sidebar__close" onClick={onClose} aria-label="Close menu">
          ×
        </button>
      </div>

      <div className="status-pill" data-online={online}>
        <span className="status-pill__dot" />
        {online ? 'Ready' : 'Unavailable'}
      </div>

      <nav className="sidebar__nav" aria-label="Primary">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `sidebar__nav-link${isActive ? ' sidebar__nav-link--active' : ''}`
            }
            onClick={onClose}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__account">
        <div className="sidebar__avatar" aria-hidden="true">
          {initials(user?.name)}
        </div>
        <div className="sidebar__account-info">
          <p className="sidebar__account-name">{user?.name}</p>
          <p className="sidebar__account-email">{user?.email}</p>
        </div>
        <button type="button" className="text-btn" onClick={signOut}>
          Sign out
        </button>
      </div>
    </aside>
  )
}
