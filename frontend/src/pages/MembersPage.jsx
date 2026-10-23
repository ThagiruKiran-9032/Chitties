import React, { useState, useEffect } from 'react'
import {
  Users,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  UserPlus,
  X,
  Phone,
  Mail,
  Calendar,
  Eye,
  Filter,
  RefreshCw,
  Building
} from 'lucide-react'
import { membersApi } from '../api/members'

export default function MembersPage() {
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [kycFilter, setKycFilter] = useState('')
  const [selectedMember, setSelectedMember] = useState(null)
  const [reviewing, setReviewing] = useState(false)

  // Onboard Member Modal state
  const [showOnboardModal, setShowOnboardModal] = useState(false)
  const [onboardData, setOnboardData] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: 'Password@123',
    role: 'MEMBER'
  })
  const [onboardLoading, setOnboardLoading] = useState(false)
  const [onboardError, setOnboardError] = useState('')

  const fetchMembers = async () => {
    setLoading(true)
    try {
      const params = {}
      if (search) params.search = search
      if (kycFilter) params.kyc_status = kycFilter
      const res = await membersApi.list(params)
      setMembers(res.data?.items || [])
    } catch (err) {
      console.error('Failed to load members:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMembers()
  }, [kycFilter])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    fetchMembers()
  }

  const handleKycStatusUpdate = async (id, status) => {
    setReviewing(true)
    try {
      await membersApi.updateKycStatus(id, { status })
      setSelectedMember(null)
      fetchMembers()
    } catch (err) {
      alert('Failed to update KYC status: ' + (err.response?.data?.detail || err.message))
    } finally {
      setReviewing(false)
    }
  }

  const handleOnboardSubmit = async (e) => {
    e.preventDefault()
    setOnboardError('')
    setOnboardLoading(true)
    try {
      await membersApi.onboard(onboardData)
      setShowOnboardModal(false)
      setOnboardData({
        full_name: '',
        email: '',
        phone: '',
        password: 'Password@123',
        role: 'MEMBER'
      })
      fetchMembers()
    } catch (err) {
      setOnboardError(err.response?.data?.detail || err.message || 'Failed to onboard subscriber.')
    } finally {
      setOnboardLoading(false)
    }
  }

  const getKycBadge = (status) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <CheckCircle2 className="w-3.5 h-3.5" /> Verified
          </span>
        )
      case 'REJECTED':
        return (
          <span className="badge badge-red" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <XCircle className="w-3.5 h-3.5" /> Rejected
          </span>
        )
      default:
        return (
          <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
            <Clock className="w-3.5 h-3.5" /> Pending Review
          </span>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Subscribers & KYC Directory</h1>
          <p className="page-description">
            Subscribed chit members, Aadhaar/PAN regulatory verification status, and profile records.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => setShowOnboardModal(true)}
            className="btn btn-primary"
          >
            <UserPlus className="w-4 h-4" />
            <span>Onboard Member</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card">
        <div className="card-body" style={{ padding: '1rem 1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', justifyContent: 'space-between' }}>
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
            <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
              <Search className="w-4 h-4 text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search by name, email, or phone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '36px' }}
              />
            </div>
            <button type="submit" className="btn btn-outline btn-sm">Search</button>
          </form>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <select
              value={kycFilter}
              onChange={(e) => setKycFilter(e.target.value)}
              className="form-select"
              style={{ width: '170px' }}
            >
              <option value="">All KYC Statuses</option>
              <option value="PENDING">Pending Review</option>
              <option value="VERIFIED">Verified</option>
              <option value="REJECTED">Rejected</option>
            </select>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Total: <strong>{members.length}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Members Directory Table */}
      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Subscriber Name</th>
                  <th>Contact Info</th>
                  <th>Role</th>
                  <th>KYC Status</th>
                  <th>Joined Date</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                      Loading registered members...
                    </td>
                  </tr>
                ) : members.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                      No members found matching your search.
                    </td>
                  </tr>
                ) : (
                  members.map((m) => (
                    <tr key={m.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <div style={{ width: 36, height: 36, borderRadius: '50%', backgroundColor: 'var(--emerald-100)', color: 'var(--emerald-800)', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.875rem' }}>
                            {m.full_name ? m.full_name.charAt(0).toUpperCase() : 'U'}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{m.full_name}</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {m.id.substring(0, 8)}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', fontSize: '0.8125rem' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-secondary)' }}>
                            <Mail className="w-3.5 h-3.5 text-muted" /> {m.email}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)' }}>
                            <Phone className="w-3.5 h-3.5 text-muted" /> {m.phone || 'No phone'}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-blue">{m.role}</span>
                      </td>
                      <td>
                        {getKycBadge(m.kyc_status)}
                      </td>
                      <td style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                        {m.created_at ? new Date(m.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          onClick={() => setSelectedMember(m)}
                          className="btn btn-outline btn-sm"
                        >
                          <Eye className="w-3.5 h-3.5" /> Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Member Profile & KYC Review Modal */}
      {selectedMember && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Subscriber Profile & KYC</h3>
              </div>
              <button onClick={() => setSelectedMember(null)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--bg-subtle)', padding: '1rem', borderRadius: 8 }}>
                <div style={{ width: 48, height: 48, borderRadius: '50%', backgroundColor: 'var(--emerald-600)', color: '#ffffff', fontWeight: 800, fontSize: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {selectedMember.full_name ? selectedMember.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: '1.0625rem', color: 'var(--text-primary)' }}>{selectedMember.full_name}</h4>
                  <p style={{ margin: '2px 0 0 0', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{selectedMember.email}</p>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8125rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Phone Number</span>
                  <span style={{ fontWeight: 600 }}>{selectedMember.phone || 'Not provided'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>System Role</span>
                  <span className="badge badge-blue">{selectedMember.role}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Current KYC Status</span>
                  {getKycBadge(selectedMember.kyc_status)}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Registered On</span>
                  <span>{new Date(selectedMember.created_at || Date.now()).toLocaleString()}</span>
                </div>
              </div>

              {/* KYC Verification Decision Controls */}
              <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '1rem' }}>
                <h5 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>Statutory KYC Decision</h5>
                <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Under Section 14 of the Chit Funds Act, subscribers must possess verified identity (PAN / Aadhaar) before being prized or receiving prize disbursements.
                </p>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    onClick={() => handleKycStatusUpdate(selectedMember.id, 'VERIFIED')}
                    disabled={reviewing || selectedMember.kyc_status === 'VERIFIED'}
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                  >
                    <CheckCircle2 className="w-4 h-4" /> Approve & Verify
                  </button>
                  <button
                    onClick={() => handleKycStatusUpdate(selectedMember.id, 'REJECTED')}
                    disabled={reviewing || selectedMember.kyc_status === 'REJECTED'}
                    className="btn btn-danger"
                    style={{ flex: 1 }}
                  >
                    <XCircle className="w-4 h-4" /> Reject KYC
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                onClick={() => setSelectedMember(null)}
                className="btn btn-outline"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Onboard Member Modal */}
      {showOnboardModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserPlus className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Onboard New Subscriber</h3>
              </div>
              <button onClick={() => setShowOnboardModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleOnboardSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {onboardError && (
                  <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#b91c1c' }}>
                    {onboardError}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Ramesh Kumar"
                    value={onboardData.full_name}
                    onChange={(e) => setOnboardData({ ...onboardData, full_name: e.target.value })}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Email Address *</label>
                  <input
                    type="email"
                    placeholder="subscriber@example.com"
                    value={onboardData.email}
                    onChange={(e) => setOnboardData({ ...onboardData, email: e.target.value })}
                    className="form-input"
                    required
                  />
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Phone Number *</label>
                    <input
                      type="tel"
                      placeholder="+91 98765 43210"
                      value={onboardData.phone}
                      onChange={(e) => setOnboardData({ ...onboardData, phone: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Initial Role</label>
                    <select
                      value={onboardData.role}
                      onChange={(e) => setOnboardData({ ...onboardData, role: e.target.value })}
                      className="form-select"
                    >
                      <option value="MEMBER">Chit Member</option>
                      <option value="BRANCH_MANAGER">Branch Manager</option>
                      <option value="COLLECTION_AGENT">Collection Agent</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Temporary Password</label>
                  <input
                    type="text"
                    value={onboardData.password}
                    onChange={(e) => setOnboardData({ ...onboardData, password: e.target.value })}
                    className="form-input font-mono"
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowOnboardModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={onboardLoading}
                >
                  {onboardLoading ? 'Registering...' : 'Register Subscriber'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
