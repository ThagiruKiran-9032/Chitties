import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default function ErrorState({
  title = 'Failed to load data',
  message = 'An error occurred while fetching information from the server.',
  onRetry,
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--status-danger-border)',
        backgroundColor: 'var(--status-danger-bg)',
        textAlign: 'center',
        margin: '1rem 0',
      }}
    >
      <AlertCircle size={28} style={{ color: 'var(--status-danger-text)', marginBottom: '0.75rem' }} />
      <h4 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700, color: 'var(--status-danger-text)' }}>
        {title}
      </h4>
      <p style={{ margin: '0.35rem 0 1rem 0', fontSize: '0.8125rem', color: '#7f1d1d', maxWidth: '400px' }}>
        {message}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-outline btn-sm"
          style={{
            backgroundColor: '#ffffff',
            borderColor: 'var(--status-danger-border)',
            color: 'var(--status-danger-text)',
          }}
        >
          <RefreshCw size={14} /> Retry Request
        </button>
      )}
    </div>
  )
}
