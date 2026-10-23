import React from 'react'
import { RefreshCw } from 'lucide-react'

export default function LoadingState({ message = 'Loading records...', height = '200px' }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        minHeight: height,
        padding: '2rem',
        color: 'var(--text-muted)',
      }}
    >
      <RefreshCw className="animate-spin" size={24} style={{ color: 'var(--emerald-600)' }} />
      <span style={{ fontSize: '0.8125rem', fontWeight: 600, letterSpacing: '0.02em' }}>
        {message}
      </span>
    </div>
  )
}
