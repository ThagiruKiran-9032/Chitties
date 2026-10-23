import React from 'react'
import { Navigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { getPrimaryRole, isSuperAdmin, isOrgAdmin, isBranchManager, isAccountant, isSubscriber, ROLES } from '../../utils/rbac'
import AccessDenied from '../common/AccessDenied'

export default function ProtectedRoute({ children, allowedRoles = null }) {
  const { user, isAuthenticated, loading } = useAuth()
  const token = typeof window !== 'undefined' ? localStorage.getItem('chitties_token') : null

  if (loading || (token && !user)) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.875rem',
          backgroundColor: 'var(--bg-app)',
        }}
      >
        <RefreshCw className="w-8 h-8 animate-spin" style={{ color: 'var(--emerald-600)' }} />
        <p
          style={{
            fontSize: '0.8125rem',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          Verifying Authorized Chitties Session...
        </p>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  // If specific roles are required, verify against user's actual resolved role & scope
  if (allowedRoles && allowedRoles.length > 0) {
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

    if (!hasAccess) {
      return (
        <AccessDenied
          requiredRole={allowedRoles.join(' or ')}
          message={`Your role (${user.role}${user.organization_id ? '' : ' - Platform Scope'}) is not authorized to access this section.`}
        />
      )
    }
  }

  return children
}
