import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Wallet,
  Clock,
  RefreshCw,
  Eye,
  FileCheck,
  CheckCircle2,
  Calendar,
  X,
  CreditCard,
  CircleDot,
  Scale,
  Award,
  Layers,
  ArrowRight,
} from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { payoutsApi } from '../../api/payouts'
import { complianceApi } from '../../api/compliance'
import { groupsApi } from '../../api/groups'

export default function AccountantDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [payouts, setPayouts] = useState([])
  const [systemSummary, setSystemSummary] = useState(null)
  const [groups, setGroups] = useState([])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [payoutsRes, compRes, groupsRes] = await Promise.allSettled([
        payoutsApi.list(),
        complianceApi.getSystemSummary(),
        groupsApi.list(),
      ])

      if (payoutsRes.status === 'fulfilled' && Array.isArray(payoutsRes.value?.data)) {
        setPayouts(payoutsRes.value.data)
      }

      if (compRes.status === 'fulfilled') {
        setSystemSummary(compRes.value.data)
      }

      if (groupsRes.status === 'fulfilled') {
        setGroups(groupsRes.value.data?.items || [])
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

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  const groupColumns = [
    {
      header: 'Group Code',
      accessor: (row) => (
        <div>
          <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
            {row.group_code}
          </span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            Month {row.current_month || 1}
          </span>
        </div>
      ),
    },
    {
      header: 'Monthly Installment',
      accessor: (row) => (
        <span className="font-mono" style={{ fontWeight: 700 }}>
          {formatINR(row.monthly_installment || 20000)}
        </span>
      ),
    },
    {
      header: 'Total Value',
      accessor: (row) => (
        <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
          {formatINR(row.total_value || 100000)}
        </span>
      ),
    },
    {
      header: 'Enrolled / Capacity',
      accessor: (row) => (
        <span>
          {row.enrolled_count || 0} / {row.total_capacity || 5} Tickets
        </span>
      ),
    },
    {
      header: 'Status',
      accessor: (row) => (
        <span className={`badge ${row.status === 'ACTIVE' ? 'badge-success' : 'badge-slate'}`}>
          {row.status}
        </span>
      ),
    },
    {
      header: 'Actions',
      align: 'right',
      render: (row) => (
        <button
          onClick={() => navigate(`/groups/${row.id}`)}
          className="btn btn-outline btn-sm"
        >
          View Ledger <ArrowRight size={13} />
        </button>
      ),
    },
  ]

  if (loading) return <LoadingState message="Loading Financial Ledger & Payouts overview..." />
  if (error) return <ErrorState message={error} onRetry={loadData} />

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-gold">Financial Ledger Scope</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Accounting & Dual-Control Preparation</span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>Financial Ledger & Payout Accounting</h1>
          <p className="page-description">
            Manage subscriber ledger obligations, inspect statutory Section 20 deposit reserves, verify arrears, and calculate prize payout claims.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => navigate('/payouts')} className="btn btn-primary">
            <Award size={16} /> Payout Claims Center
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-cols-4">
        <StatCard
          label="Active Chit Circles"
          value={groups.length}
          variant="blue"
          icon={CircleDot}
          trend="Managed Ledgers"
          trendPositive={true}
          helperText="Running subscriber circles"
        />

        <StatCard
          label="Payouts in Preparation"
          value={payouts.length}
          variant="purple"
          icon={Award}
          trend="Dual Control"
          trendPositive={true}
          helperText="Prize claims awaiting verification"
        />

        <StatCard
          label="Statutory Security Deposits"
          value={formatINR(systemSummary?.total_lien_pledged || 100000)}
          variant="emerald"
          icon={Scale}
          trend="Section 20 100% Lien"
          trendPositive={true}
          helperText="Bank FDR pledged with Registrar"
        />

        <StatCard
          label="Outstanding Ledger Arrears"
          value={formatINR(systemSummary?.total_arrears_uncollected || 0)}
          variant="red"
          icon={Clock}
          trend="Uncollected Dues"
          trendPositive={false}
          helperText="Subscribers with overdue installments"
        />
      </div>

      {/* Chit Circles Financial Schedules */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Chit Circles Installment Schedules & Capacity</h3>
            <p className="card-subtitle">Active groups with monthly installment parameters and enrollment quotas</p>
          </div>
          <button onClick={() => navigate('/groups')} className="btn btn-outline btn-sm">
            All Groups
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={groupColumns}
            data={groups}
            emptyTitle="No chit groups found"
            emptyDescription="Active chit groups will appear here once launched."
          />
        </div>
      </div>

      {/* Payout Claims & Arrears Calculations */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Prize Money Payout Calculations & Arrears Offsets</h3>
            <p className="card-subtitle">Dual-control prize disbursements with auto-calculated dividend offsets and surety checks</p>
          </div>
          <button onClick={() => navigate('/payouts')} className="btn btn-outline btn-sm">
            Manage Payouts
          </button>
        </div>
        <div className="card-body">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Prized Member</th>
                  <th>Gross Prize</th>
                  <th>Arrears Deducted</th>
                  <th>Net Disbursed</th>
                  <th>Disbursement Status</th>
                </tr>
              </thead>
              <tbody>
                {payouts.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      No payout claims currently pending preparation.
                    </td>
                  </tr>
                ) : (
                  payouts.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                          {p.winner_name || p.subscriber_name || 'Subscriber'}
                        </span>
                      </td>
                      <td className="font-mono">{formatINR(p.gross_prize_amount)}</td>
                      <td className="font-mono" style={{ color: '#dc2626' }}>
                        {formatINR(p.arrears_deducted || 0)}
                      </td>
                      <td className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-700)' }}>
                        {formatINR(p.net_disbursed_amount)}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            p.disbursement_status === 'DISBURSED'
                              ? 'badge-success'
                              : p.disbursement_status === 'SURETY_APPROVED'
                              ? 'badge-purple'
                              : 'badge-warning'
                          }`}
                        >
                          {p.disbursement_status?.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
