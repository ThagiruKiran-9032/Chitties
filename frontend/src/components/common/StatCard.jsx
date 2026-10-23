import React from 'react'

export default function StatCard({
  label,
  value,
  icon: Icon,
  variant = 'emerald', // emerald | blue | gold | purple | red | slate
  trend,
  trendPositive = true,
  helperText,
  onClick,
}) {
  const variantStyles = {
    emerald: { bg: 'var(--emerald-50)', color: 'var(--emerald-700)', border: 'var(--emerald-200)' },
    blue: { bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe' },
    gold: { bg: 'var(--gold-50)', color: 'var(--gold-700)', border: 'var(--gold-200)' },
    purple: { bg: '#faf5ff', color: '#7e22ce', border: '#e9d5ff' },
    red: { bg: '#fef2f2', color: '#dc2626', border: '#fecaca' },
    slate: { bg: 'var(--bg-subtle)', color: 'var(--text-secondary)', border: 'var(--border-subtle)' },
  }

  const v = variantStyles[variant] || variantStyles.emerald

  return (
    <div
      onClick={onClick}
      className={`card ${onClick ? 'cursor-pointer hover:border-emerald-500 transition-all' : ''}`}
      style={{
        padding: '1.25rem 1.5rem',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-card)',
        boxShadow: 'var(--shadow-xs)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          {label}
        </span>
        {Icon && (
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: v.bg,
              color: v.color,
              border: `1px solid ${v.border}`,
            }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>

      <div>
        <div
          style={{
            fontSize: '1.625rem',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            lineHeight: 1.15,
          }}
        >
          {value}
        </div>

        {(trend || helperText) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.625rem', fontSize: '0.75rem' }}>
            {trend && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 700,
                  fontSize: '0.6875rem',
                  backgroundColor: trendPositive ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
                  color: trendPositive ? 'var(--status-success-text)' : 'var(--status-danger-text)',
                  border: `1px solid ${trendPositive ? 'var(--status-success-border)' : 'var(--status-danger-border)'}`,
                }}
              >
                {trend}
              </span>
            )}
            {helperText && (
              <span style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {helperText}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
