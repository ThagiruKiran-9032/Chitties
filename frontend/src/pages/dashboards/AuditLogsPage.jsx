import React, { useState, useEffect } from 'react'
import { FileText, ShieldCheck, RefreshCw } from 'lucide-react'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import client from '../../api/client'

export default function AuditLogsPage({ title = 'Regulatory & System Audit Logs' }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterAction, setFilterAction] = useState('')

  const loadLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = filterAction ? `/audit-logs?action=${filterAction}&limit=100` : '/audit-logs?limit=100'
      const res = await client.get(url)
      setLogs(res.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [filterAction])

  const columns = [
    {
      header: 'Timestamp',
      accessor: (r) => (
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
          {new Date(r.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      header: 'Action Taken',
      accessor: (r) => (
        <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
          {r.action}
        </span>
      ),
    },
    {
      header: 'Actor User',
      accessor: (r) => (
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
          {r.user_name || 'System / Batch'}
        </span>
      ),
    },
    {
      header: 'Entity Type',
      accessor: (r) => <span className="badge badge-slate">{r.entity_type}</span>,
    },
    {
      header: 'Changes / Payload',
      accessor: (r) => (
        <span
          className="font-mono"
          style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', maxWidth: '280px', display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          title={JSON.stringify(r.changes_json)}
        >
          {r.changes_json ? JSON.stringify(r.changes_json) : '—'}
        </span>
      ),
    },
    {
      header: 'IP Address',
      accessor: (r) => <span className="font-mono" style={{ fontSize: '0.75rem' }}>{r.ip_address || '127.0.0.1'}</span>,
    },
  ]

  if (loading) return <LoadingState message="Loading immutable audit trail records..." />
  if (error) return <ErrorState message={error} onRetry={loadLogs} />

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={18} color="var(--emerald-600)" />
            <span className="badge badge-emerald">Statutory Audit Trail</span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>{title}</h1>
          <p className="page-description">
            Tamper-evident, chronological log of all administrative actions, financial approvals, and statutory state transitions.
          </p>
        </div>
        <div className="page-actions">
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="form-input"
            style={{ width: 'auto', fontSize: '0.8125rem' }}
          >
            <option value="">All Actions</option>
            <option value="LOGIN">User Logins</option>
            <option value="RECORD_PAYMENT">Installment Collections</option>
            <option value="AUTHORIZE_DISBURSEMENT">Payout Approvals</option>
            <option value="START_AUCTION">Auctions Started</option>
            <option value="CLOSE_AUCTION">Auctions Settled</option>
            <option value="LODGE_SECURITY_DEPOSIT">Section 20 Pledges</option>
          </select>
          <button onClick={loadLogs} className="btn btn-outline">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={columns}
            data={logs}
            emptyTitle="No audit records found"
            emptyDescription="Events matching the filter will be chronologically indexed here."
          />
        </div>
      </div>
    </div>
  )
}
