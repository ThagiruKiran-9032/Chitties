import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CircleDot,
  Gavel,
  Calendar,
  Clock,
  ArrowRight,
  TrendingUp,
  Award,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Eye,
  X,
  Shield,
  ShieldCheck,
  Upload,
} from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { groupsApi } from '../../api/groups'
import { auctionsApi } from '../../api/auctions'
import { payoutsApi } from '../../api/payouts'
import { useAuth } from '../../context/AuthContext'

export default function SubscriberDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [myGroups, setMyGroups] = useState([])
  const [auctions, setAuctions] = useState([])
  const [myPayouts, setMyPayouts] = useState([])

  // Submit surety modal
  const [showSuretyModal, setShowSuretyModal] = useState(false)
  const [selectedPayoutForSurety, setSelectedPayoutForSurety] = useState(null)
  const [submittingSurety, setSubmittingSurety] = useState(false)
  const [suretyForm, setSuretyForm] = useState({
    surety_type: 'GUARANTOR',
    guarantor_name: '',
    guarantor_phone: '',
    document_reference: '',
    remarks: '',
  })

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [groupsRes, auctionsRes, payoutsRes] = await Promise.allSettled([
        groupsApi.list(),
        auctionsApi.list(),
        payoutsApi.list(),
      ])

      if (groupsRes.status === 'fulfilled') {
        setMyGroups(groupsRes.value.data?.items || [])
      }

      if (auctionsRes.status === 'fulfilled' && Array.isArray(auctionsRes.value?.data)) {
        setAuctions(auctionsRes.value.data)
      }

      if (payoutsRes.status === 'fulfilled' && Array.isArray(payoutsRes.value?.data)) {
        setMyPayouts(payoutsRes.value.data)
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

  const handleSubmitSurety = async (e) => {
    e.preventDefault()
    if (!selectedPayoutForSurety) return
    setSubmittingSurety(true)
    try {
      await payoutsApi.addSurety(selectedPayoutForSurety.id, suretyForm)
      setShowSuretyModal(false)
      setSuretyForm({
        surety_type: 'GUARANTOR',
        guarantor_name: '',
        guarantor_phone: '',
        document_reference: '',
        remarks: '',
      })
      await loadData()
    } catch (err) {
      alert('Failed to submit surety: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingSurety(false)
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  const activeLiveAuction = auctions.find((a) => a.status === 'OPEN')
  const upcomingAuctions = auctions.filter((a) => a.status === 'SCHEDULED')

  const groupColumns = [
    {
      header: 'Group Code',
      accessor: (row) => (
        <div>
          <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-800)' }}>
            {row.group_code}
          </span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            Circle #{row.id.substring(0, 6)}
          </span>
        </div>
      ),
    },
    {
      header: 'My Ticket',
      accessor: (row) => (
        <span className="badge badge-emerald font-mono">
          Ticket #1
        </span>
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
      accessor: (row) => <span className="font-mono">{formatINR(row.total_value || 100000)}</span>,
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
          View Circle
        </button>
      ),
    },
  ]

  const auctionColumns = [
    {
      header: 'Round / Group',
      accessor: (row) => (
        <div>
          <span style={{ fontWeight: 700 }}>Month {row.month_number}</span>
          <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            {row.group_code || 'APEX-GOLD-2026'}
          </span>
        </div>
      ),
    },
    {
      header: 'Scheduled Date',
      accessor: (row) => (
        <span>{row.scheduled_at ? new Date(row.scheduled_at).toLocaleDateString() : '15th of Month'}</span>
      ),
    },
    {
      header: 'Pot Value',
      accessor: (row) => <span className="font-mono">{formatINR(row.total_value || 100000)}</span>,
    },
    {
      header: 'Status',
      accessor: (row) => (
        <span
          className={`badge ${
            row.status === 'OPEN'
              ? 'badge-success animate-pulse'
              : row.status === 'SCHEDULED'
              ? 'badge-blue'
              : 'badge-slate'
          }`}
        >
          {row.status === 'OPEN' ? 'LIVE BIDDING' : row.status}
        </span>
      ),
    },
    {
      header: 'Actions',
      align: 'right',
      render: (row) => (
        <button
          onClick={() => navigate(`/auctions/${row.id}`)}
          className={`btn btn-sm ${row.status === 'OPEN' ? 'btn-primary' : 'btn-outline'}`}
        >
          {row.status === 'OPEN' ? 'Enter Live Room' : 'View Details'}
        </button>
      ),
    },
  ]

  if (loading) return <LoadingState message="Loading Subscriber Portal & Passes..." />
  if (error) return <ErrorState message={error} onRetry={loadData} />

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-emerald">Subscriber Portal</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Ticket Holder #{user?.phone?.slice(-4) || '1'}
            </span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>
            Welcome back, {user?.full_name?.split(' ')[0] || 'Subscriber'}
          </h1>
          <p className="page-description">
            Track your enrolled chit circles, participate in live auction bidding chambers, and manage prize payout claims.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => navigate('/auctions')} className="btn btn-primary">
            <Gavel size={16} /> Auction Chamber
          </button>
        </div>
      </div>

      {/* Live Auction Broadcast Alert (If an auction is open) */}
      {activeLiveAuction && (
        <div
          className="card"
          style={{
            backgroundColor: '#ecfdf5',
            borderColor: '#a7f3d0',
            borderLeft: '5px solid var(--emerald-600)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  background: 'var(--emerald-600)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Gavel size={24} />
              </div>
              <div>
                <span className="badge badge-success animate-pulse">LIVE AUCTION ACTIVE NOW</span>
                <h4 style={{ margin: '4px 0 0 0', fontSize: '1rem', fontWeight: 800, color: 'var(--emerald-950)' }}>
                  Round #{activeLiveAuction.month_number} Reverse Bidding Chamber is Open!
                </h4>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.8125rem', color: 'var(--emerald-800)' }}>
                  Eligible non-prized subscribers can enter the room and place discount bids in real time.
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate(`/auctions/${activeLiveAuction.id}`)}
              className="btn btn-primary"
            >
              Enter Bidding Room <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid-cols-4">
        <StatCard
          label="My Active Tickets"
          value={myGroups.length || 1}
          variant="emerald"
          icon={CircleDot}
          trend="Enrolled"
          trendPositive={true}
          helperText="Enrolled in active circles"
        />

        <StatCard
          label="Upcoming Auctions"
          value={upcomingAuctions.length}
          variant="blue"
          icon={Gavel}
          trend="Next 30 Days"
          trendPositive={true}
          helperText="Rounds scheduled this month"
        />

        <StatCard
          label="My Prize Claims"
          value={myPayouts.length}
          variant="purple"
          icon={Award}
          trend="Prize Workflow"
          trendPositive={true}
          helperText="Prize claims & sureties"
        />

        <StatCard
          label="KYC Verification Status"
          value={user?.kyc_status || 'VERIFIED'}
          variant="gold"
          icon={ShieldCheck}
          trend="Govt ID On File"
          trendPositive={user?.kyc_status === 'VERIFIED'}
          helperText="Aadhaar / PAN identity"
        />
      </div>

      {/* Prize Payout Claims & Sureties Section (If Prized) */}
      {myPayouts.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Award size={18} color="var(--emerald-600)" />
                <h3 className="card-title">My Prize Money Payout Workflow</h3>
                <span className="badge badge-success">AUCTION PRIZE CLAIM</span>
              </div>
              <p className="card-subtitle">
                Track collateral surety verification and bank disbursement for your won auction round.
              </p>
            </div>
          </div>
          <div className="card-body">
            {myPayouts.map((payout) => (
              <div
                key={payout.id}
                style={{
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-subtle)',
                  border: '1px solid var(--border-subtle)',
                  marginBottom: '1rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Gross Prize Amount:</span>
                    <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--emerald-700)' }}>
                      {formatINR(payout.gross_prize_amount)}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Workflow Status:</span>
                    <div>
                      <span className={`badge ${payout.disbursement_status === 'DISBURSED' ? 'badge-success' : 'badge-warning'}`}>
                        {payout.disbursement_status?.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  <div>
                    {payout.disbursement_status === 'PENDING_SURETY' && (
                      <button
                        onClick={() => {
                          setSelectedPayoutForSurety(payout)
                          setShowSuretyModal(true)
                        }}
                        className="btn btn-primary btn-sm"
                      >
                        <Upload size={14} /> Submit Sureties / Guarantor
                      </button>
                    )}
                    {payout.disbursement_status === 'SURETY_APPROVED' && (
                      <span style={{ fontSize: '0.8125rem', color: 'var(--emerald-800)', fontWeight: 600 }}>
                        <CheckCircle2 size={15} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
                        Sureties Approved • Awaiting Admin Dual-Control Sign-Off
                      </span>
                    )}
                    {payout.disbursement_status === 'DISBURSED' && (
                      <span style={{ fontSize: '0.8125rem', color: 'var(--emerald-700)', fontWeight: 700 }}>
                        Funds Disbursed to Bank Account (Ref: {payout.disbursement_reference || 'NEFT'})
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Enrolled Chit Circles Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">My Enrolled Chit Circles</h3>
            <p className="card-subtitle">Circles where you hold active subscriber ticket memberships</p>
          </div>
          <button onClick={() => navigate('/groups')} className="btn btn-outline btn-sm">
            View All Circles
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={groupColumns}
            data={myGroups}
            emptyTitle="No chit groups found"
            emptyDescription="You are not currently enrolled in any active circles."
          />
        </div>
      </div>

      {/* Upcoming Auctions Schedule Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Upcoming & Recent Auctions</h3>
            <p className="card-subtitle">Schedule of reverse discount auctions across your enrolled circles</p>
          </div>
          <button onClick={() => navigate('/auctions')} className="btn btn-outline btn-sm">
            Auctions Chamber
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <DataTable
            columns={auctionColumns}
            data={auctions}
            emptyTitle="No auctions scheduled"
            emptyDescription="Upcoming auction rounds will appear here once scheduled."
          />
        </div>
      </div>

      {/* Submit Sureties Modal */}
      {showSuretyModal && selectedPayoutForSurety && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Shield size={20} color="var(--emerald-600)" />
                <h3 className="modal-title">Submit Prize Money Sureties</h3>
              </div>
              <button onClick={() => setShowSuretyModal(false)} className="btn-icon-only">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleSubmitSurety}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label className="form-label">Collateral / Surety Type *</label>
                  <select
                    value={suretyForm.surety_type}
                    onChange={(e) => setSuretyForm({ ...suretyForm, surety_type: e.target.value })}
                    className="form-input"
                  >
                    <option value="GUARANTOR">Personal Guarantor</option>
                    <option value="SALARY_CERTIFICATE">Salary Certificate</option>
                    <option value="PROPERTY_COLLATERAL">Property Mortgage / Title Deed</option>
                    <option value="FIXED_DEPOSIT">Fixed Deposit Receipt Lien</option>
                  </select>
                </div>

                <div>
                  <label className="form-label">Guarantor Legal Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ramesh Chandra"
                    value={suretyForm.guarantor_name}
                    onChange={(e) => setSuretyForm({ ...suretyForm, guarantor_name: e.target.value })}
                    className="form-input"
                  />
                </div>

                <div>
                  <label className="form-label">Guarantor Contact Phone *</label>
                  <input
                    type="text"
                    required
                    placeholder="+919876543210"
                    value={suretyForm.guarantor_phone}
                    onChange={(e) => setSuretyForm({ ...suretyForm, guarantor_phone: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>

                <div>
                  <label className="form-label">Document Reference Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. EMP-ID-781920 or DEED-REG-2026"
                    value={suretyForm.document_reference}
                    onChange={(e) => setSuretyForm({ ...suretyForm, document_reference: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>

                <div>
                  <label className="form-label">Remarks / Description</label>
                  <input
                    type="text"
                    placeholder="e.g. Salary certificate from PSU / MNC uploaded"
                    value={suretyForm.remarks}
                    onChange={(e) => setSuretyForm({ ...suretyForm, remarks: e.target.value })}
                    className="form-input"
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowSuretyModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button type="submit" disabled={submittingSurety} className="btn btn-primary">
                  {submittingSurety ? 'Submitting...' : 'Submit Surety Documents'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
