import React from 'react'
import { Inbox } from 'lucide-react'

export default function EmptyState({
  title = 'No records found',
  description = 'There are no items matching this criteria right now.',
  icon: Icon = Inbox,
  action,
  actionLabel,
  height = '240px',
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '2.5rem 1.5rem',
        minHeight: height,
        backgroundColor: 'var(--bg-card)',
        borderRadius: 'var(--radius-lg)',
        border: '1px dashed var(--border-medium)',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: 'var(--radius-full)',
          backgroundColor: 'var(--bg-subtle)',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '1rem',
        }}
      >
        <Icon size={24} />
      </div>

      <h4 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700, color: 'var(--text-primary)' }}>
        {title}
      </h4>
      <p style={{ margin: '0.35rem 0 1.25rem 0', fontSize: '0.8125rem', color: 'var(--text-muted)', maxWidth: '340px' }}>
        {description}
      </p>

      {action && actionLabel && (
        <button onClick={action} className="btn btn-primary btn-sm">
          {actionLabel}
        </button>
      )}
    </div>
  )
}
