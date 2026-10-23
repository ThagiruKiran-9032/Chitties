import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'

import { AuthProvider, useAuth } from './context/AuthContext'
import { ROLES } from './utils/rbac'
import AuthPage from './pages/AuthPage'
import AppLayout from './layouts/AppLayout'
import ProtectedRoute from './components/auth/ProtectedRoute'

// Role-Specific Dashboards
import DashboardRouter from './pages/DashboardRouter'
import SuperAdminDashboard from './pages/dashboards/SuperAdminDashboard'
import OrgAdminDashboard from './pages/dashboards/OrgAdminDashboard'
import ManagerDashboard from './pages/dashboards/ManagerDashboard'
import AccountantDashboard from './pages/dashboards/AccountantDashboard'
import SubscriberDashboard from './pages/dashboards/SubscriberDashboard'
import TenantsPage from './pages/dashboards/TenantsPage'
import AuditLogsPage from './pages/dashboards/AuditLogsPage'

// Core Functional Pages
import ChitGroupsPage from './pages/ChitGroupsPage'
import GroupDetailPage from './pages/GroupDetailPage'
import ChitSchemesPage from './pages/ChitSchemesPage'
import BranchesPage from './pages/BranchesPage'
import MembersPage from './pages/MembersPage'
import AuctionsPage from './pages/AuctionsPage'
import LiveAuctionRoom from './pages/LiveAuctionRoom'
import PayoutsPage from './pages/PayoutsPage'
import ReportsPage from './pages/ReportsPage'
import CompliancePage from './pages/CompliancePage'
import SettingsPage from './pages/SettingsPage'

function PublicAuthRoute() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
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
          Verifying Session...
        </p>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <AuthPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Route */}
          <Route path="/login" element={<PublicAuthRoute />} />

          {/* Authenticated Application Shell */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            {/* Dynamic Dashboard Landing Redirector */}
            <Route path="/" element={<DashboardRouter />} />
            <Route path="/dashboard" element={<DashboardRouter />} />

            {/* 1. Global Super Admin Routes */}
            <Route
              path="/platform/dashboard"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN]}>
                  <SuperAdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/platform/tenants"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN]}>
                  <TenantsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/platform/audit-logs"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN]}>
                  <AuditLogsPage title="Platform Global Audit Logs" />
                </ProtectedRoute>
              }
            />

            {/* 2. Organization Admin Routes */}
            <Route
              path="/organization/dashboard"
              element={
                <ProtectedRoute allowedRoles={[ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <OrgAdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organization/audit-logs"
              element={
                <ProtectedRoute allowedRoles={[ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <AuditLogsPage title="Organization Audit Logs" />
                </ProtectedRoute>
              }
            />

            {/* 3. Branch Manager Routes */}
            <Route
              path="/manager/dashboard"
              element={
                <ProtectedRoute allowedRoles={[ROLES.BRANCH_MANAGER, ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <ManagerDashboard />
                </ProtectedRoute>
              }
            />

            {/* 4. Accountant Routes */}
            <Route
              path="/accounting/dashboard"
              element={
                <ProtectedRoute allowedRoles={[ROLES.ACCOUNTANT, ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <AccountantDashboard />
                </ProtectedRoute>
              }
            />

            {/* 5. Subscriber (Member) Routes */}
            <Route
              path="/member/dashboard"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUBSCRIBER, ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <SubscriberDashboard />
                </ProtectedRoute>
              }
            />

            {/* Domain Functional Pages (Role Guarded) */}
            <Route path="/groups" element={<ChitGroupsPage />} />
            <Route path="/groups/:id" element={<GroupDetailPage />} />

            <Route
              path="/schemes"
              element={
                <ProtectedRoute allowedRoles={[ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <ChitSchemesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/branches"
              element={
                <ProtectedRoute allowedRoles={[ROLES.ORG_ADMIN, ROLES.SUPER_ADMIN]}>
                  <BranchesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/members"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.BRANCH_MANAGER, ROLES.ACCOUNTANT]}>
                  <MembersPage />
                </ProtectedRoute>
              }
            />

            <Route path="/auctions" element={<AuctionsPage />} />
            <Route path="/auctions/:id" element={<LiveAuctionRoom />} />

            <Route path="/payouts" element={<PayoutsPage />} />

            <Route
              path="/compliance"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN]}>
                  <CompliancePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.BRANCH_MANAGER, ROLES.ACCOUNTANT]}>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />

            <Route path="/settings" element={<SettingsPage />} />

            {/* Catch-all fallback */}
            <Route path="*" element={<DashboardRouter />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
