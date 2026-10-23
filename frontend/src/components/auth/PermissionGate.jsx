import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { getPrimaryRole, isSuperAdmin, isOrgAdmin, isBranchManager, isAccountant, isSubscriber, ROLES } from '../../utils/rbac'

/**
 * PermissionGate: Conditionally render UI elements based on authorized roles
 */
export default function PermissionGate({
  children,
  allowedRoles = [],
  fallback = null,
}) {
  const { user } = useAuth()
  if (!user) return fallback

  const primary = getPrimaryRole(user)

  const hasAccess = allowedRoles.some((targetRole) => {
    if (targetRole === ROLES.SUPER_ADMIN && isSuperAdmin(user)) return true
    if (targetRole === ROLES.ORG_ADMIN && isOrgAdmin(user)) return true
    if (targetRole === ROLES.BRANCH_MANAGER && isBranchManager(user)) return true
    if (targetRole === ROLES.ACCOUNTANT && isAccountant(user)) return true
    if (targetRole === ROLES.SUBSCRIBER && isSubscriber(user)) return true
    if (targetRole === primary) return true
    return false
  })

  return hasAccess ? children : fallback
}
