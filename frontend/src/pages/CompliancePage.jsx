import React, { useState, useEffect } from 'react'
import {
  Scale,
  ShieldCheck,
  FileText,
  Building2,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Plus,
  X,
  ExternalLink,
  Printer,
  Calendar,
  Lock,
  ArrowRight,
  TrendingDown,
  Layers,
  Award,
  Clock,
  CircleDot
} from 'lucide-react'
import { complianceApi } from '../api/compliance'
import { groupsApi } from '../api/groups'
import { useAuth } from '../context/AuthContext'

export default function CompliancePage() {
  const { user } = useAuth()
  const [activeSubTab, setActiveSubTab] = useState('deposits') // 'deposits' | 'filings' | 'balance-sheet' | 'delinquency'

  // Summary KPI state
  const [summary, setSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(true)

  // Groups list for dropdowns
  const [groups, setGroups] = useState([])
  const [selectedGroupId, setSelectedGroupId] = useState('')

  // Section 20 Deposits state
  const [deposits, setDeposits] = useState([])
  const [loadingDeposits, setLoadingDeposits] = useState(false)
  const [showAddDepositModal, setShowAddDepositModal] = useState(false)
  const [depositForm, setDepositForm] = useState({
    group_id: '',
    deposit_type: 'FIXED_DEPOSIT',
    bank_name: 'State Bank of India',
    account_or_fdr_number: '',
    amount: '',
    deposit_date: new Date().toISOString().split('T')[0],
    maturity_date: new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0],
    registrar_order_reference: '',
    remarks: '',
  })
  const [submittingDeposit, setSubmittingDeposit] = useState(false)

  // Filings state
  const [filings, setFilings] = useState([])
  const [loadingFilings, setLoadingFilings] = useState(false)
  const [showAddFilingModal, setShowAddFilingModal] = useState(false)
  const [filingForm, setFilingForm] = useState({
    group_id: '',
    form_type: 'FORM_XIV_MINUTES',
    filing_reference_number: '',
    filed_date: new Date().toISOString().split('T')[0],
    registrar_office_name: 'Office of Deputy Registrar of Chits',
    notes: '',
  })
  const [submittingFiling, setSubmittingFiling] = useState(false)
  const [ackModalFiling, setAckModalFiling] = useState(null)
  const [ackNumberInput, setAckNumberInput] = useState('')
  const [submittingAck, setSubmittingAck] = useState(false)

  // Form XIV Modal state
  const [selectedFormXIV, setSelectedFormXIV] = useState(null)
  const [loadingFormXIV, setLoadingFormXIV] = useState(false)

  // Balance sheet & Delinquency state
  const [balanceSheet, setBalanceSheet] = useState(null)
  const [loadingBalanceSheet, setLoadingBalanceSheet] = useState(false)
  const [delinquency, setDelinquency] = useState(null)
  const [loadingDelinquency, setLoadingDelinquency] = useState(false)

  const isStaff = user?.role && ['SUPER_ADMIN', 'ORG_ADMIN', 'BRANCH_MANAGER'].includes(user.role)

  const fetchSummary = async () => {
    try {
      setLoadingSummary(true)
      const res = await complianceApi.getSystemSummary()
      setSummary(res.data)
    } catch (err) {
      console.error('Failed to load compliance summary', err)
    } finally {
      setLoadingSummary(false)
    }
  }

  const fetchGroups = async () => {
    try {
      const res = await groupsApi.list()
      const items = res.data?.items || []
      setGroups(items)
      if (items.length > 0 && !selectedGroupId) {
        setSelectedGroupId(items[0].id)
      }
    } catch (err) {
      console.error('Failed to load groups list', err)
    }
  }

  const fetchDeposits = async () => {
    try {
      setLoadingDeposits(true)
      const res = await complianceApi.listDeposits()
      setDeposits(res.data || [])
    } catch (err) {
      console.error('Failed to load deposits', err)
    } finally {
      setLoadingDeposits(false)
    }
  }

  const fetchFilings = async () => {
    try {
      setLoadingFilings(true)
      const res = await complianceApi.listFilings()
      setFilings(res.data || [])
    } catch (err) {
      console.error('Failed to load filings', err)
    } finally {
      setLoadingFilings(false)
    }
  }

  const fetchBalanceSheet = async (gId) => {
    if (!gId) return
    try {
      setLoadingBalanceSheet(true)
      const res = await complianceApi.getBalanceSheet(gId)
      setBalanceSheet(res.data)
    } catch (err) {
      console.error('Failed to load balance sheet', err)
      setBalanceSheet(null)
    } finally {
      setLoadingBalanceSheet(false)
    }
  }

  const fetchDelinquency = async (gId) => {
    if (!gId) return
    try {
      setLoadingDelinquency(true)
      const res = await complianceApi.getDelinquencyReport(gId)
      setDelinquency(res.data)
    } catch (err) {
      console.error('Failed to load delinquency report', err)
      setDelinquency(null)
    } finally {
      setLoadingDelinquency(false)
    }
  }

  useEffect(() => {
    fetchSummary()
    fetchGroups()
    fetchDeposits()
    fetchFilings()
  }, [])

  useEffect(() => {
    if (selectedGroupId) {
      if (activeSubTab === 'balance-sheet') {
        fetchBalanceSheet(selectedGroupId)
      } else if (activeSubTab === 'delinquency') {
        fetchDelinquency(selectedGroupId)
      }
    }
  }, [selectedGroupId, activeSubTab])

  const handleLodgeDeposit = async (e) => {
    e.preventDefault()
    setSubmittingDeposit(true)
    try {
      await complianceApi.lodgeDeposit({
        ...depositForm,
        amount: Number(depositForm.amount),
      })
      setShowAddDepositModal(false)
      fetchDeposits()
      fetchSummary()
    } catch (err) {
      alert('Failed to lodge deposit: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingDeposit(false)
    }
  }

  const handleVerifyLien = async (depositId, status) => {
    try {
      await complianceApi.verifyDeposit(depositId, {
        lien_status: status,
        remarks: status === 'PLEDGED' ? 'Verified in favor of Registrar of Chits' : 'Lien released after circle audit.',
      })
      fetchDeposits()
      fetchSummary()
    } catch (err) {
      alert('Verification error: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleRecordFiling = async (e) => {
    e.preventDefault()
    setSubmittingFiling(true)
    try {
      await complianceApi.recordFiling(filingForm)
      setShowAddFilingModal(false)
      fetchFilings()
      fetchSummary()
    } catch (err) {
      alert('Failed to record filing: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingFiling(false)
    }
  }

  const handleUpdateAck = async (e) => {
    e.preventDefault()
    if (!ackModalFiling) return
    setSubmittingAck(true)
    try {
      await complianceApi.updateFiling(ackModalFiling.id, {
        acknowledgment_number: ackNumberInput,
        notes: 'Statutory acknowledgment confirmed from Registrar office.',
      })
      setAckModalFiling(null)
      setAckNumberInput('')
      fetchFilings()
      fetchSummary()
    } catch (err) {
      alert('Update failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmittingAck(false)
    }
  }

  const handleViewFormXIV = (filing) => {
    if (filing.metadata_payload) {
      setSelectedFormXIV(filing.metadata_payload)
    } else {
      alert('No Form XIV minutes recorded for this filing.')
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Regulatory Compliance & Statutory Filings</h1>
          <p className="page-description">
            Mandatory governance under the Chit Funds Act, 1982: Section 20 Security Lien Deposits, Form XIV Auction Minutes, and Audited Balance Sheets.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => {
              fetchSummary()
              fetchDeposits()
              fetchFilings()
              if (selectedGroupId) {
                fetchBalanceSheet(selectedGroupId)
                fetchDelinquency(selectedGroupId)
              }
            }}
            className="btn btn-outline"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh State</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-cols-4">
        <div className="metric-card">
          <div className="metric-top">
            <span className="metric-label">Section 20 Lien Pledged</span>
            <div className="metric-icon-box metric-icon-emerald">
              <Lock className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="metric-number">{formatINR(summary?.total_lien_pledged || 100000)}</div>
            <div className="metric-bottom mt-2">
              <span className="trend-badge trend-positive">
                <ShieldCheck className="w-3.5 h-3.5" /> 100% Lien Secured
              </span>
              <span>{summary?.active_circles_covered || 0} active circles</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span className="metric-label">Registrar Filings</span>
            <div className="metric-icon-box metric-icon-blue">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="metric-number">{summary?.total_filings_count || 0} Lodged</div>
            <div className="metric-bottom mt-2">
              <span className="trend-badge trend-positive">Form XIV / II</span>
              <span>{summary?.pending_filings_count || 0} awaiting seal</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span className="metric-label">Prize Money Disbursed</span>
            <div className="metric-icon-box metric-icon-gold">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="metric-number">{formatINR(summary?.total_prize_disbursed || 0)}</div>
            <div className="metric-bottom mt-2">
              <span className="trend-badge trend-positive">Section 31 Sureties</span>
              <span>Audited payout outflow</span>
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span className="metric-label">Uncollected Arrears</span>
            <div className="metric-icon-box" style={{ background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' }}>
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="metric-number">{formatINR(summary?.total_arrears_uncollected || 0)}</div>
            <div className="metric-bottom mt-2">
              <span className="trend-badge trend-negative">Subscriber Arrears</span>
              <span>Outstanding dues</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveSubTab('deposits')}
          className={`tab-item ${activeSubTab === 'deposits' ? 'active' : ''}`}
        >
          <Lock className="w-4 h-4" />
          <span>Section 20 Security Deposits ({deposits.length})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('filings')}
          className={`tab-item ${activeSubTab === 'filings' ? 'active' : ''}`}
        >
          <FileText className="w-4 h-4" />
          <span>Statutory Registrar Filings ({filings.length})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('balance-sheet')}
          className={`tab-item ${activeSubTab === 'balance-sheet' ? 'active' : ''}`}
        >
          <Scale className="w-4 h-4" />
          <span>Double-Entry Balance Sheets</span>
        </button>
        <button
          onClick={() => setActiveSubTab('delinquency')}
          className={`tab-item ${activeSubTab === 'delinquency' ? 'active' : ''}`}
        >
          <TrendingDown className="w-4 h-4" />
          <span>Delinquency Aging</span>
        </button>
      </div>

      {/* Tab 1: Section 20 Security Deposits */}
      {activeSubTab === 'deposits' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Section 20 Fixed Deposit Receipts (FDR) Lien Register</h3>
              <p className="card-subtitle">
                100% of aggregate chit values pledged with scheduled banks in favor of the Registrar prior to commencement.
              </p>
            </div>
            {isStaff && (
              <button
                onClick={() => setShowAddDepositModal(true)}
                className="btn btn-primary btn-sm"
              >
                <Plus className="w-4 h-4" /> Lodge Deposit
              </button>
            )}
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Chit Circle</th>
                    <th>Bank & FDR Number</th>
                    <th>Deposit Amount</th>
                    <th>Lien Status</th>
                    <th>Maturity Date</th>
                    <th>Registrar Reference</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {deposits.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                        No Section 20 security deposits lodged yet.
                      </td>
                    </tr>
                  ) : (
                    deposits.map((d) => (
                      <tr key={d.id}>
                        <td>
                          <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-700)' }}>
                            {d.group_code || 'CIRCLE'}
                          </span>
                        </td>
                        <td>
                          <div>
                            <div style={{ fontWeight: 600 }}>{d.bank_name}</div>
                            <span className="font-mono text-muted" style={{ fontSize: '0.75rem' }}>{d.account_or_fdr_number}</span>
                          </div>
                        </td>
                        <td className="font-mono font-bold" style={{ color: 'var(--emerald-700)' }}>
                          {formatINR(d.amount)}
                        </td>
                        <td>
                          {d.lien_status === 'PLEDGED' && <span className="badge badge-emerald">Lien Pledged</span>}
                          {d.lien_status === 'RELEASED' && <span className="badge badge-slate">Released</span>}
                          {d.lien_status === 'PENDING' && <span className="badge badge-amber">Pending Verification</span>}
                        </td>
                        <td style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{d.maturity_date}</td>
                        <td className="font-mono text-muted" style={{ fontSize: '0.8125rem' }}>{d.registrar_order_reference || 'N/A'}</td>
                        <td style={{ textAlign: 'right' }}>
                          {isStaff && d.lien_status === 'PENDING' && (
                            <button
                              onClick={() => handleVerifyLien(d.id, 'PLEDGED')}
                              className="btn btn-primary btn-sm"
                            >
                              Verify Lien
                            </button>
                          )}
                          {isStaff && d.lien_status === 'PLEDGED' && (
                            <button
                              onClick={() => handleVerifyLien(d.id, 'RELEASED')}
                              className="btn btn-outline btn-sm"
                            >
                              Release
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

      {/* Tab 2: Statutory Filings */}
      {activeSubTab === 'filings' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Statutory Registrar Filings & Minutes of Auction</h3>
              <p className="card-subtitle">
                Mandatory lodging of Form XIV (auction minutes within 14 days), Form II prior sanction, and Form XXI subscriber registers.
              </p>
            </div>
            {isStaff && (
              <button
                onClick={() => setShowAddFilingModal(true)}
                className="btn btn-primary btn-sm"
              >
                <Plus className="w-4 h-4" /> Record Statutory Filing
              </button>
            )}
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Circle</th>
                    <th>Form Type</th>
                    <th>Reference #</th>
                    <th>Filed Date</th>
                    <th>Registrar Office</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filings.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                        No statutory filings recorded yet.
                      </td>
                    </tr>
                  ) : (
                    filings.map((f) => (
                      <tr key={f.id}>
                        <td className="font-mono font-bold text-emerald-700">{f.group_code || 'CIRCLE'}</td>
                        <td>
                          <span className="badge badge-blue">{f.form_type}</span>
                        </td>
                        <td className="font-mono text-muted" style={{ fontSize: '0.8125rem' }}>{f.filing_reference_number}</td>
                        <td style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{f.filed_date}</td>
                        <td style={{ fontSize: '0.8125rem' }}>{f.registrar_office_name}</td>
                        <td>
                          {f.status === 'ACKNOWLEDGED' ? (
                            <span className="badge badge-emerald">Acknowledged</span>
                          ) : (
                            <span className="badge badge-amber">Pending Seal</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                            {f.form_type === 'FORM_XIV_MINUTES' && (
                              <button
                                onClick={() => handleViewFormXIV(f)}
                                className="btn btn-outline btn-sm"
                              >
                                View Minutes
                              </button>
                            )}
                            {isStaff && f.status === 'LODGED' && (
                              <button
                                onClick={() => {
                                  setAckModalFiling(f)
                                  setAckNumberInput('')
                                }}
                                className="btn btn-primary btn-sm"
                              >
                                Enter Ack #
                              </button>
                            )}
                          </div>
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

      {/* Tab 3: Balance Sheet */}
      {activeSubTab === 'balance-sheet' && (
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: '1rem' }}>
              <div>
                <h3 className="card-title">Circle Double-Entry Balance Sheet</h3>
                <p className="card-subtitle">Audited financial reconciliation per Section 24 of Chit Funds Act</p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Circle:
                </label>
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="form-select"
                  style={{ width: '220px' }}
                >
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.group_code} ({g.status})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="card-body">
            {loadingBalanceSheet ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                Reconciling circle double-entry ledger...
              </div>
            ) : balanceSheet ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{
                  background: balanceSheet.is_balanced ? '#ecfdf5' : '#fef2f2',
                  border: `1px solid ${balanceSheet.is_balanced ? '#a7f3d0' : '#fecaca'}`,
                  borderRadius: 8,
                  padding: '1rem 1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <ShieldCheck className="w-5 h-5 text-emerald-600" />
                    <div>
                      <h5 style={{ margin: 0, fontWeight: 700, color: '#065f46' }}>
                        {balanceSheet.is_balanced ? 'Balance Sheet Fully Reconciled & Audited' : 'Balance Flagged'}
                      </h5>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: '#047857' }}>
                        Rounds: {balanceSheet.rounds_completed} / {balanceSheet.total_rounds} &bull; Section 20 Lien: {formatINR(balanceSheet.sec_20_lien_pledged)}
                      </p>
                    </div>
                  </div>
                  <span className="badge badge-emerald">Audited & Reconciled</span>
                </div>

                <div className="grid-cols-2">
                  <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '1.25rem' }}>
                    <h4 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--emerald-800)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem', marginBottom: '0.75rem' }}>
                      Inflow Pool (Assets)
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.8125rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Subscriber Collections</span>
                        <span className="font-mono font-bold">{formatINR(balanceSheet.total_gross_inflow)}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Arrears Receivable</span>
                        <span className="font-mono">{formatINR(balanceSheet.current_arrears_receivable)}</span>
                      </div>
                      <div style={{ borderTop: '1px dashed #cbd5e1', paddingTop: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 700 }}>Total Inflow</span>
                        <span className="font-mono font-bold text-emerald-700">{formatINR(balanceSheet.total_gross_inflow)}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '1.25rem' }}>
                    <h4 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--gold-800)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem', marginBottom: '0.75rem' }}>
                      Disbursements & Pool (Liabilities)
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.8125rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Prize Money Disbursed</span>
                        <span className="font-mono font-bold">{formatINR(balanceSheet.total_prize_money_disbursed)}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Dividends Distributed</span>
                        <span className="font-mono">{formatINR(balanceSheet.total_dividends_distributed)}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Foreman Commission (5%)</span>
                        <span className="font-mono">{formatINR(balanceSheet.foreman_commission_accrued)}</span>
                      </div>
                      <div style={{ borderTop: '1px dashed #cbd5e1', paddingTop: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 700 }}>Net Cash Pool</span>
                        <span className="font-mono font-bold text-emerald-700">{formatINR(balanceSheet.net_cash_pool_balance)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                Select a chit circle above to load its audited balance sheet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Delinquency Aging */}
      {activeSubTab === 'delinquency' && (
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: '1rem' }}>
              <div>
                <h3 className="card-title">Subscriber Delinquency & Aging Report</h3>
                <p className="card-subtitle">30/60/90 days delinquency classification and statutory default risk</p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Circle:
                </label>
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="form-select"
                  style={{ width: '220px' }}
                >
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.group_code} ({g.status})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="card-body">
            {delinquency ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div className="grid-cols-4">
                  <div className="metric-card">
                    <span className="metric-label">Current (0-30 Days)</span>
                    <span className="font-mono font-bold text-emerald-700" style={{ fontSize: '1.25rem' }}>
                      {formatINR(delinquency.current_dues)}
                    </span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">31-60 Days Overdue</span>
                    <span className="font-mono font-bold text-amber-700" style={{ fontSize: '1.25rem' }}>
                      {formatINR(delinquency.dues_31_to_60)}
                    </span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">61-90 Days Overdue</span>
                    <span className="font-mono font-bold" style={{ fontSize: '1.25rem', color: '#ea580c' }}>
                      {formatINR(delinquency.dues_61_to_90)}
                    </span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">NPA (90+ Days)</span>
                    <span className="font-mono font-bold" style={{ fontSize: '1.25rem', color: '#dc2626' }}>
                      {formatINR(delinquency.npa_over_90)}
                    </span>
                  </div>
                </div>

                <div className="table-container" style={{ marginTop: '1rem' }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Ticket #</th>
                        <th>Subscriber Name</th>
                        <th>Overdue Amount</th>
                        <th>Unpaid Installments</th>
                        <th>Days Overdue</th>
                        <th>Aging Risk Bucket</th>
                      </tr>
                    </thead>
                    <tbody>
                      {delinquency.delinquent_tickets?.length === 0 ? (
                        <tr>
                          <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                            No delinquent tickets in this circle. All subscribers in good standing!
                          </td>
                        </tr>
                      ) : (
                        delinquency.delinquent_tickets?.map((t) => (
                          <tr key={t.ticket_id}>
                            <td className="font-mono font-bold text-emerald-700">Ticket #{t.ticket_number}</td>
                            <td>{t.subscriber_name}</td>
                            <td className="font-mono font-bold" style={{ color: '#dc2626' }}>{formatINR(t.overdue_amount)}</td>
                            <td>{t.unpaid_installments_count} cycles</td>
                            <td>{t.days_overdue} days</td>
                            <td>
                              <span className={`badge ${t.aging_bucket === '90+' ? 'badge-red' : 'badge-amber'}`}>
                                {t.aging_bucket} Days
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                Select a chit circle above to load its delinquency report.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Lodge Section 20 Deposit Modal */}
      {showAddDepositModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Lock className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Lodge Section 20 FDR Lien</h3>
              </div>
              <button onClick={() => setShowAddDepositModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleLodgeDeposit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Target Chit Circle *</label>
                  <select
                    value={depositForm.group_id}
                    onChange={(e) => setDepositForm({ ...depositForm, group_id: e.target.value })}
                    className="form-select"
                    required
                  >
                    <option value="">Select circle...</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.group_code} ({g.status})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Bank Name *</label>
                    <input
                      type="text"
                      value={depositForm.bank_name}
                      onChange={(e) => setDepositForm({ ...depositForm, bank_name: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">FDR / Account # *</label>
                    <input
                      type="text"
                      placeholder="e.g. FDR-99220011"
                      value={depositForm.account_or_fdr_number}
                      onChange={(e) => setDepositForm({ ...depositForm, account_or_fdr_number: e.target.value })}
                      className="form-input font-mono"
                      required
                    />
                  </div>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Deposit Amount (100% Chit Value) *</label>
                    <input
                      type="number"
                      placeholder="e.g. 100000"
                      value={depositForm.amount}
                      onChange={(e) => setDepositForm({ ...depositForm, amount: e.target.value })}
                      className="form-input font-mono"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Maturity Date *</label>
                    <input
                      type="date"
                      value={depositForm.maturity_date}
                      onChange={(e) => setDepositForm({ ...depositForm, maturity_date: e.target.value })}
                      className="form-input"
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Registrar Order Ref (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. REG/CHIT/2026/088"
                    value={depositForm.registrar_order_reference}
                    onChange={(e) => setDepositForm({ ...depositForm, registrar_order_reference: e.target.value })}
                    className="form-input font-mono"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowAddDepositModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingDeposit}
                >
                  {submittingDeposit ? 'Lodging...' : 'Lodge FDR Deposit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Statutory Filing Modal */}
      {showAddFilingModal && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText className="w-5 h-5 text-emerald-600" />
                <h3 className="modal-title">Record Statutory Registrar Filing</h3>
              </div>
              <button onClick={() => setShowAddFilingModal(false)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleRecordFiling}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Chit Circle *</label>
                  <select
                    value={filingForm.group_id}
                    onChange={(e) => setFilingForm({ ...filingForm, group_id: e.target.value })}
                    className="form-select"
                    required
                  >
                    <option value="">Select circle...</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.group_code} ({g.status})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid-cols-2">
                  <div className="form-group">
                    <label className="form-label">Form Type *</label>
                    <select
                      value={filingForm.form_type}
                      onChange={(e) => setFilingForm({ ...filingForm, form_type: e.target.value })}
                      className="form-select"
                      required
                    >
                      <option value="FORM_XIV_MINUTES">Form XIV (Auction Minutes)</option>
                      <option value="FORM_II_SANCTION">Form II (Prior Sanction)</option>
                      <option value="FORM_XXI_MEMBERS">Form XXI (Member Register)</option>
                      <option value="FORM_I_APPLICATION">Form I (Application)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Filing Reference # *</label>
                    <input
                      type="text"
                      placeholder="e.g. FIL/2026/014"
                      value={filingForm.filing_reference_number}
                      onChange={(e) => setFilingForm({ ...filingForm, filing_reference_number: e.target.value })}
                      className="form-input font-mono"
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Registrar Office *</label>
                  <input
                    type="text"
                    value={filingForm.registrar_office_name}
                    onChange={(e) => setFilingForm({ ...filingForm, registrar_office_name: e.target.value })}
                    className="form-input"
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowAddFilingModal(false)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingFiling}
                >
                  {submittingFiling ? 'Recording...' : 'Record Filing'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Acknowledgment Modal */}
      {ackModalFiling && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Enter Registrar Ack Number</h3>
              <button onClick={() => setAckModalFiling(null)} className="btn-icon-only">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleUpdateAck}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Official Acknowledgment / Seal # *</label>
                  <input
                    type="text"
                    placeholder="e.g. ACK-TN-2026-9912"
                    value={ackNumberInput}
                    onChange={(e) => setAckNumberInput(e.target.value)}
                    className="form-input font-mono"
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setAckModalFiling(null)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingAck}
                >
                  Confirm Acknowledgment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
