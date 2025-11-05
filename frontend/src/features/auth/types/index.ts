export type RoleCode = 'GUEST' | 'RECEPTIONIST' | 'ADMIN'

export interface User {
  id: string
  email: string
  full_name: string
  role_id: string
  role_code: RoleCode
}

export interface GuestProfile {
  id: string
  user_id: string
  phone?: string
  address?: string
  preferences?: Record<string, unknown>
}

export interface AuthCredentials {
  email: string
  password: string
}

export interface RegisterPayload extends AuthCredentials {
  full_name: string
}
