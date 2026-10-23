import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  User,
  LogOut,
  Building2,
  CheckCircle2,
  AlertCircle,
  Shield,
  X,
} from 'lucide-react'
import { useAuth, DEMO_ACCOUNTS } from '../context/AuthContext'
import { getRoleHomeRoute, getRoleDisplayInfo } from '../utils/rbac'

export default function TopNavbar() {
  const { user, logout, quickDemoLogin } = useAuth()
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const roleInfo = getRoleDisplayInfo(user)

  // Sample regulatory & operational notifications
  const sampleNotifications = [
    {
      id: 1,
      title: 'Auction Round Concluded',
      message: 'APEX-GOLD-2026 Month 1 auction completed. Prized ticket: #1.',
      time: '10 mins ago',
      type: 'success',
      unread: true,
    },
    {
      id: 2,
      title: 'Section 20 Lien Verified',
      message: 'Registrar order confirmed ₹1,00,000 FDR pledge for APEX-GOLD-2026.',
      time: '1 hour ago',
      type: 'info',
      unread: true,
    },
    {
      id: 3,
      title: 'Sureties Review Pending',
      message: 'Collateral submissions awaiting verification.',
      time: '3 hours ago',
      type: 'warning',
      unread: false,
    },
  ]

  const getPageTitle = () => {
    const path = location.pathname
    if (path.includes('/platform/dashboard')) return 'Platform Super Admin Overview'
    if (path.includes('/platform/tenants')) return 'Tenant Organizations & Provisioning'
    if (path.includes('/platform/audit-logs')) return 'Global Platform Audit Logs'
    if (path.includes('/organization/dashboard')) return 'Executive Foreman Command Center'
    if (path.includes('/manager/dashboard')) return 'Branch Operations & Circle Overview'
    if (path.includes('/accounting/dashboard')) return 'Financial Ledger & Payout Center'
    if (path.includes('/member/dashboard')) return 'Subscriber Portal & Circle Overview'
    if (path.startsWith('/groups')) return 'Chit Circles & Tickets'
    if (path.startsWith('/members')) return 'Members & KYC Directory'
    if (path.startsWith('/auctions')) return 'Auctions & Live Bidding Chamber'
    if (path.startsWith('/payouts')) return 'Prize Payouts & Collateral Sureties'
    if (path.startsWith('/reports')) return 'Financial Reports & Analytics'
    if (path.startsWith('/compliance')) return 'Regulatory Compliance & Filings'
    if (path.startsWith('/settings')) return 'Settings & Account Profile'
    return 'Chitties Management'
  }

  const handleRoleSwitch = async (roleKey) => {
    setShowProfileMenu(false)
    try {
      const newUser = await quickDemoLogin(roleKey)
      const targetHome = getRoleHomeRoute(newUser)
      navigate(targetHome)
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <div className="breadcrumbs" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <span>Chitties</span>
          <span>/</span>
          {user?.organization_id ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 600, color: 'var(--emerald-700)' }}>
              <Building2 size={13} /> Apex Chits International
            </span>
          ) : (
            <span style={{ fontWeight: 600, color: '#7e22ce' }}>Global Platform SaaS</span>
          )}
        </div>
        <h2 className="topbar-page-title" style={{ margin: '2px 0 0 0', fontSize: '1.125rem', fontWeight: 800 }}>
          {getPageTitle()}
        </h2>
      </div>

      <div className="topbar-right">
        {/* Notification Bell */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => {
              setShowNotifications(!showNotifications)
              setShowProfileMenu(false)
            }}
            className="topbar-btn"
            title="Notifications"
          >
            <Bell size={18} />
            <span className="notification-dot" />
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: '48px',
                width: '340px',
                backgroundColor: '#ffffff',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-xl)',
                zIndex: 60,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '0.875rem 1rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: 'var(--bg-subtle)',
                }}
              >
                <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Notifications (2 Unread)
                </span>
                <button
                  onClick={() => setShowNotifications(false)}
                  style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  <X size={16} />
                </button>
              </div>

              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {sampleNotifications.map((notif) => (
                  <div
                    key={notif.id}
                    style={{
                      padding: '0.875rem 1rem',
                      borderBottom: '1px solid var(--border-subtle)',
                      backgroundColor: notif.unread ? 'var(--emerald-50)' : '#ffffff',
                      display: 'flex',
                      gap: '0.75rem',
                    }}
                  >
                    {notif.type === 'success' ? (
                      <CheckCircle2 size={16} color="var(--emerald-600)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    ) : notif.type === 'warning' ? (
                      <AlertCircle size={16} color="var(--gold-600)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    ) : (
                      <Shield size={16} color="var(--emerald-600)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    )}
                    <div>
                      <p style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                        {notif.title}
                      </p>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                        {notif.message}
                      </p>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
                        {notif.time}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => {
              setShowProfileMenu(!showProfileMenu)
              setShowNotifications(false)
            }}
            className="topbar-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              width: 'auto',
              padding: '0 0.75rem',
            }}
          >
            <div
              style={{
                width: '24px',
                height: '24px',
                borderRadius: 'var(--radius-full)',
                backgroundColor: 'var(--emerald-600)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.75rem',
                fontWeight: 700,
              }}
            >
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div style={{ textAlign: 'left', lineHeight: 1.15 }}>
              <span
                style={{
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  display: 'block',
                  maxWidth: '120px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {user?.full_name}
              </span>
              <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                {roleInfo.label}
              </span>
            </div>
          </button>

          {/* Profile Dropdown */}
          {showProfileMenu && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: '48px',
                width: '270px',
                backgroundColor: '#ffffff',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-xl)',
                zIndex: 60,
                padding: '0.5rem',
              }}
            >
              <div
                style={{
                  padding: '0.75rem 0.875rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  marginBottom: '0.35rem',
                }}
              >
                <p style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                  {user?.full_name}
                </p>
                <p style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>{user?.email}</p>
                <span
                  style={{
                    display: 'inline-block',
                    marginTop: '0.35rem',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: 'var(--emerald-50)',
                    color: 'var(--emerald-800)',
                    border: '1px solid var(--emerald-200)',
                  }}
                >
                  {roleInfo.label}
                </span>
              </div>

              {/* 1-Click Role Switcher */}
              <div style={{ padding: '0.35rem 0.5rem' }}>
                <span
                  style={{
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    paddingLeft: '0.35rem',
                    display: 'block',
                    marginBottom: '0.25rem',
                  }}
                >
                  Switch Demo Persona
                </span>
                {Object.entries(DEMO_ACCOUNTS).map(([key, acc]) => (
                  <button
                    key={key}
                    onClick={() => handleRoleSwitch(key)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '0.4rem 0.5rem',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.75rem',
                      color: user?.email === acc.email ? 'var(--emerald-700)' : 'var(--text-secondary)',
                      fontWeight: user?.email === acc.email ? 700 : 500,
                      backgroundColor: user?.email === acc.email ? 'var(--emerald-50)' : 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      border: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    <span>{acc.label}</span>
                    {user?.email === acc.email && <CheckCircle2 size={12} color="var(--emerald-600)" />}
                  </button>
                ))}
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '0.35rem', paddingTop: '0.35rem' }}>
                <button
                  onClick={() => {
                    setShowProfileMenu(false)
                    navigate('/settings')
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8125rem',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <User size={15} /> My Profile & Settings
                </button>

                <button
                  onClick={logout}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8125rem',
                    color: '#dc2626',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontWeight: 600,
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <LogOut size={15} /> Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
