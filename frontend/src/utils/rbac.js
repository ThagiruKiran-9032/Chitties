/**
 * Role-Based Access Control (RBAC) & Scope Utilities for Chitties
 * Implements canonical normalization and explicit scope detection (Super Admin vs Org Admin).
 */

export const ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  ORG_ADMIN: 'ORG_ADMIN',
  BRANCH_MANAGER: 'BRANCH_MANAGER',
  ACCOUNTANT: 'ACCOUNTANT',
  SUBSCRIBER: 'SUBSCRIBER',
  // Canonical backend aliases
  ADMIN: 'ADMIN',
  MANAGER: 'MANAGER',
  MEMBER: 'MEMBER',
  COLLECTION_AGENT: 'COLLECTION_AGENT',
}

/**
 * Returns canonical role string (ADMIN, MANAGER, ACCOUNTANT, MEMBER)
 */
export function getCanonicalRole(role) {
  if (!role) return ''
  const r = String(role).toUpperCase()
  if (r === 'SUPER_ADMIN' || r === 'ORG_ADMIN' || r === 'ADMIN') return 'ADMIN'
  if (r === 'BRANCH_MANAGER' || r === 'MANAGER') return 'MANAGER'
  if (r === 'ACCOUNTANT' || r === 'COLLECTION_AGENT') return 'ACCOUNTANT'
  if (r === 'SUBSCRIBER' || r === 'MEMBER') return 'MEMBER'
  return r
}

/**
 * Global Super Admin: explicit scope check.
 * organization_id must be null/empty, or explicit role SUPER_ADMIN
 */
export function isSuperAdmin(user) {
  if (!user) return false
  if (user.role === 'SUPER_ADMIN') return true
  return getCanonicalRole(user.role) === 'ADMIN' && !user.organization_id
}

/**
 * Organization Admin: must be an ADMIN bound to a specific organization.
 */
export function isOrgAdmin(user) {
  if (!user) return false
  if (user.role === 'ORG_ADMIN') return true
  return getCanonicalRole(user.role) === 'ADMIN' && Boolean(user.organization_id)
}

/**
 * Branch Manager: operational circle manager
 */
export function isBranchManager(user) {
  if (!user) return false
  return user.role === 'BRANCH_MANAGER' || getCanonicalRole(user.role) === 'MANAGER'
}

/**
 * Accountant / Financial Controller
 */
export function isAccountant(user) {
  if (!user) return false
  return user.role === 'ACCOUNTANT' || user.role === 'COLLECTION_AGENT'
}

/**
 * Chit Subscriber / Member
 */
export function isSubscriber(user) {
  if (!user) return false
  return user.role === 'SUBSCRIBER' || getCanonicalRole(user.role) === 'MEMBER'
}

/**
 * Resolves the primary business role key for UI rendering & routing
 */
export function getPrimaryRole(user) {
  if (!user) return null
  if (isSuperAdmin(user)) return ROLES.SUPER_ADMIN
  if (isOrgAdmin(user)) return ROLES.ORG_ADMIN
  if (isBranchManager(user)) return ROLES.BRANCH_MANAGER
  if (isAccountant(user)) return ROLES.ACCOUNTANT
  return ROLES.SUBSCRIBER
}

/**
 * Returns the correct home dashboard path according to the user's role
 */
export function getRoleHomeRoute(user) {
  if (!user) return '/login'
  const primaryRole = getPrimaryRole(user)
  switch (primaryRole) {
    case ROLES.SUPER_ADMIN:
      return '/platform/dashboard'
    case ROLES.ORG_ADMIN:
      return '/organization/dashboard'
    case ROLES.BRANCH_MANAGER:
      return '/manager/dashboard'
    case ROLES.ACCOUNTANT:
      return '/accounting/dashboard'
    case ROLES.SUBSCRIBER:
    default:
      return '/member/dashboard'
  }
}

/**
 * User-facing formatted title & badge
 */
export function getRoleDisplayInfo(user) {
  const role = getPrimaryRole(user)
  switch (role) {
    case ROLES.SUPER_ADMIN:
      return { label: 'Global Super Admin', badgeClass: 'badge-purple', scope: 'Multi-Tenant Platform' }
    case ROLES.ORG_ADMIN:
      return { label: 'Organization Admin', badgeClass: 'badge-emerald', scope: 'Company Foreman' }
    case ROLES.BRANCH_MANAGER:
      return { label: 'Branch Manager', badgeClass: 'badge-blue', scope: 'Circle Operations' }
    case ROLES.ACCOUNTANT:
      return { label: 'Accountant', badgeClass: 'badge-gold', scope: 'Financial Ledger' }
    case ROLES.SUBSCRIBER:
    default:
      return { label: 'Chit Subscriber', badgeClass: 'badge-slate', scope: 'Personal Account' }
  }
}
