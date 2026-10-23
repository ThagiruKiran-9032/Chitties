import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CircleDot,
  Plus,
  Calendar,
  Clock,
  Users,
  ArrowRight,
  Search,
  Filter,
  CheckCircle2,
  X,
  Layers,
  Sparkles,
  ShieldCheck
} from 'lucide-react'
import { groupsApi } from '../api/groups'
import { schemesApi } from '../api/schemes'
import { branchesApi } from '../api/branches'

export default function ChitGroupsPage({ onSelectGroup }) {
  const navigate = useNavigate()
  const [groups, setGroups] = useState([])
  const [schemes, setSchemes] = useState([])
  const [branches, setBranches] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [showModal, setShowModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  const [formData, setFormData] = useState({
    scheme_id: '',
    branch_id: '',
    group_code: '',
    start_date: '',
    end_date: '',
    auction_day_of_month: 15,
    auction_time: '17:00:00',
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [groupsRes, schemesRes, branchesRes] = await Promise.all([
        groupsApi.list(),
        schemesApi.list().catch(() => ({ data: { items: [] } })),
        branchesApi.list().catch(() => ({ data: { items: [] } })),
      ])
      setGroups(groupsRes.data?.items || [])
      setSchemes(schemesRes.data?.items || [])
      setBranches(branchesRes.data?.items || [])
    } catch (err) {
      console.error('Failed to load group data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError('')
    if (!formData.scheme_id || !formData.branch_id || !formData.group_code || !formData.start_date || !formData.end_date) {
      setFormError('Please fill in all mandatory fields before launching.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        ...formData,
        auction_day_of_month: parseInt(formData.auction_day_of_month),
      }
      await groupsApi.create(payload)
      setShowModal(false)
      setFormData({
        scheme_id: '',
        branch_id: '',
        group_code: '',
        start_date: '',
        end_date: '',
        auction_day_of_month: 15,
        auction_time: '17:00:00',
      })
      fetchData()
    } catch (err) {
      setFormError(err.response?.data?.detail || err.message || 'Failed to launch chit circle.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleGroupClick = (groupId) => {
    if (onSelectGroup) {
      onSelectGroup(groupId)
    } else {
      navigate(`/groups/${groupId}`)
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="badge badge-emerald">Active</span>
      case 'ENROLLING':
        return <span className="badge badge-blue">Enrolling</span>
      case 'COMPLETED':
        return <span className="badge badge-slate">Completed</span>
      default:
        return <span className="badge badge-amber">Draft</span>
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  // Filter groups
  const filteredGroups = groups.filter((g) => {
    const matchesSearch = g.group_code.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'ALL' || g.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Chit Circles & Groups</h1>
          <p className="page-description">
            Regulated chit circles, member subscriber quotas, enrollment capacity, and auction schedules.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => setShowModal(true)}
            className="btn btn-primary"
          >
            <Plus className="w-4 h-4" />
            <span>Launch Circle</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card">
        <div className="card-body" style={{ padding: '1rem 1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
            <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
              <Search className="w-4 h-4 text-muted" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search by circle code (e.g. APEX-GOLD)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '36px' }}
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-select"
              style={{ width: '160px' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="ENROLLING">Enrolling</option>
              <option value="DRAFT">Draft</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            <span>Showing: <strong>{filteredGroups.length}</strong> of {groups.length} circles</span>
          </div>
        </div>
      </div>

      {/* Chit Circles Grid */}
      {loading ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            Loading active chit circles...
          </div>
        </div>
      ) : filteredGroups.length === 0 ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
            <CircleDot className="w-12 h-12 text-muted" style={{ margin: '0 auto 1rem auto', strokeWidth: 1.5 }} />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>No Chit Circles Found</h3>
            <p style={{ maxWidth: '400px', margin: '0.5rem auto 1.5rem auto', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              {searchQuery || statusFilter !== 'ALL'
                ? 'No circles matched your search query or filter.'
                : 'No chit circles have been launched yet. Click "Launch Circle" to configure your first chit scheme.'}
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="btn btn-primary"
            >
              <Plus className="w-4 h-4" /> Launch Circle Now
            </button>
          </div>
        </div>
      ) : (
        <div className="grid-cols-3">
          {filteredGroups.map((g) => {
            const pct = g.total_capacity > 0 ? Math.round((g.enrolled_count / g.total_capacity) * 100) : 0
            return (
              <div
                key={g.id}
                className="card"
                style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                onClick={() => handleGroupClick(g.id)}
              >
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-700)', fontSize: '1rem' }}>
                      {g.group_code}
                    </span>
                  </div>
                  {getStatusBadge(g.status)}
                </div>

                <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Round indicator */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Current Round</span>
                    <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                      Month #{g.current_month || 1}
                    </span>
                  </div>

                  {/* Enrollment Capacity Progress Bar */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      <span>Enrolled Subscribers</span>
                      <span className="font-mono" style={{ fontWeight: 600, color: 'var(--emerald-700)' }}>
                        {g.enrolled_count} / {g.total_capacity} tickets ({pct}%)
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${pct}%`, backgroundColor: pct >= 100 ? 'var(--emerald-600)' : 'var(--emerald-500)' }}
                      />
                    </div>
                  </div>

                  {/* Schedule Details */}
                  <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '0.75rem 1rem', fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.35rem', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Calendar className="w-3.5 h-3.5 text-muted" />
                      <span>Period: {g.start_date} to {g.end_date}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Clock className="w-3.5 h-3.5 text-muted" />
                      <span>Auction: Day {g.auction_day_of_month} of month @ {g.auction_time}</span>
                    </div>
                  </div>
                </div>

                <div className="card-footer" style={{ justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Click to manage tickets & ledger
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--emerald-600)', fontWeight: 600, fontSize: '0.8125rem' }}>
                    <span>Manage</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Launch Circle Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '580px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CircleDot className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Launch New Chit Circle</h3>
              </div>
              <button onClick={() => setShowModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {formError && (
                  <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#b91c1c' }}>
                    {formError}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Chit Scheme *</label>
                  <select
                    value={formData.scheme_id}
                    onChange={(e) => setFormData({ ...formData, scheme_id: e.target.value })}
                    className="form-select"
                    required
                  >
                    <option value="">Select an approved scheme...</option>
                    {schemes.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.scheme_code} - {s.scheme_name} (Chit Value: {formatINR(s.chit_value)})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Branch *</label>
                    <select
                      value={formData.branch_id}
                      onChange={(e) => setFormData({ ...formData, branch_id: e.target.value })}
                      className="form-select"
                      required
                    >
                      <option value="">Select branch...</option>
                      {branches.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.branch_name} ({b.branch_code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Circle Code *</label>
                    <input
                      type="text"
                      placeholder="e.g. APEX-GOLD-2026-02"
                      value={formData.group_code}
                      onChange={(e) => setFormData({ ...formData, group_code: e.target.value.toUpperCase() })}
                      className="form-input font-mono"
                      required
                    />
                  </div>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Start Date *</label>
                    <input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">End Date *</label>
                    <input
                      type="date"
                      value={formData.end_date}
                      onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Auction Day of Month (1-28)</label>
                    <input
                      type="number"
                      min="1"
                      max="28"
                      value={formData.auction_day_of_month}
                      onChange={(e) => setFormData({ ...formData, auction_day_of_month: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Auction Time</label>
                    <input
                      type="time"
                      value={formData.auction_time.substring(0, 5)}
                      onChange={(e) => setFormData({ ...formData, auction_time: `${e.target.value}:00` })}
                      className="form-input"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Launching...' : 'Create & Launch Circle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
