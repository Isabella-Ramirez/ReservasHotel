import { createContext } from 'react'

import type {
  AuthCredentials,
  GuestProfile,
  RegisterPayload,
  RoleCode,
  User,
} from '@/features/auth/types'

export interface AuthResponse {
  access_token: string
  expires_at: number
  user: User
}

export interface AuthContextValue {
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

export const GUEST_ROLE: RoleCode = 'GUEST'
