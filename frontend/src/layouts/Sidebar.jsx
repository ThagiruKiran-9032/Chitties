import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  CircleDot,
  Users,
  Gavel,
  Receipt,
  Scale,
  BarChart3,
  Settings,
  ShieldCheck,
  FileText,
  Award,
  Layers,
  ChevronLeft,
  ChevronRight,
  Shield,
  CreditCard,
  History,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getPrimaryRole, ROLES, getRoleDisplayInfo } from '../utils/rbac'

export default function Sidebar({ collapsed, setCollapsed }) {
  const { user } = useAuth()
  const primaryRole = getPrimaryRole(user)
  const roleInfo = getRoleDisplayInfo(user)

  // Build role-specific navigation menu
  const getNavLinks = () => {
    switch (primaryRole) {
      case ROLES.SUPER_ADMIN:
        return [
          { to: '/platform/dashboard', label: 'Platform Overview', icon: LayoutDashboard },
          { to: '/platform/tenants', label: 'Organizations / Tenants', icon: Building2 },
          { to: '/platform/audit-logs', label: 'Platform Audit Logs', icon: ShieldCheck },
          { to: '/settings', label: 'Settings', icon: Settings },
        ]

      case ROLES.ORG_ADMIN:
        return [
          { to: '/organization/dashboard', label: 'Organization Overview', icon: LayoutDashboard },
          { to: '/groups', label: 'Chit Groups', icon: CircleDot },
          { to: '/schemes', label: 'Chit Schemes', icon: Layers },
          { to: '/branches', label: 'Branch Management', icon: Building2 },
          { to: '/members', label: 'Members & KYC', icon: Users },
          { to: '/auctions', label: 'Auctions Overview', icon: Gavel },
          { to: '/payouts', label: 'Payout Approvals', icon: Award },
          { to: '/compliance', label: 'Compliance & Section 20', icon: Scale },
          { to: '/reports', label: 'Financial Reports', icon: BarChart3 },
          { to: '/organization/audit-logs', label: 'Audit Logs', icon: FileText },
          { to: '/settings', label: 'Settings', icon: Settings },
        ]

      case ROLES.BRANCH_MANAGER:
        return [
          { to: '/manager/dashboard', label: 'Branch Overview', icon: LayoutDashboard },
          { to: '/groups', label: 'My Assigned Groups', icon: CircleDot },
          { to: '/members', label: 'Group Members & KYC', icon: Users },
          { to: '/auctions', label: 'Live Auction Chamber', icon: Gavel },
          { to: '/payouts', label: 'Surety Verification', icon: Shield },
          { to: '/reports', label: 'Group Reports', icon: BarChart3 },
          { to: '/settings', label: 'Settings', icon: Settings },
        ]

      case ROLES.ACCOUNTANT:
        return [
          { to: '/accounting/dashboard', label: 'Financial Overview', icon: LayoutDashboard },
          { to: '/groups', label: 'Installment Schedules', icon: CircleDot },
          { to: '/members', label: 'Member Ledgers', icon: Users },
          { to: '/payouts', label: 'Payout Calculations', icon: Award },
          { to: '/reports', label: 'Financial Reports', icon: BarChart3 },
          { to: '/settings', label: 'Settings', icon: Settings },
        ]

      case ROLES.SUBSCRIBER:
      default:
        return [
          { to: '/member/dashboard', label: 'My Dashboard', icon: LayoutDashboard },
          { to: '/groups', label: 'My Chit Circles', icon: CircleDot },
          { to: '/auctions', label: 'Live Auction Room', icon: Gavel },
          { to: '/payouts', label: 'Prize Claim & Sureties', icon: Award },
          { to: '/settings', label: 'My Profile & KYC', icon: Settings },
        ]
    }
  }

  const navLinks = getNavLinks()

  return (
    <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="brand-icon">Ch</div>
          {!collapsed && (
            <div className="brand-text-wrap">
              <span className="brand-title">Chitties</span>
              <span className="brand-subtitle">Enterprise Chit Fund</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="sidebar-collapse-btn"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Role Scope Indicator */}
      {!collapsed && (
        <div style={{ padding: '0.5rem 1rem 0.25rem 1rem' }}>
          <div
            style={{
              padding: '0.4rem 0.65rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
            }}
          >
            <div style={{ fontSize: '0.6875rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--emerald-200)', fontWeight: 700 }}>
              {roleInfo.label}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.8)', marginTop: '2px', fontWeight: 500 }}>
              {roleInfo.scope}
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Role Navigation */}
      <nav className="sidebar-nav">
        {navLinks.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link-item ${isActive ? 'active' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <Icon className="nav-link-icon" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* User Mini Profile in Sidebar Footer */}
      <div className="sidebar-footer">
        {user && (
          <div className="user-mini-card">
            <div className="user-avatar-circle">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            {!collapsed && (
              <div className="user-info">
                <div className="user-name">{user.full_name}</div>
                <div className="user-role-tag">
                  {roleInfo.label}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
