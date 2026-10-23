import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CircleDot,
  Gavel,
  Users,
  ShieldCheck,
  Play,
  Calendar,
  Clock,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  X,
  FileCheck,
  Shield,
  Eye,
} from 'lucide-react'
import StatCard from '../../components/common/StatCard'
import DataTable from '../../components/common/DataTable'
import LoadingState from '../../components/common/LoadingState'
import ErrorState from '../../components/common/ErrorState'
import { groupsApi } from '../../api/groups'
import { auctionsApi } from '../../api/auctions'
import { membersApi } from '../../api/members'
import { payoutsApi } from '../../api/payouts'
import { useAuth } from '../../context/AuthContext'

export default function ManagerDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [assignedGroups, setAssignedGroups] = useState([])
  const [auctions, setAuctions] = useState([])
  const [branchMembers, setBranchMembers] = useState([])
  const [pendingPayouts, setPendingPayouts] = useState([])

  // Surety Inspection modal state
  const [selectedSuretyPayout, setSelectedSuretyPayout] = useState(null)
  const [verifyingSurety, setVerifyingSurety] = useState(false)
  const [suretyRemarks, setSuretyRemarks] = useState('')

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [groupsRes, auctionsRes, membersRes, payoutsRes] = await Promise.allSettled([
        groupsApi.list(),
        auctionsApi.list(),
        membersApi.list(),
        payoutsApi.list(),
      ])

      let gList = []
      if (groupsRes.status === 'fulfilled') {
        gList = groupsRes.value.data?.items || []
        setAssignedGroups(gList)
      }

      let aList = []
      if (auctionsRes.status === 'fulfilled' && Array.isArray(auctionsRes.value?.data)) {
        aList = auctionsRes.value.data
        setAuctions(aList)
      }

      let mList = []
      if (membersRes.status === 'fulfilled') {
        mList = membersRes.value.data?.items || []
        setBranchMembers(mList)
      }

      let pList = []
      if (payoutsRes.status === 'fulfilled' && Array.isArray(payoutsRes.value?.data)) {
        pList = payoutsRes.value.data
        setPendingPayouts(pList.filter((p) => p.disbursement_status === 'PENDING_SURETY'))
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

  const handleStartAuction = async (auctionId) => {
    try {
      await auctionsApi.startAuction(auctionId)
      navigate(`/auctions/${auctionId}`)
    } catch (err) {
      alert('Could not start auction chamber: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleVerifySurety = async (suretyId, approved) => {
    setVerifyingSurety(true)
    try {
      await payoutsApi.verifySurety(suretyId, {
        verification_status: approved ? 'VERIFIED' : 'REJECTED',
        remarks: suretyRemarks || (approved ? 'Surety collateral inspected & approved by Branch Manager' : 'Rejected'),
      })
      setSelectedSuretyPayout(null)
      await loadData()
      alert(approved ? 'Surety verified successfully!' : 'Surety marked as rejected.')
    } catch (err) {
      alert('Verification failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setVerifyingSurety(false)
    }
  }

  const pendingKycs = branchMembers.filter((m) => m.kyc_status === 'PENDING').length
  const activeAuctions = auctions.filter((a) => a.status === 'OPEN')
  const scheduledAuctions = auctions.filter((a) => a.status === 'SCHEDULED')

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  if (loading) return <LoadingState message="Loading Branch Manager circle operations..." />
  if (error) return <ErrorState message={error} onRetry={loadData} />

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-blue">Branch Operations Scope</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Assigned Circles: {assignedGroups.length}
            </span>
          </div>
          <h1 className="page-title" style={{ marginTop: '0.25rem' }}>Branch Operations & Auction Conductor</h1>
          <p className="page-description">
            Supervise assigned chit circles, conduct real-time live reverse auctions, and inspect winning subscriber collateral.
          </p>
        </div>
        <div className="page-actions">
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-cols-4">
        <StatCard
          label="My Assigned Circles"
          value={assignedGroups.length}
          variant="blue"
          icon={CircleDot}
          trend="Active Assignment"
          trendPositive={true}
          helperText="Circles managed by you"
        />

        <StatCard
          label="Live Auction Rounds"
          value={activeAuctions.length}
          variant={activeAuctions.length > 0 ? 'emerald' : 'slate'}
          icon={Gavel}
          trend={activeAuctions.length > 0 ? 'LIVE NOW' : 'No Active Chamber'}
          trendPositive={activeAuctions.length > 0}
          helperText="Chamber open for bidding"
        />

        <StatCard
          label="Pending Surety Reviews"
          value={pendingPayouts.length}
          variant="gold"
          icon={ShieldCheck}
          trend="Prized Winners"
          trendPositive={pendingPayouts.length === 0}
          helperText="Collateral awaiting inspection"
        />

        <StatCard
          label="Subscribers in My Circles"
          value={branchMembers.length}
          variant="emerald"
          icon={Users}
          trend={`${pendingKycs} KYC Pending`}
          trendPositive={pendingKycs === 0}
          helperText="Branch roster"
        />
      </div>

      {/* Live Auction Chamber Fast-Action Card */}
      {activeAuctions.length > 0 && (
        <div
          className="card"
          style={{
            borderLeft: '4px solid var(--emerald-600)',
            background: 'linear-gradient(to right, #ecfdf5, #ffffff)',
            padding: '1.25rem 1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div
                style={{
                  background: 'var(--emerald-600)',
                  color: '#ffffff',
                  padding: '0.625rem',
                  borderRadius: 'var(--radius-full)',
                }}
              >
                <Gavel size={24} />
              </div>
              <div>
                <span className="badge badge-success animate-pulse">AUCTION IN PROGRESS</span>
                <h4 style={{ margin: '4px 0 0 0', fontSize: '1rem', fontWeight: 800, color: 'var(--emerald-950)' }}>
                  Round #{activeAuctions[0].month_number} Live Bidding Chamber is Open
                </h4>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.8125rem', color: 'var(--emerald-800)' }}>
                  Subscribers are submitting reverse discount bids via WebSockets.
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate(`/auctions/${activeAuctions[0].id}`)}
              className="btn btn-primary"
            >
              Enter Live Chamber <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Next Upcoming Auction Schedule & Assigned Circles */}
      <div className="grid-cols-2">
        {/* Auctions Panel */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Auction Schedule (Assigned Circles)</h3>
              <p className="card-subtitle">Scheduled rounds ready for execution</p>
            </div>
            <button onClick={() => navigate('/auctions')} className="btn btn-outline btn-sm">
              All Rounds
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Circle & Month</th>
                    <th>Scheduled Date</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Chamber Action</th>
                  </tr>
                </thead>
                <tbody>
                  {auctions.slice(0, 5).map((a) => (
                    <tr key={a.id}>
                      <td>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                          Month #{a.month_number}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                          <Calendar size={13} />
                          {a.scheduled_at ? new Date(a.scheduled_at).toLocaleDateString() : 'Scheduled'}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${a.status === 'OPEN' ? 'badge-success' : a.status === 'CLOSED' ? 'badge-slate' : 'badge-blue'}`}>
                          {a.status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {a.status === 'SCHEDULED' && (
                          <button
                            onClick={() => handleStartAuction(a.id)}
                            className="btn btn-primary btn-sm"
                          >
                            <Play size={13} /> Start Room
                          </button>
                        )}
                        {a.status === 'OPEN' && (
                          <button
                            onClick={() => navigate(`/auctions/${a.id}`)}
                            className="btn btn-secondary btn-sm"
                          >
                            Join Chamber
                          </button>
                        )}
                        {a.status === 'CLOSED' && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Concluded</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Pending Sureties Queue */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Prized Subscriber Sureties Queue</h3>
              <p className="card-subtitle">Collateral documents awaiting branch inspection</p>
            </div>
            <button onClick={() => navigate('/payouts')} className="btn btn-outline btn-sm">
              All Sureties
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {pendingPayouts.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                <CheckCircle2 size={24} color="var(--emerald-600)" style={{ margin: '0 auto 0.5rem auto' }} />
                All prized subscribers have completed surety collateral verification.
              </div>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Prized Member</th>
                      <th>Gross Prize</th>
                      <th>Sureties</th>
                      <th style={{ textAlign: 'right' }}>Inspection</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingPayouts.map((p) => (
                      <tr key={p.id}>
                        <td>
                          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                            {p.winner_name || 'Prized Member'}
                          </span>
                        </td>
                        <td className="font-mono">{formatINR(p.gross_prize_amount)}</td>
                        <td>
                          <span className="badge badge-warning">
                            {p.sureties?.length || 0} Lodged
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedSuretyPayout(p)}
                            className="btn btn-outline btn-sm"
                          >
                            <FileCheck size={13} /> Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Surety Inspection & Verification Modal */}
      {selectedSuretyPayout && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={20} color="var(--emerald-600)" />
                <h3 className="modal-title">Inspect & Verify Winner Collateral</h3>
              </div>
              <button onClick={() => setSelectedSuretyPayout(null)} className="btn-icon-only">
                <X size={16} />
              </button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '0.875rem', borderRadius: 'var(--radius-md)' }}>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Prized Winner:</div>
                <div style={{ fontSize: '0.9375rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {selectedSuretyPayout.winner_name || 'Subscriber'}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--emerald-700)', fontWeight: 700, marginTop: '2px' }}>
                  Prize Amount: {formatINR(selectedSuretyPayout.gross_prize_amount)}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '0.8125rem', fontWeight: 700, margin: '0 0 0.5rem 0' }}>
                  Submitted Sureties & Collateral:
                </h4>
                {selectedSuretyPayout.sureties && selectedSuretyPayout.sureties.length > 0 ? (
                  selectedSuretyPayout.sureties.map((s) => (
                    <div
                      key={s.id}
                      style={{
                        padding: '0.75rem',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-subtle)',
                        backgroundColor: '#ffffff',
                        marginBottom: '0.5rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.8125rem' }}>{s.surety_type}</span>
                        <span className={`badge ${s.verification_status === 'VERIFIED' ? 'badge-success' : 'badge-warning'}`}>
                          {s.verification_status}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Guarantor: {s.guarantor_name || 'N/A'} • Ref: {s.document_reference || 'N/A'}
                      </div>
                      {s.verification_status === 'PENDING' && (
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                          <button
                            onClick={() => handleVerifySurety(s.id, true)}
                            disabled={verifyingSurety}
                            className="btn btn-primary btn-sm"
                          >
                            Mark Verified
                          </button>
                          <button
                            onClick={() => handleVerifySurety(s.id, false)}
                            disabled={verifyingSurety}
                            className="btn btn-outline btn-sm"
                            style={{ color: '#dc2626', borderColor: '#fecaca' }}
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    No collateral documents submitted yet by subscriber.
                  </p>
                )}
              </div>

              <div>
                <label className="form-label">Inspection Remarks</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Verified original salary slip and guarantor identity in branch."
                  value={suretyRemarks}
                  onChange={(e) => setSuretyRemarks(e.target.value)}
                  className="form-input"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setSelectedSuretyPayout(null)} className="btn btn-outline">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
