import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Users,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Play,
  Gavel,
  Clock,
  ArrowRight,
  TrendingUp,
  Receipt,
  CreditCard,
  AlertTriangle,
  X,
  UserCheck,
  CircleDot
} from 'lucide-react'
import { groupsApi } from '../api/groups'
import { membersApi } from '../api/members'
import { auctionsApi } from '../api/auctions'
import { installmentsApi } from '../api/installments'

export default function GroupDetailPage({ groupId: propGroupId, onBack: propOnBack, onSelectAuction: propOnSelectAuction }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const effectiveGroupId = propGroupId || id

  const [group, setGroup] = useState(null)
  const [memberships, setMemberships] = useState([])
  const [verifiedMembers, setVerifiedMembers] = useState([])
  const [groupAuctions, setGroupAuctions] = useState([])
  const [groupInstallments, setGroupInstallments] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeSubTab, setActiveSubTab] = useState('tickets') // 'tickets' | 'auctions' | 'dues'

  // Enrollment Modal state
  const [showEnrollModal, setShowEnrollModal] = useState(false)
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [enrolling, setEnrolling] = useState(false)

  // Penalty Modal state
  const [showPenaltyModal, setShowPenaltyModal] = useState(false)
  const [penaltyAmount, setPenaltyAmount] = useState('500')
  const [penaltyReason, setPenaltyReason] = useState('Overdue late payment fee')
  const [submittingPenalty, setSubmittingPenalty] = useState(false)

  const fetchGroupDetails = async () => {
    setLoading(true)
    try {
      const [gRes, mRes, verifiedRes, aRes, iRes] = await Promise.all([
        groupsApi.get(effectiveGroupId),
        groupsApi.getMemberships(effectiveGroupId),
        membersApi.list({ kyc_status: 'VERIFIED', size: 100 }),
        auctionsApi.getGroupAuctions(effectiveGroupId).catch(() => ({ data: [] })),
        installmentsApi.getGroupInstallments(effectiveGroupId).catch(() => ({ data: [] })),
      ])
      setGroup(gRes.data)
      setMemberships(mRes.data || [])
      setVerifiedMembers(verifiedRes.data?.items || [])
      setGroupAuctions(aRes.data || [])
      setGroupInstallments(iRes.data || [])
    } catch (err) {
      console.error('Failed to load group details:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (effectiveGroupId) fetchGroupDetails()
  }, [effectiveGroupId])

  const handleBack = () => {
    if (propOnBack) {
      propOnBack()
    } else {
      navigate('/groups')
    }
  }

  const handleEnroll = async (e) => {
    e.preventDefault()
    setEnrolling(true)
    try {
      await groupsApi.enroll(effectiveGroupId, {
        user_id: selectedUserId,
        ticket_number: selectedTicket,
      })
      setShowEnrollModal(false)
      setSelectedUserId('')
      fetchGroupDetails()
    } catch (err) {
      alert('Enrollment failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setEnrolling(false)
    }
  }

  const handleRemoveMember = async (membershipId) => {
    if (!window.confirm('Are you sure you want to remove this subscriber from the ticket?')) return
    try {
      await groupsApi.removeMember(effectiveGroupId, membershipId)
      fetchGroupDetails()
    } catch (err) {
      alert('Failed to remove subscriber: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleStatusChange = async (newStatus) => {
    try {
      await groupsApi.updateStatus(effectiveGroupId, newStatus)
      fetchGroupDetails()
    } catch (err) {
      alert('Status transition failed: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleStartAuction = async (auctionId) => {
    try {
      await auctionsApi.startAuction(auctionId)
      fetchGroupDetails()
      if (propOnSelectAuction) {
        propOnSelectAuction(auctionId)
      } else {
        navigate(`/auctions/${auctionId}`)
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start auction round.')
    }
  }

  const openPenaltyModal = (inst) => {
    setSelectedInstallment(inst)
    setPenaltyAmount('500')
    setPenaltyReason('Overdue late fee')
    setShowPenaltyModal(true)
  }

  const handleApplyPenalty = async (e) => {
    e.preventDefault()
    if (!selectedInstallment) return
    setSubmittingPenalty(true)
    try {
      await installmentsApi.applyPenalty(selectedInstallment.id, {
        penalty_amount: Number(penaltyAmount),
        reason: penaltyReason,
      })
      setShowPenaltyModal(false)
      fetchGroupDetails()
    } catch (err) {
      alert('Penalty application failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingPenalty(false)
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  if (loading || !group) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading chit circle details and ledger...
        </div>
      </div>
    )
  }

  const ticketMap = {}
  memberships.forEach((m) => {
    ticketMap[m.ticket_number] = m
  })

  const tickets = []
  for (let i = 1; i <= group.total_capacity; i++) {
    tickets.push({
      number: i,
      membership: ticketMap[i] || null,
    })
  }

  const isFull = group.enrolled_count === group.total_capacity

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

  return (
    <div className="space-y-6">
      {/* Top Navigation & Status */}
      <div className="card">
        <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={handleBack}
              className="btn btn-outline btn-sm"
              title="Return to circles list"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }} className="font-mono text-emerald-700">
                  {group.group_code}
                </h1>
                {getStatusBadge(group.status)}
              </div>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Capacity: <strong>{group.enrolled_count} / {group.total_capacity}</strong> Tickets Allocated &bull; Starts {group.start_date}
              </p>
            </div>
          </div>

          {/* Lifecycle Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {group.status === 'DRAFT' && (
              <button
                onClick={() => handleStatusChange('ENROLLING')}
                className="btn btn-primary"
              >
                Open for Enrollment
              </button>
            )}
            {group.status === 'ENROLLING' && (
              <button
                disabled={!isFull}
                onClick={() => handleStatusChange('ACTIVE')}
                className={`btn ${isFull ? 'btn-primary' : 'btn-outline'}`}
                style={!isFull ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
              >
                <Play className="w-4 h-4" /> Activate Group & Initialize Dues
              </button>
            )}
          </div>
        </div>
      </div>

      {!isFull && group.status === 'ENROLLING' && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, padding: '0.875rem 1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8125rem', color: '#92400e' }}>
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-amber-500" />
          <span>
            Circle activation requires all <strong>{group.total_capacity}</strong> tickets to be allocated ({group.total_capacity - group.enrolled_count} tickets remaining).
          </span>
        </div>
      )}

      {/* Subtab Switcher */}
      <div className="tabs">
        <button
          onClick={() => setActiveSubTab('tickets')}
          className={`tab-item ${activeSubTab === 'tickets' ? 'active' : ''}`}
        >
          <Users className="w-4 h-4" />
          <span>Tickets ({group.enrolled_count}/{group.total_capacity})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('auctions')}
          className={`tab-item ${activeSubTab === 'auctions' ? 'active' : ''}`}
        >
          <Gavel className="w-4 h-4" />
          <span>Auctions ({groupAuctions.length} Rounds)</span>
        </button>
        <button
          onClick={() => setActiveSubTab('dues')}
          className={`tab-item ${activeSubTab === 'dues' ? 'active' : ''}`}
        >
          <Receipt className="w-4 h-4" />
          <span>Installment Dues ({groupInstallments.length})</span>
        </button>
      </div>

      {/* Subtab 1: Ticket Allocation Grid */}
      {activeSubTab === 'tickets' && (
        <div className="space-y-4">
          <div className="grid-cols-4">
            {tickets.map((t) => {
              const isAssigned = !!t.membership
              return (
                <div
                  key={t.number}
                  className="card"
                  style={{
                    border: isAssigned ? '1px solid var(--emerald-200)' : '1px dashed var(--border-medium)',
                    background: isAssigned ? 'var(--bg-card)' : 'var(--bg-subtle)',
                  }}
                >
                  <div className="card-body" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '140px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <span className="font-mono" style={{ fontWeight: 800, fontSize: '1.125rem', color: isAssigned ? 'var(--emerald-700)' : 'var(--text-muted)' }}>
                        Ticket #{t.number}
                      </span>
                      {isAssigned ? (
                        <span className="badge badge-emerald">Assigned</span>
                      ) : (
                        <span className="badge badge-amber">Open</span>
                      )}
                    </div>

                    {isAssigned ? (
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                          {t.membership.user?.full_name || 'Subscriber'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {t.membership.user?.phone || t.membership.user?.email || 'N/A'}
                        </div>
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
                        Vacant slot available for subscriber enrollment.
                      </p>
                    )}

                    <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.625rem', display: 'flex', justifyContent: 'flex-end' }}>
                      {isAssigned ? (
                        group.status !== 'ACTIVE' && group.status !== 'COMPLETED' ? (
                          <button
                            onClick={() => handleRemoveMember(t.membership.id)}
                            className="btn btn-outline btn-sm"
                            style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                            title="Remove subscriber"
                          >
                            <Trash2 className="w-3.5 h-3.5" /> Remove
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--emerald-600)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <CheckCircle2 className="w-3.5 h-3.5" /> Enrolled
                          </span>
                        )
                      ) : (
                        group.status === 'ENROLLING' || group.status === 'DRAFT' ? (
                          <button
                            onClick={() => {
                              setSelectedTicket(t.number)
                              setShowEnrollModal(true)
                            }}
                            className="btn btn-primary btn-sm"
                          >
                            <Plus className="w-3.5 h-3.5" /> Assign
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Locked</span>
                        )
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Subtab 2: Auction Rounds */}
      {activeSubTab === 'auctions' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Auction Schedule & History</h3>
              <p className="card-subtitle">Monthly bidding rounds under 5%-40% discount regulations</p>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Round</th>
                    <th>Date & Time</th>
                    <th>Status</th>
                    <th>Prized Ticket</th>
                    <th>Discount</th>
                    <th>Net Payout</th>
                    <th style={{ textAlign: 'right' }}>Chamber</th>
                  </tr>
                </thead>
                <tbody>
                  {groupAuctions.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                        No auction rounds scheduled yet. Group activation automatically generates rounds.
                      </td>
                    </tr>
                  ) : (
                    groupAuctions.map((auc) => (
                      <tr key={auc.id}>
                        <td className="font-mono" style={{ fontWeight: 700 }}>
                          Round #{auc.round_number}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8125rem' }}>
                            <Clock className="w-3.5 h-3.5 text-muted" />
                            {new Date(auc.scheduled_date).toLocaleString()}
                          </div>
                        </td>
                        <td>
                          {auc.status === 'SCHEDULED' && <span className="badge badge-blue">Scheduled</span>}
                          {auc.status === 'IN_PROGRESS' && <span className="badge badge-emerald">Live Now</span>}
                          {auc.status === 'COMPLETED' && <span className="badge badge-slate">Completed</span>}
                        </td>
                        <td>
                          {auc.winning_ticket_number ? (
                            <span className="font-mono" style={{ fontWeight: 600, color: 'var(--emerald-700)' }}>
                              Ticket #{auc.winning_ticket_number}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>Pending</span>
                          )}
                        </td>
                        <td className="font-mono">{formatINR(auc.winning_bid_amount || 0)}</td>
                        <td className="font-mono font-medium" style={{ color: 'var(--emerald-700)' }}>
                          {formatINR(auc.prize_amount || 0)}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {auc.status === 'SCHEDULED' && (
                            <button
                              onClick={() => handleStartAuction(auc.id)}
                              className="btn btn-primary btn-sm"
                            >
                              <Play className="w-3.5 h-3.5" /> Start Auction
                            </button>
                          )}
                          {auc.status === 'IN_PROGRESS' && (
                            <button
                              onClick={() => {
                                if (propOnSelectAuction) propOnSelectAuction(auc.id)
                                else navigate(`/auctions/${auc.id}`)
                              }}
                              className="btn btn-primary btn-sm"
                            >
                              Enter Chamber <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {auc.status === 'COMPLETED' && (
                            <button
                              onClick={() => {
                                if (propOnSelectAuction) propOnSelectAuction(auc.id)
                                else navigate(`/auctions/${auc.id}`)
                              }}
                              className="btn btn-outline btn-sm"
                            >
                              View Results
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Subtab 3: Installment Ledger */}
      {activeSubTab === 'dues' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Subscriber Installment Ledger</h3>
              <p className="card-subtitle">Monthly dues, dividend adjustments, penalties, and payment collection</p>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Subscriber / Ticket</th>
                    <th>Month</th>
                    <th>Due Date</th>
                    <th>Net Payable</th>
                    <th>Paid</th>
                    <th>Remaining</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groupInstallments.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                        No installment records generated yet. Active groups generate installments upon activation.
                      </td>
                    </tr>
                  ) : (
                    groupInstallments.map((inst) => {
                      const isPaid = inst.status === 'PAID'
                      return (
                        <tr key={inst.id}>
                          <td>
                            <div>
                              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                                {inst.user?.full_name || 'Subscriber'}
                              </div>
                              <span className="font-mono text-muted" style={{ fontSize: '0.75rem' }}>
                                Ticket #{inst.chit_membership?.ticket_number || 'N/A'}
                              </span>
                            </div>
                          </td>
                          <td className="font-mono font-medium">#{inst.month_number}</td>
                          <td style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{inst.due_date}</td>
                          <td className="font-mono">{formatINR(inst.net_payable_amount)}</td>
                          <td className="font-mono font-medium" style={{ color: 'var(--emerald-700)' }}>
                            {formatINR(inst.paid_amount)}
                          </td>
                          <td className="font-mono" style={{ color: inst.remaining_balance > 0 ? '#dc2626' : 'var(--text-muted)' }}>
                            {formatINR(inst.remaining_balance)}
                          </td>
                          <td>
                            {isPaid ? (
                              <span className="badge badge-emerald">Paid</span>
                            ) : inst.status === 'OVERDUE' ? (
                              <span className="badge badge-red">Overdue</span>
                            ) : (
                              <span className="badge badge-amber">Pending</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            {!isPaid && (
                              <button
                                onClick={() => openPenaltyModal(inst)}
                                className="btn btn-outline btn-sm"
                                title="Add late penalty"
                              >
                                Penalty
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Enroll Member into Ticket */}
      {showEnrollModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Assign Ticket #{selectedTicket}</h3>
              </div>
              <button onClick={() => setShowEnrollModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleEnroll}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  Assigning ticket #{selectedTicket} in circle <strong>{group.group_code}</strong>. Only KYC-verified subscribers are eligible.
                </p>

                <div className="form-group">
                  <label className="form-label">Select Verified Subscriber *</label>
                  <select
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(e.target.value)}
                    className="form-select"
                    required
                  >
                    <option value="">Choose a member...</option>
                    {verifiedMembers.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.full_name} ({m.phone || m.email})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowEnrollModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={enrolling || !selectedUserId}
                >
                  {enrolling ? 'Enrolling...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Late Penalty */}
      {showPenaltyModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                <h3 className="modal-title">Apply Overdue Penalty</h3>
              </div>
              <button onClick={() => setShowPenaltyModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleApplyPenalty}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Penalty Amount (INR) *</label>
                  <input
                    type="number"
                    value={penaltyAmount}
                    onChange={(e) => setPenaltyAmount(e.target.value)}
                    className="form-input font-mono"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Reason *</label>
                  <input
                    type="text"
                    value={penaltyReason}
                    onChange={(e) => setPenaltyReason(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowPenaltyModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={submittingPenalty}
                >
                  {submittingPenalty ? 'Applying...' : 'Apply Penalty'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
