import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)

  // Restore the session on first load if a token is already stored
  useEffect(() => {
    let cancelled = false

    async function restore() {
      if (!api.getToken()) {
        if (!cancelled) setChecking(false)
        return
      }
      try {
        const me = await api.fetchMe()
        if (!cancelled) setUser(me)
      } catch {
        api.setToken('')
      } finally {
        if (!cancelled) setChecking(false)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (email, password) => {
    const { token, user: account } = await api.login(email, password)
    api.setToken(token)
    setUser(account)
  }, [])

  const signUp = useCallback(async (name, email, password) => {
    const { token, user: account } = await api.signup(name, email, password)
    api.setToken(token)
    setUser(account)
  }, [])

  const signOut = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // Token may already be invalid; clear it either way
    }
    api.setToken('')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, checking, signIn, signUp, signOut }),
    [user, checking, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
