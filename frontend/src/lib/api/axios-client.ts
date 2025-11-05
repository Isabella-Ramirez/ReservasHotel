import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL
if (!API_BASE_URL) {
  console.warn(
    'VITE_API_URL is not defined. axiosClient will fallback to relative URLs, which may break API calls.',
  )
}
const TOKEN_STORAGE_KEY = 'hotel.token'
const UNAUTHORIZED_EVENT = 'auth:unauthorized'

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
})

axiosClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  } else {
    config.headers.delete('Authorization')
  }

  return config
})

axiosClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }
    return Promise.reject(error)
  },
)

export function setAuthToken(token: string | null) {
  if (typeof window === 'undefined') return

  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

export function getStoredToken() {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function onUnauthorized(callback: () => void) {
  if (typeof window === 'undefined') {
    return () => {}
  }

  window.addEventListener(UNAUTHORIZED_EVENT, callback)
  return () => window.removeEventListener(UNAUTHORIZED_EVENT, callback)
}

export { axiosClient }
