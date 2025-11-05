import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import type {
  AuthCredentials,
  GuestProfile,
  RegisterPayload,
  RoleCode,
  User,
} from '@/features/auth/types'
import {
  axiosClient,
  getStoredToken,
  onUnauthorized,
  setAuthToken,
} from '@/lib/api/axios-client'

interface AuthContextValue {
  token: string | null
  user: User | null
  guestProfile: GuestProfile | null
  loading: boolean
  login: (credentials: AuthCredentials) => Promise<AuthResponse>
  register: (payload: RegisterPayload) => Promise<AuthResponse>
  logout: () => void
  hasRole: (roles: RoleCode | RoleCode[]) => boolean
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

interface AuthResponse {
  access_token: string
  expires_at: number
  user: User
}

const GUEST_ROLE: RoleCode = 'GUEST'

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [user, setUser] = useState<User | null>(null)
  const [guestProfile, setGuestProfile] = useState<GuestProfile | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    setAuthToken(null)
    setToken(null)
    setUser(null)
    setGuestProfile(null)
  }, [])

  const fetchGuestProfile = useCallback(async () => {
    try {
      const response = await axiosClient.get<GuestProfile>('/guests/me')
      setGuestProfile(response.data)
    } catch {
      setGuestProfile(null)
    }
  }, [])

  const persistSession = useCallback(
    async (response: AuthResponse) => {
      const authToken = response.access_token
      setUser(response.user)
      setAuthToken(authToken)
      setToken(authToken)
      if (response.user.role_code === GUEST_ROLE) {
        await fetchGuestProfile()
      } else {
        setGuestProfile(null)
      }
      setLoading(false)
    },
    [fetchGuestProfile],
  )

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const { data } = await axiosClient.post<AuthResponse>('/auth/login', credentials)
      await persistSession(data)
      return data
    },
    [persistSession],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const { data } = await axiosClient.post<AuthResponse>('/auth/register', payload)
      await persistSession(data)
      return data
    },
    [persistSession],
  )

  useEffect(() => {
    return onUnauthorized(() => {
      logout()
    })
  }, [logout])

  const hasRole = useCallback(
    (roles: RoleCode | RoleCode[]) => {
      if (!user) return false
      const roleList = Array.isArray(roles) ? roles : [roles]
      return roleList.includes(user.role_code)
    },
    [user],
  )

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = getStoredToken()
      
      if (!storedToken) {
        setLoading(false)
        return
      }

      try {
        setAuthToken(storedToken)
        const response = await axiosClient.get<User>('/auth/me')
        setUser(response.data)
        
        if (response.data.role_code === GUEST_ROLE) {
          await fetchGuestProfile()
        }
      } catch {
        logout()
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [fetchGuestProfile, logout])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      guestProfile,
      loading,
      login,
      register,
      logout,
      hasRole,
    }),
    [guestProfile, hasRole, loading, login, logout, register, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
