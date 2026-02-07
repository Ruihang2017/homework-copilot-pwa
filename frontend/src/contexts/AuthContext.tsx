import React, { createContext, useContext, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '@/lib/api'
import type { User, AuthTokens, LoginCredentials, RegisterCredentials } from '@/types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => void
  updateUser: (data: Partial<User>) => void
  token: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'homework_copilot_token'
const REFRESH_KEY = 'homework_copilot_refresh'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()

  // Handle OAuth callback tokens from URL
  useEffect(() => {
    const accessToken = searchParams.get('access_token')
    const refreshToken = searchParams.get('refresh_token')

    if (accessToken && refreshToken) {
      localStorage.setItem(TOKEN_KEY, accessToken)
      localStorage.setItem(REFRESH_KEY, refreshToken)
      setToken(accessToken)
      
      // Clear URL params
      searchParams.delete('access_token')
      searchParams.delete('refresh_token')
      setSearchParams(searchParams, { replace: true })
      
      fetchUser(accessToken)
      return
    }

    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (storedToken) {
      setToken(storedToken)
      fetchUser(storedToken)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async (accessToken: string) => {
    try {
      const userData = await api.get<User>('/auth/me', { token: accessToken })
      setUser(userData)
      setToken(accessToken)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        // Try to refresh token
        const refreshToken = localStorage.getItem(REFRESH_KEY)
        if (refreshToken) {
          try {
            const tokens = await api.post<AuthTokens>('/auth/refresh', {
              refresh_token: refreshToken,
            })
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
            setToken(tokens.access_token)
            const userData = await api.get<User>('/auth/me', {
              token: tokens.access_token,
            })
            setUser(userData)
          } catch {
            logout()
          }
        } else {
          logout()
        }
      } else {
        logout()
      }
    } finally {
      setLoading(false)
    }
  }

  const login = async (credentials: LoginCredentials) => {
    const tokens = await api.post<AuthTokens>('/auth/login', credentials)
    localStorage.setItem(TOKEN_KEY, tokens.access_token)
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
    setToken(tokens.access_token)
    const userData = await api.get<User>('/auth/me', {
      token: tokens.access_token,
    })
    setUser(userData)
  }

  const register = async (credentials: RegisterCredentials) => {
    const tokens = await api.post<AuthTokens>('/auth/register', credentials)
    localStorage.setItem(TOKEN_KEY, tokens.access_token)
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
    setToken(tokens.access_token)
    const userData = await api.get<User>('/auth/me', {
      token: tokens.access_token,
    })
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    setToken(null)
    setUser(null)
  }

  const updateUser = (data: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...data } : null))
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser, token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
