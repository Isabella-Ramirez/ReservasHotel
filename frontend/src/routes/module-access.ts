import type { RoleCode } from '@/features/auth/types'

export type ModuleKey =
  | 'dashboard'
  | 'myReservations'
  | 'newReservation'
  | 'myPayments'
  | 'profile'
  | 'reservations'
  | 'payments'
  | 'guests'
  | 'rooms'
  | 'users'
  | 'roles'

export const moduleAccess: Record<RoleCode, ModuleKey[]> = {
  GUEST: ['dashboard', 'myReservations', 'newReservation', 'myPayments', 'profile'],
  RECEPTIONIST: ['dashboard', 'reservations', 'payments', 'guests'],
  ADMIN: ['dashboard', 'reservations', 'payments', 'guests', 'rooms', 'users', 'roles'],
}
