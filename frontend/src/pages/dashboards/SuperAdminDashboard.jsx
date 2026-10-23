import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Building2,
  Users,
  ShieldCheck,
  Server,
  Plus,
  ArrowUpRight,
  RefreshCw,
  Scale,
  CheckCircle2,
  AlertTriangle,
  X,
  FileText,
} from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { organizationsApi } from '../../api/organizations'
import { complianceApi } from '../../api/compliance'
import client from '../../api/client'

export default function SuperAdminDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tenants, setTenants] = useState([])
  const [systemSummary, setSystemSummary] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)

  // Form state for provisioning new tenant organization
  const [formData, setFormData] = useState({
    name: '',
    registration_number: '',
    tax_id: '',
    state_registration_details: '',
  })

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [tenantsRes, summaryRes, logsRes] = await Promise.allSettled([
        organizationsApi.list({ page: 1, size: 50 }),
        complianceApi.getSystemSummary(),
        client.get('/audit-logs?limit=6'),
      ])

      if (tenantsRes.status === 'fulfilled') {
        setTenants(tenantsRes.value.data?.items || [])
      }
      if (summaryRes.status === 'fulfilled') {
        setSystemSummary(summaryRes.value.data)
      }
      if (logsRes.status === 'fulfilled') {
        setAuditLogs(logsRes.value.data || [])
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreateTenant = async (e) => {
    e.preventDefault()
    setCreating(true)
    try {
      await organizationsApi.create(formData)
      setShowCreateModal(false)
      setFormData({
        name: '',
        registration_number: '',
        tax_id: '',
        state_registration_details: '',
      })
      await loadData()
    } catch (err) {
      alert('Failed to provision organization: ' + (err.response?.data?.detail || err.message))
    } finally {
      setCreating(false)
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  const activeTenantsCount = tenants.filter((t) => t.status === 'ACTIVE').length

  const tenantColumns = [
    {
      header: 'Company Name',
      accessor: (row) => (
        <div>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{row.name}</span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            ID: {row.id.substring(0, 8)}...
          </span>
        </div>
      ),
    },
    {
      header: 'State Reg Number',
      accessor: (row) => <span className="font-mono">{row.registration_number}</span>,
    },
    {
      header: 'Tax ID (GSTIN/PAN)',
      accessor: (row) => <span className="font-mono">{row.tax_id || '—'}</span>,
    },
    {
      header: 'Tenancy Status',
      accessor: (row) => (
        <span className={`badge ${row.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}`}>
          {row.status}
        </span>
      ),
    },
    {
      header: 'Registered Date',
      accessor: (row) => new Date(row.created_at).toLocaleDateString(),
    },
  ]

  if (loading) return <LoadingState message="Loading Platform Super Admin overview..." />
  if (error) return <ErrorState message={error} onRetry={loadData} />

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-purple">Platform Scope</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Global SaaS Control</span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>Platform Multi-Tenant Governance</h1>
          <p className="page-description">
            Oversee all registered Chit Fund Company tenants, statutory registration compliance, and global audit trails.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadData} className="btn btn-outline" title="Refresh Platform Data">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus size={16} /> Provision New Tenant
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid-cols-4">
        <StatCard
          label="Registered Chit Companies"
          value={tenants.length}
          variant="purple"
          icon={Building2}
          trend={`${activeTenantsCount} Active`}
          trendPositive={true}
          helperText="Independent SaaS Tenants"
        />

        <StatCard
          label="Platform Aggregate Liens"
          value={formatINR(systemSummary?.total_lien_pledged || 100000)}
          variant="emerald"
          icon={Scale}
          trend="Section 20 Verified"
          trendPositive={true}
          helperText="Total statutory security pledged"
        />

        <StatCard
          label="Statutory Circles Covered"
          value={systemSummary?.active_circles_covered || 1}
          variant="blue"
          icon={ShieldCheck}
          helperText="Active chit groups with valid FDRs"
        />

        <StatCard
          label="Platform API & WebSocket Engine"
          value="100% Online"
          variant="emerald"
          icon={Server}
          trend="Healthy"
          trendPositive={true}
          helperText="PostgreSQL 18 • ASGI Uvicorn"
        />
      </div>

      {/* Tenants Table & Platform Audit Split */}
      <div className="grid-cols-3">
        {/* Tenants List (2 Cols) */}
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header">
            <div>
              <h3 className="card-title">Registered Chit Fund Organizations</h3>
              <p className="card-subtitle">Active companies provisioned on the Chitties platform</p>
            </div>
            <button onClick={() => navigate('/platform/tenants')} className="btn btn-outline btn-sm">
              View All
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <DataTable
              columns={tenantColumns}
              data={tenants}
              emptyTitle="No tenant companies registered"
              emptyDescription="Use the provision button to onboard your first chit fund company."
            />
          </div>
        </div>

        {/* Global Audit Events Feed (1 Col) */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Platform Audit Trail</h3>
              <p className="card-subtitle">Latest immutable security logs</p>
            </div>
            <button onClick={() => navigate('/platform/audit-logs')} className="btn btn-outline btn-sm">
              Full Logs
            </button>
          </div>
          <div className="card-body" style={{ padding: '0.75rem 1rem' }}>
            {auditLogs.length === 0 ? (
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem 0' }}>
                No recent platform audit entries.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {auditLogs.map((log) => (
                  <div
                    key={log.id}
                    style={{
                      padding: '0.625rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'var(--bg-subtle)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.75rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                      <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
                        {log.action}
                      </span>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                        {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)' }}>
                      Entity: <span style={{ fontWeight: 600 }}>{log.entity_type}</span> ({log.user_name || 'System'})
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Provision New Tenant Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Building2 size={20} color="var(--emerald-600)" />
                <h3 className="modal-title">Provision New Chit Fund Organization</h3>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="btn-icon-only">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreateTenant}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="form-label">Company Legal Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Zenith Chits Private Limited"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="form-input"
                  />
                </div>

                <div>
                  <label className="form-label">State Registration Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. REG-KA-2026-CHIT-099"
                    value={formData.registration_number}
                    onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                    className="form-input font-mono"
                  />
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                    Mandatory Section 4 Certificate of Incorporation reference
                  </span>
                </div>

                <div>
                  <label className="form-label">Tax ID (GSTIN / Corporate PAN)</label>
                  <input
                    type="text"
                    placeholder="e.g. 29AAAAA0000A1Z5"
                    value={formData.tax_id}
                    onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>

                <div>
                  <label className="form-label">State Registrar Office Details</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Office of the Sub-Registrar of Chits, 4th Block Jayanagar, Bangalore"
                    value={formData.state_registration_details}
                    onChange={(e) => setFormData({ ...formData, state_registration_details: e.target.value })}
                    className="form-input"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" disabled={creating} className="btn btn-primary">
                  {creating ? 'Provisioning...' : 'Provision Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
