import React, { useState, useEffect } from 'react'
import {
  Award,
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  UserCheck,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  X,
  Plus,
  Send,
  Lock,
} from 'lucide-react'
import { payoutsApi } from '../api/payouts'
import { useAuth } from '../context/AuthContext'

export default function PayoutsPage() {
  const { user } = useAuth()
  const [payouts, setPayouts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [selectedPayout, setSelectedPayout] = useState(null)

  // Surety Form state
  const [showAddSurety, setShowAddSurety] = useState(false)
  const [suretyType, setSuretyType] = useState('SALARY_CERTIFICATE')
  const [guarantorName, setGuarantorName] = useState('')
  const [guarantorPhone, setGuarantorPhone] = useState('')
  const [docRef, setDocRef] = useState('')
  const [suretyRemarks, setSuretyRemarks] = useState('')
  const [submittingSurety, setSubmittingSurety] = useState(false)

  // Disbursement Form state
  const [disburseRef, setDisburseRef] = useState('')
  const [docCharges, setDocCharges] = useState('500')
  const [autoClearArrears, setAutoClearArrears] = useState(true)
  const [submittingDisburse, setSubmittingDisburse] = useState(false)

  const isStaff = user?.role && ['SUPER_ADMIN', 'ORG_ADMIN', 'BRANCH_MANAGER'].includes(user.role)

  const fetchPayouts = async () => {
    try {
      setLoading(true)
      const params = filterStatus === 'ALL' ? {} : { status: filterStatus }
      const res = await payoutsApi.list(params)
      setPayouts(res.data || [])
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load prize payouts.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPayouts()
  }, [filterStatus])

  const handleOpenDetail = (p) => {
    setSelectedPayout(p)
    setShowAddSurety(false)
    setDisburseRef(`NEFT-${Date.now().toString().slice(-6)}`)
  }

  const handleAddSurety = async (e) => {
    e.preventDefault()
    if (!selectedPayout) return
    setSubmittingSurety(true)
    try {
      await payoutsApi.addSurety(selectedPayout.id, {
        surety_type: suretyType,
        guarantor_name: guarantorName,
        guarantor_phone: guarantorPhone,
        document_reference: docRef,
        remarks: suretyRemarks,
      })
      setShowAddSurety(false)
      setGuarantorName('')
      setGuarantorPhone('')
      setDocRef('')
      setSuretyRemarks('')
      // Refresh
      const updated = await payoutsApi.list()
      setPayouts(updated.data || [])
      const current = updated.data?.find((x) => x.id === selectedPayout.id)
      if (current) setSelectedPayout(current)
    } catch (err) {
      alert('Failed to add surety: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingSurety(false)
    }
  }

  const handleVerifySurety = async (suretyId, status) => {
    try {
      await payoutsApi.verifySurety(suretyId, {
        verification_status: status,
        remarks: status === 'VERIFIED' ? 'Authenticated and confirmed.' : 'Inadequate coverage.',
      })
      // Refresh
      const updated = await payoutsApi.list()
      setPayouts(updated.data || [])
      const current = updated.data?.find((x) => x.id === selectedPayout.id)
      if (current) setSelectedPayout(current)
    } catch (err) {
      alert('Verification failed: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDisburse = async (e) => {
    e.preventDefault()
    if (!selectedPayout) return
    setSubmittingDisburse(true)
    try {
      await payoutsApi.disburse(selectedPayout.id, {
        disbursement_reference: disburseRef,
        foreman_charges_deducted: Number(docCharges),
        auto_clear_arrears: autoClearArrears,
      })
      // Refresh
      const updated = await payoutsApi.list()
      setPayouts(updated.data || [])
      const current = updated.data?.find((x) => x.id === selectedPayout.id)
      if (current) setSelectedPayout(current)
    } catch (err) {
      alert('Disbursement failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingDisburse(false)
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Prize Money Payouts & Sureties
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Two-step disbursement pipeline: Collateral & Guarantor verification followed by arrears deduction and fund release.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchPayouts}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-medium border border-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Claims
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {['ALL', 'PENDING_SURETY', 'SURETY_APPROVED', 'DISBURSED'].map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              filterStatus === status
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {status === 'ALL'
              ? 'All Claims'
              : status === 'PENDING_SURETY'
              ? 'Awaiting Surety'
              : status === 'SURETY_APPROVED'
              ? 'Ready for Disbursement'
              : 'Disbursed'}
          </button>
        ))}
      </div>

      {/* Claims Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
          <p className="text-xs font-medium">Scanning prize claims...</p>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-950/20 text-red-400 text-xs border border-red-800/40">
          {error}
        </div>
      ) : payouts.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 space-y-3">
          <Award className="w-10 h-10 text-slate-600 mx-auto stroke-1" />
          <h3 className="text-sm font-semibold text-slate-300">No prize claims found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Once an auction round is concluded and a winner is determined, their prize payout claim will appear here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {payouts.map((p) => {
            const isApproved = p.disbursement_status === 'SURETY_APPROVED'
            const isDisbursed = p.disbursement_status === 'DISBURSED'

            return (
              <div
                key={p.id}
                className={`rounded-2xl border p-5 flex flex-col justify-between transition-all ${
                  isApproved
                    ? 'bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 border-indigo-500/40 shadow-lg'
                    : isDisbursed
                    ? 'bg-slate-900/60 border-slate-800'
                    : 'bg-slate-900/90 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded">
                      {p.group_code} • Round #{p.round_number}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        isDisbursed
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : isApproved
                          ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse'
                          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {p.disbursement_status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="mt-4 space-y-2">
                    <div className="flex justify-between items-baseline">
                      <span className="text-xs text-slate-400">Prized Winner:</span>
                      <span className="font-bold text-slate-200">
                        #{p.ticket_number} - {p.subscriber_name}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Gross Prize:</span>
                        <span className="font-mono text-white font-bold">
                          ₹{Number(p.gross_prize_amount).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs text-rose-400">
                        <span>Unpaid Arrears:</span>
                        <span className="font-mono">
                          {Number(p.unpaid_installments_amount) > 0
                            ? `-₹${Number(p.unpaid_installments_amount).toLocaleString('en-IN')}`
                            : '₹0'}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs pt-1 border-t border-slate-800 font-bold">
                        <span className="text-slate-300">Est. Net Disbursed:</span>
                        <span className="font-mono text-emerald-400">
                          ₹{Number(p.gross_prize_amount - p.unpaid_installments_amount).toLocaleString('en-IN')}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pt-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                      <span>{p.sureties.length} Surety Documents Registered</span>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-800/60">
                  <button
                    onClick={() => handleOpenDetail(p)}
                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center justify-center gap-1.5"
                  >
                    <span>Manage Claim & Sureties</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Payout & Surety Modal */}
      {selectedPayout && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-6 shadow-2xl relative my-8 text-slate-200">
            <button
              onClick={() => setSelectedPayout(null)}
              className="absolute right-5 top-5 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Header */}
            <div className="border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded">
                  {selectedPayout.group_code} • Round #{selectedPayout.round_number}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full font-bold uppercase bg-slate-800 text-slate-300">
                  {selectedPayout.disbursement_status.replace('_', ' ')}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white mt-1">
                Prize Money Claim: Ticket #{selectedPayout.ticket_number} ({selectedPayout.subscriber_name})
              </h2>
            </div>

            {/* Financial Ledger Breakdown */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/70 p-4 rounded-2xl border border-slate-800">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold">Gross Prize</span>
                <p className="text-base font-extrabold text-white font-mono mt-0.5">
                  ₹{Number(selectedPayout.gross_prize_amount).toLocaleString('en-IN')}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold">Ticket Arrears</span>
                <p className="text-base font-bold text-rose-400 font-mono mt-0.5">
                  ₹{Number(selectedPayout.arrears_deducted || selectedPayout.unpaid_installments_amount).toLocaleString('en-IN')}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold">Doc Charges</span>
                <p className="text-base font-bold text-slate-300 font-mono mt-0.5">
                  ₹{Number(selectedPayout.foreman_charges_deducted).toLocaleString('en-IN')}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold">Net Disbursed</span>
                <p className="text-base font-extrabold text-emerald-400 font-mono mt-0.5">
                  ₹{Number(selectedPayout.net_disbursed_amount).toLocaleString('en-IN')}
                </p>
              </div>
            </div>

            {/* Surety Collateral Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  Submitted Sureties ({selectedPayout.sureties.length})
                </h3>
                {selectedPayout.disbursement_status !== 'DISBURSED' && (
                  <button
                    onClick={() => setShowAddSurety(!showAddSurety)}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                  >
                    <Plus className="w-3.5 h-3.5" /> {showAddSurety ? 'Cancel' : 'Add Surety'}
                  </button>
                )}
              </div>

              {/* Add Surety Form */}
              {showAddSurety && (
                <form onSubmit={handleAddSurety} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-slate-400 mb-1">Surety Type</label>
                      <select
                        value={suretyType}
                        onChange={(e) => setSuretyType(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="SALARY_CERTIFICATE">Salary Certificate / Pay Slips</option>
                        <option value="GUARANTOR">Personal Guarantor</option>
                        <option value="PROPERTY_COLLATERAL">Property Mortgage / Title Deed</option>
                        <option value="FIXED_DEPOSIT">Fixed Deposit Lien</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Guarantor Name</label>
                      <input
                        type="text"
                        value={guarantorName}
                        onChange={(e) => setGuarantorName(e.target.value)}
                        placeholder="e.g. Suresh Raina"
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-slate-400 mb-1">Guarantor Phone</label>
                      <input
                        type="text"
                        value={guarantorPhone}
                        onChange={(e) => setGuarantorPhone(e.target.value)}
                        placeholder="+91..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Document Reference / ID</label>
                      <input
                        type="text"
                        required
                        value={docRef}
                        onChange={(e) => setDocRef(e.target.value)}
                        placeholder="Deed / ID / Certificate Number"
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Valuation / Remarks</label>
                    <input
                      type="text"
                      value={suretyRemarks}
                      onChange={(e) => setSuretyRemarks(e.target.value)}
                      placeholder="e.g. Monthly salary ₹75,000, 5 years service"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submittingSurety}
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold"
                  >
                    {submittingSurety ? 'Registering...' : 'Lodge Surety Document'}
                  </button>
                </form>
              )}

              {/* Sureties List */}
              <div className="space-y-2">
                {selectedPayout.sureties.length === 0 ? (
                  <p className="text-xs text-slate-500 italic p-3 text-center bg-slate-950/40 rounded-xl">
                    No sureties submitted yet. Prized subscriber must provide collateral before funds can be released.
                  </p>
                ) : (
                  selectedPayout.sureties.map((s) => (
                    <div
                      key={s.id}
                      className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{s.surety_type.replace('_', ' ')}</span>
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              s.verification_status === 'VERIFIED'
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : s.verification_status === 'REJECTED'
                                ? 'bg-rose-500/20 text-rose-400'
                                : 'bg-amber-500/20 text-amber-400'
                            }`}
                          >
                            {s.verification_status}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Ref: <span className="font-mono text-slate-300">{s.document_reference}</span>
                          {s.guarantor_name && ` • Guarantor: ${s.guarantor_name}`}
                        </p>
                        {s.remarks && <p className="text-[10px] text-slate-500 mt-0.5">{s.remarks}</p>}
                      </div>

                      {isStaff && s.verification_status === 'PENDING' && (
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleVerifySurety(s.id, 'VERIFIED')}
                            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-[11px]"
                          >
                            Verify
                          </button>
                          <button
                            onClick={() => handleVerifySurety(s.id, 'REJECTED')}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-rose-950/40 text-rose-400 font-bold rounded-lg text-[11px]"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Disbursement Section */}
            {selectedPayout.disbursement_status === 'DISBURSED' ? (
              <div className="p-4 bg-emerald-950/30 border border-emerald-500/40 rounded-2xl flex items-center gap-3 text-xs text-emerald-300">
                <CheckCircle2 className="w-6 h-6 flex-shrink-0 text-emerald-400" />
                <div>
                  <p className="font-bold text-sm text-emerald-200">Prize Money Disbursed</p>
                  <p className="text-[11px] text-emerald-400/90 mt-0.5">
                    Reference: <span className="font-mono font-bold">{selectedPayout.disbursement_reference}</span> &bull; Disbursed on{' '}
                    {new Date(selectedPayout.disbursed_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ) : isStaff && (
              <div className="border-t border-slate-800 pt-4 space-y-3">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-400" /> Authorize & Release Funds
                </h3>

                {selectedPayout.disbursement_status !== 'SURETY_APPROVED' ? (
                  <div className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-xl text-amber-300 text-xs flex items-center gap-2">
                    <Lock className="w-4 h-4 text-amber-400" />
                    <span>Disbursement is locked until all submitted sureties are authenticated and verified.</span>
                  </div>
                ) : (
                  <form onSubmit={handleDisburse} className="space-y-3 bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-400 mb-1 font-semibold">Bank UTR / Cheque Ref</label>
                        <input
                          type="text"
                          required
                          value={disburseRef}
                          onChange={(e) => setDisburseRef(e.target.value)}
                          placeholder="e.g. NEFT-UTR-990088"
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1 font-semibold">Documentation Charges (₹)</label>
                        <input
                          type="number"
                          step="10"
                          value={docCharges}
                          onChange={(e) => setDocCharges(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="checkbox"
                        id="autoArrears"
                        checked={autoClearArrears}
                        onChange={(e) => setAutoClearArrears(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-800 text-emerald-600 focus:ring-0"
                      />
                      <label htmlFor="autoArrears" className="text-slate-300 font-medium">
                        Automatically deduct ticket arrears (₹{Number(selectedPayout.unpaid_installments_amount).toLocaleString('en-IN')}) and mark installments as PAID
                      </label>
                    </div>

                    <button
                      type="submit"
                      disabled={submittingDisburse}
                      className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold transition flex items-center justify-center gap-2 mt-2"
                    >
                      {submittingDisburse ? 'Disbursing...' : 'Confirm & Disburse Prize Funds'}
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
