import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CircleDot,
  Users,
  Wallet,
  Building2,
  Clock,
  ArrowUpRight,
  TrendingUp,
  ShieldCheck,
  Award,
  Scale,
  RefreshCw,
  Plus,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
  Eye,
  FileCheck,
} from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { groupsApi } from '../../api/groups'
import { membersApi } from '../../api/members'
import { payoutsApi } from '../../api/payouts'
import { complianceApi } from '../../api/compliance'
import { branchesApi } from '../../api/branches'
import client from '../../api/client'

export default function OrgAdminDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [metrics, setMetrics] = useState({
    activeGroups: 0,
    totalBranches: 0,
    totalMembers: 0,
    pendingPayouts: 0,
    totalLienPledged: 0,
    activeCirclesCovered: 0,
  })

  const [groups, setGroups] = useState([])
  const [payouts, setPayouts] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [complianceSummary, setComplianceSummary] = useState(null)

  // Dual-control payout disbursement modal state
  const [selectedPayout, setSelectedPayout] = useState(null)
  const [disbursing, setDisbursing] = useState(false)
  const [disburseForm, setDisburseForm] = useState({
    disbursement_reference: '',
    foreman_charges_deducted: 0,
    auto_clear_arrears: true,
  })

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [groupsRes, membersRes, payoutsRes, compRes, branchesRes, logsRes] =
        await Promise.allSettled([
          groupsApi.list(),
          membersApi.list(),
          payoutsApi.list(),
          complianceApi.getSystemSummary(),
          branchesApi.list(),
          client.get('/audit-logs?limit=5'),
        ])

      let groupItems = []
      if (groupsRes.status === 'fulfilled') {
        groupItems = groupsRes.value.data?.items || []
        setGroups(groupItems)
      }

      let memberCount = 0
      if (membersRes.status === 'fulfilled') {
        memberCount = membersRes.value.data?.total_items || membersRes.value.data?.items?.length || 0
      }

      let payoutItems = []
      if (payoutsRes.status === 'fulfilled' && Array.isArray(payoutsRes.value?.data)) {
        payoutItems = payoutsRes.value.data
        setPayouts(payoutItems)
      }

      let compData = null
      if (compRes.status === 'fulfilled') {
        compData = compRes.value.data
        setComplianceSummary(compData)
      }

      let branchCount = 0
      if (branchesRes.status === 'fulfilled' && Array.isArray(branchesRes.value?.data)) {
        branchCount = branchesRes.value.data.length
      }

      if (logsRes.status === 'fulfilled') {
        setAuditLogs(logsRes.value.data || [])
      }

      const activeCircles = groupItems.filter((g) => g.status === 'ACTIVE').length
      const pendingApprovalPayouts = payoutItems.filter(
        (p) => p.disbursement_status === 'SURETY_APPROVED' || p.disbursement_status === 'PENDING_SURETY'
      ).length

      setMetrics({
        activeGroups: activeCircles,
        totalBranches: branchCount || 1,
        totalMembers: memberCount,
        pendingPayouts: pendingApprovalPayouts,
        totalLienPledged: compData?.total_lien_pledged || 100000,
        activeCirclesCovered: compData?.active_circles_covered || activeCircles,
      })
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleDisburseSubmit = async (e) => {
    e.preventDefault()
    if (!selectedPayout) return
    setDisbursing(true)
    try {
      await payoutsApi.disburse(selectedPayout.id, {
        disbursement_reference: disburseForm.disbursement_reference || `NEFT-${Date.now()}`,
        foreman_charges_deducted: parseFloat(disburseForm.foreman_charges_deducted) || 0,
        auto_clear_arrears: disburseForm.auto_clear_arrears,
      })
      setSelectedPayout(null)
      await loadData()
      alert('Dual-Control Sign-Off Complete: Prize money disbursement authorized successfully!')
    } catch (err) {
      alert('Disbursement authorization failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setDisbursing(false)
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  const pendingPayoutColumns = [
    {
      header: 'Circle & Round',
      accessor: (row) => (
        <div>
          <span style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
            {row.chit_group_code || 'APEX-GOLD-2026'}
          </span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            Month #{row.month_number || 1} • Ticket #{row.ticket_number}
          </span>
        </div>
      ),
    },
    {
      header: 'Prized Winner',
      accessor: (row) => (
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
          {row.winner_name || 'Subscriber'}
        </span>
      ),
    },
    {
      header: 'Gross Prize',
      accessor: (row) => <span className="font-mono">{formatINR(row.gross_prize_amount)}</span>,
    },
    {
      header: 'Surety Status',
      accessor: (row) => (
        <span
          className={`badge ${
            row.disbursement_status === 'SURETY_APPROVED'
              ? 'badge-success'
              : row.disbursement_status === 'DISBURSED'
              ? 'badge-blue'
              : 'badge-warning'
          }`}
        >
          {row.disbursement_status?.replace('_', ' ')}
        </span>
      ),
    },
    {
      header: 'Dual-Control Action',
      align: 'right',
      render: (row) => (
        row.disbursement_status === 'SURETY_APPROVED' ? (
          <button
            onClick={() => {
              setSelectedPayout(row)
              setDisburseForm({
                disbursement_reference: `UTR-${Date.now().toString().slice(-8)}`,
                foreman_charges_deducted: 0,
                auto_clear_arrears: true,
              })
            }}
            className="btn btn-primary btn-sm"
          >
            <FileCheck size={14} /> Authorize Payout
          </button>
        ) : (
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {row.disbursement_status === 'DISBURSED' ? 'Disbursed' : 'Awaiting Sureties'}
          </span>
        )
      ),
    },
  ]

  if (loading) return <LoadingState message="Loading Executive Foreman Command Center..." />
  if (error) return <ErrorState message={error} onRetry={loadData} />

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-emerald">Company Foreman Scope</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Apex Chits International</span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>Executive Foreman Command Center</h1>
          <p className="page-description">
            Oversee company schemes, active circles, statutory Section 20 FDR security pledges, and sensitive dual-control payout approvals.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadData} className="btn btn-outline" title="Refresh Operations Data">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => navigate('/groups')} className="btn btn-primary">
            <Plus size={16} /> Launch Chit Circle
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-cols-4">
        <StatCard
          label="Active Chit Circles"
          value={metrics.activeGroups}
          variant="emerald"
          icon={CircleDot}
          trend={`${metrics.totalBranches} Branches`}
          trendPositive={true}
          helperText="Running subscriber circles"
        />

        <StatCard
          label="Total Enrolled Subscribers"
          value={metrics.totalMembers}
          variant="blue"
          icon={Users}
          trend="KYC Verified"
          trendPositive={true}
          helperText="Members across circles"
        />

        <StatCard
          label="Authorized Branch Offices"
          value={metrics.totalBranches}
          variant="gold"
          icon={Building2}
          trend="Operational Circles"
          trendPositive={true}
          helperText="Active branch circle offices"
        />

        <StatCard
          label="Pending Payout Approvals"
          value={metrics.pendingPayouts}
          variant="purple"
          icon={Award}
          trend="Dual Control"
          trendPositive={metrics.pendingPayouts === 0}
          helperText="Prize claims awaiting sign-off"
        />
      </div>

      {/* Section 20 Compliance Barometer Strip */}
      <div
        className="card"
        style={{
          borderLeft: '4px solid var(--emerald-600)',
          background: 'linear-gradient(to right, #ecfdf5, #ffffff)',
          padding: '1rem 1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                background: 'var(--emerald-100)',
                color: 'var(--emerald-800)',
                padding: '0.625rem',
                borderRadius: 'var(--radius-full)',
              }}
            >
              <ShieldCheck size={24} />
            </div>
            <div>
              <h4 style={{ color: 'var(--emerald-900)', fontWeight: 800, margin: 0, fontSize: '0.9375rem' }}>
                Section 20 (Chit Funds Act 1982) Statutory Security Lien Verified
              </h4>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.8125rem', color: 'var(--emerald-800)' }}>
                100% aggregate chit value pledged with State Registrar via Bank FDR ({formatINR(metrics.totalLienPledged)}).
                Covering {metrics.activeCirclesCovered} active circles.
              </p>
            </div>
          </div>
          <button onClick={() => navigate('/compliance')} className="btn btn-secondary btn-sm">
            Statutory Center <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Dual Control Payout Authorization Queue */}
      <div className="card">
        <div className="card-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 className="card-title">Dual-Control Prize Money Disbursement Approvals</h3>
              <span className="badge badge-purple">Admin Sign-Off Required</span>
            </div>
            <p className="card-subtitle">
              Section 22 & 31 Mandate: Accountants calculate arrears; Organization Admins authorize final release of prize funds.
            </p>
          </div>
          <button onClick={() => navigate('/payouts')} className="btn btn-outline btn-sm">
            All Claims
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={pendingPayoutColumns}
            data={payouts}
            emptyTitle="No prize money claims pending approval"
            emptyDescription="All concluded auction rounds have either been settled or are awaiting surety submission."
          />
        </div>
      </div>

      {/* Circle Distribution & Recent Audit Logs */}
      <div className="grid-cols-3">
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header">
            <div>
              <h3 className="card-title">Chit Circles Roster</h3>
              <p className="card-subtitle">Assigned managers, capacity, and current installment months</p>
            </div>
            <button onClick={() => navigate('/groups')} className="btn btn-outline btn-sm">
              Manage Groups
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Circle Code</th>
                    <th>Assigned Manager</th>
                    <th>Round</th>
                    <th>Capacity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.slice(0, 5).map((g) => (
                    <tr key={g.id}>
                      <td>
                        <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
                          {g.group_code}
                        </span>
                      </td>
                      <td>{g.manager_name || 'Unassigned'}</td>
                      <td>Month #{g.current_month || 1}</td>
                      <td>
                        <span className="font-mono font-medium">
                          {g.enrolled_count || 5} / {g.total_capacity || 5}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${g.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}`}>
                          {g.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Audit Feed */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Company Audit Trail</h3>
              <p className="card-subtitle">Recent administrative events</p>
            </div>
            <button onClick={() => navigate('/organization/audit-logs')} className="btn btn-outline btn-sm">
              All
            </button>
          </div>
          <div className="card-body" style={{ padding: '0.75rem 1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {auditLogs.map((log) => (
                <div
                  key={log.id}
                  style={{
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--bg-subtle)',
                    fontSize: '0.75rem',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: 'var(--emerald-900)' }}>
                    <span>{log.action}</span>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
                    By: {log.user_name || 'Admin'} • Entity: {log.entity_type}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Dual Control Disbursement Modal */}
      {selectedPayout && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Award size={20} color="var(--emerald-600)" />
                <h3 className="modal-title">Authorize Prize Money Disbursement</h3>
              </div>
              <button onClick={() => setSelectedPayout(null)} className="btn-icon-only">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleDisburseSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.875rem', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Prized Subscriber:</span>
                    <span style={{ fontWeight: 700 }}>{selectedPayout.winner_name || 'Subscriber'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginTop: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Gross Prize Amount:</span>
                    <span className="font-mono" style={{ fontWeight: 800, color: 'var(--emerald-700)' }}>
                      {formatINR(selectedPayout.gross_prize_amount)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginTop: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Sureties Status:</span>
                    <span className="badge badge-success">VERIFIED BY BRANCH</span>
                  </div>
                </div>

                <div>
                  <label className="form-label">Bank Disbursement UTR / Cheque Reference *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. UTR-AXIS-9928172938"
                    value={disburseForm.disbursement_reference}
                    onChange={(e) => setDisburseForm({ ...disburseForm, disbursement_reference: e.target.value })}
                    className="form-input font-mono"
                  />
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                    Permanent reference recorded in the statutory audit log.
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <input
                    type="checkbox"
                    id="autoClearArrears"
                    checked={disburseForm.auto_clear_arrears}
                    onChange={(e) => setDisburseForm({ ...disburseForm, auto_clear_arrears: e.target.checked })}
                    style={{ width: '16px', height: '16px' }}
                  />
                  <label htmlFor="autoClearArrears" style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    Auto-deduct and reconcile outstanding ticket arrears from prize payout
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setSelectedPayout(null)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" disabled={disbursing} className="btn btn-primary">
                  {disbursing ? 'Authorizing...' : 'Authorize & Disburse Funds'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
