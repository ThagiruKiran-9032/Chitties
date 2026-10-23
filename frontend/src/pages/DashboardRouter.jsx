import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getRoleHomeRoute } from '../utils/rbac'
import LoadingState from '../components/common/LoadingState'

export default function DashboardRouter() {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingState message="Routing to authorized dashboard..." height="60vh" />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  const targetRoute = getRoleHomeRoute(user)
  return <Navigate to={targetRoute} replace />
}
