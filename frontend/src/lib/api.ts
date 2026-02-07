// In production (Docker), use empty string so requests go to same origin (nginx handles routing)
// In development, use localhost:8000 directly
const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

const TOKEN_KEY = 'homework_copilot_token'
const REFRESH_KEY = 'homework_copilot_refresh'

interface ApiOptions extends RequestInit {
  token?: string | null
}

class ApiError extends Error {
  status: number
  data: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

// Prevent concurrent refresh attempts
let refreshPromise: Promise<string | null> | null = null

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY)
  if (!refreshToken) return null

  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) return null

    const tokens = await response.json()
    localStorage.setItem(TOKEN_KEY, tokens.access_token)
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
    // Notify AuthContext that token was refreshed
    window.dispatchEvent(new CustomEvent('token-refreshed', { detail: tokens.access_token }))
    return tokens.access_token as string
  } catch {
    return null
  }
}

async function refreshAccessToken(): Promise<string | null> {
  // If a refresh is already in-flight, reuse that promise
  if (refreshPromise) return refreshPromise
  refreshPromise = tryRefreshToken().finally(() => { refreshPromise = null })
  return refreshPromise
}

async function request<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  // On 401, try refreshing the token and retry once
  if (response.status === 401 && token) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`
      const retryResponse = await fetch(`${API_URL}${endpoint}`, {
        ...fetchOptions,
        headers,
      })

      if (!retryResponse.ok) {
        const data = await retryResponse.json().catch(() => ({}))
        throw new ApiError(data.detail || 'An error occurred', retryResponse.status, data)
      }

      if (retryResponse.status === 204) return undefined as T
      return retryResponse.json()
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(
      data.detail || 'An error occurred',
      response.status,
      data
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string, options?: ApiOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(endpoint: string, data?: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string, options?: ApiOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),

  upload: async <T>(
    endpoint: string,
    formData: FormData,
    options?: ApiOptions
  ): Promise<T> => {
    const { token } = options || {}

    const headers: HeadersInit = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    })

    // On 401, try refreshing the token and retry once
    if (response.status === 401 && token) {
      const newToken = await refreshAccessToken()
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`
        const retryResponse = await fetch(`${API_URL}${endpoint}`, {
          method: 'POST',
          headers,
          body: formData,
        })

        if (!retryResponse.ok) {
          const data = await retryResponse.json().catch(() => ({}))
          throw new ApiError(data.detail || 'Upload failed', retryResponse.status, data)
        }

        return retryResponse.json()
      }
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new ApiError(
        data.detail || 'Upload failed',
        response.status,
        data
      )
    }

    return response.json()
  },
}

export { ApiError }
