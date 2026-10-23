import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Plus, ArrowLeft, RefreshCw, X } from 'lucide-react'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { organizationsApi } from '../../api/organizations'

export default function TenantsPage() {
  const navigate = useNavigate()
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    registration_number: '',
    tax_id: '',
    state_registration_details: '',
  })

  const loadTenants = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await organizationsApi.list({ page: 1, size: 50 })
      setTenants(res.data?.items || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTenants()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreating(true)
    try {
      await organizationsApi.create(formData)
      setShowCreateModal(false)
      setFormData({ name: '', registration_number: '', tax_id: '', state_registration_details: '' })
      await loadTenants()
    } catch (err) {
      alert('Error creating organization: ' + (err.response?.data?.detail || err.message))
    } finally {
      setCreating(false)
    }
  }

  const columns = [
    {
      header: 'Company Legal Name',
      accessor: (r) => (
        <div>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{r.name}</span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            UUID: {r.id}
          </span>
        </div>
      ),
    },
    {
      header: 'State Registration No',
      accessor: (r) => <span className="font-mono">{r.registration_number}</span>,
    },
    {
      header: 'Tax ID (GSTIN/PAN)',
      accessor: (r) => <span className="font-mono">{r.tax_id || '—'}</span>,
    },
    {
      header: 'Registrar Office',
      accessor: (r) => r.state_registration_details || 'Bangalore Sub-Registrar',
    },
    {
      header: 'Status',
      accessor: (r) => (
        <span className={`badge ${r.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}`}>
          {r.status}
        </span>
      ),
    },
    {
      header: 'Onboarded Date',
      accessor: (r) => new Date(r.created_at).toLocaleDateString(),
    },
  ]

  if (loading) return <LoadingState message="Loading platform tenant registry..." />
  if (error) return <ErrorState message={error} onRetry={loadTenants} />

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/platform/dashboard')} className="btn btn-outline btn-sm" style={{ marginBottom: '0.5rem' }}>
            <ArrowLeft size={13} /> Back to Overview
          </button>
          <h1 className="page-title">Tenant Organizations Directory</h1>
          <p className="page-description">
            Multi-tenant company registry under the statutory jurisdiction of State Chit Registrars.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadTenants} className="btn btn-outline">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary">
            <Plus size={16} /> Provision Tenant
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={columns}
            data={tenants}
            emptyTitle="No tenant companies registered"
            emptyDescription="Provision a new chit fund company using the button above."
          />
        </div>
      </div>

      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Building2 size={20} color="var(--emerald-600)" />
                <h3 className="modal-title">Provision New Organization</h3>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="btn-icon-only">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="form-label">Company Legal Name *</label>
                  <input
                    type="text"
                    required
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
                    value={formData.registration_number}
                    onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>
                <div>
                  <label className="form-label">Tax ID (GSTIN / PAN)</label>
                  <input
                    type="text"
                    value={formData.tax_id}
                    onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>
                <div>
                  <label className="form-label">State Registration Office Details</label>
                  <textarea
                    rows={2}
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
                  {creating ? 'Provisioning...' : 'Provision Tenant'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
