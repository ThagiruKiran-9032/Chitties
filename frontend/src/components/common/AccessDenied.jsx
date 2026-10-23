import React from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldAlert, ArrowLeft, Home } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { getRoleHomeRoute } from '../../utils/rbac'

export default function AccessDenied({ message, requiredRole }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const homeRoute = getRoleHomeRoute(user)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <div
        style={{
          width: '64px',
          height: '64px',
          borderRadius: 'var(--radius-full)',
          backgroundColor: 'var(--status-danger-bg)',
          color: 'var(--status-danger-text)',
          border: '1px solid var(--status-danger-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '1.25rem',
        }}
      >
        <ShieldAlert size={32} />
      </div>

      <span
        style={{
          fontSize: '0.75rem',
          fontWeight: 800,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: 'var(--status-danger-text)',
        }}
      >
        403 Forbidden • Access Denied
      </span>

      <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0.5rem 0' }}>
        Restricted Scope & Authorization
      </h2>

      <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: '440px', lineHeight: 1.5, margin: '0 0 1.5rem 0' }}>
        {message ||
          `Your authenticated account (${user?.role || 'User'}) does not hold the necessary scope or permission${
            requiredRole ? ` for role [${requiredRole}]` : ''
          } to view or execute actions on this resource under Chit Funds Act statutory rules.`}
      </p>

      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button onClick={() => navigate(-1)} className="btn btn-outline">
          <ArrowLeft size={16} /> Go Back
        </button>
        <button onClick={() => navigate(homeRoute)} className="btn btn-primary">
          <Home size={16} /> Return to My Dashboard
        </button>
      </div>
    </div>
  )
}
