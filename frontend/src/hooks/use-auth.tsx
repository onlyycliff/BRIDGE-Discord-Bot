import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { api } from "@/api/client"
import type { AuthUser } from "@/api/types"

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<string | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  login: async () => null,
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const checkAuth = useCallback(async () => {
    try {
      const data = await api.get<{ authenticated: boolean; user?: AuthUser }>("/api/auth/me")
      if (data.authenticated && data.user) {
        setUser(data.user)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    try {
      const data = await api.post<{ success: boolean; user: AuthUser }>("/api/auth/login", { email, password })
      if (data.success && data.user) {
        setUser(data.user)
        return null
      }
      return "Login failed"
    } catch (err) {
      return err instanceof Error ? err.message : "Login failed"
    }
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    window.location.href = "/logout"
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
