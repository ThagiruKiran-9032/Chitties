import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Gavel,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  Zap,
  Radio,
  ArrowRight,
  Filter,
  RefreshCw,
  Play
} from 'lucide-react'
import { auctionsApi } from '../api/auctions'

export default function AuctionsPage({ onSelectAuction }) {
  const navigate = useNavigate()
  const [auctions, setAuctions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterStatus, setFilterStatus] = useState('ALL')

  const fetchAuctions = async () => {
    try {
      setLoading(true)
      const params = filterStatus === 'ALL' ? {} : { status: filterStatus }
      const res = await auctionsApi.list(params)
      setAuctions(res.data || [])
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load auction rounds.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAuctions()
  }, [filterStatus])

  const handleSelect = (auctionId) => {
    if (onSelectAuction) {
      onSelectAuction(auctionId)
    } else {
      navigate(`/auctions/${auctionId}`)
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
          <h1 className="page-title">Auctions & Bidding Chamber</h1>
          <p className="page-description">
            Reverse discount bidding rounds under the Chit Funds Act, 1982. Real-time FCFS monotonic tie-breaking and dividend calculations.
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={fetchAuctions}
            className="btn btn-outline"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Feed</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="tabs">
        <button
          onClick={() => setFilterStatus('ALL')}
          className={`tab-item ${filterStatus === 'ALL' ? 'active' : ''}`}
        >
          <span>All Rounds</span>
        </button>
        <button
          onClick={() => setFilterStatus('OPEN')}
          className={`tab-item ${filterStatus === 'OPEN' ? 'active' : ''}`}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#059669', display: 'inline-block' }} />
            Live Chambers
          </span>
        </button>
        <button
          onClick={() => setFilterStatus('SCHEDULED')}
          className={`tab-item ${filterStatus === 'SCHEDULED' ? 'active' : ''}`}
        >
          <span>Upcoming Scheduled</span>
        </button>
        <button
          onClick={() => setFilterStatus('CLOSED')}
          className={`tab-item ${filterStatus === 'CLOSED' ? 'active' : ''}`}
        >
          <span>Concluded & Settled</span>
        </button>
      </div>

      {/* Auction Rounds Grid */}
      {loading ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            Scanning live auction chambers...
          </div>
        </div>
      ) : error ? (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '1rem', borderRadius: 8, color: '#b91c1c', fontSize: '0.875rem' }}>
          {error}
        </div>
      ) : auctions.length === 0 ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
            <Gavel className="w-12 h-12 text-muted" style={{ margin: '0 auto 1rem auto', strokeWidth: 1.5 }} />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>No Auction Rounds Found</h3>
            <p style={{ maxWidth: '400px', margin: '0.5rem auto 1.5rem auto', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No auctions match the selected filter. Active chit circles automatically generate monthly scheduled auction rounds.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid-cols-3">
          {auctions.map((auc) => {
            const isLive = auc.status === 'OPEN' || auc.status === 'IN_PROGRESS'
            const isClosed = auc.status === 'CLOSED' || auc.status === 'COMPLETED'
            return (
              <div
                key={auc.id}
                className="card"
                style={{
                  border: isLive ? '1.5px solid var(--emerald-500)' : '1px solid var(--border-subtle)',
                  boxShadow: isLive ? '0 4px 14px rgba(5, 150, 105, 0.15)' : 'var(--shadow-sm)'
                }}
              >
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="font-mono" style={{ fontWeight: 700, color: 'var(--emerald-700)', fontSize: '0.9375rem' }}>
                      {auc.group_code || 'CHIT-CIRCLE'}
                    </span>
                    <span className="badge badge-slate" style={{ fontSize: '0.6875rem' }}>
                      Round #{auc.round_number}
                    </span>
                  </div>
                  {isLive && (
                    <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Radio className="w-3 h-3 text-emerald-600 animate-pulse" /> Live Now
                    </span>
                  )}
                  {auc.status === 'SCHEDULED' && <span className="badge badge-blue">Scheduled</span>}
                  {isClosed && <span className="badge badge-slate">Concluded</span>}
                </div>

                <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    <Clock className="w-4 h-4 text-muted" />
                    <span>{new Date(auc.scheduled_date).toLocaleString()}</span>
                  </div>

                  <div style={{ background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Chit Pool Value</span>
                      <span className="font-mono font-bold">{formatINR(auc.chit_value || 100000)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Statutory Discount (5%-40%)</span>
                      <span className="font-mono" style={{ color: 'var(--gold-700)' }}>
                        {formatINR(auc.min_discount_amount || 5000)} - {formatINR(auc.max_discount_amount || 40000)}
                      </span>
                    </div>
                    {isClosed && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.35rem' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Winning Prize</span>
                        <span className="font-mono font-bold" style={{ color: 'var(--emerald-700)' }}>
                          {formatINR(auc.prize_amount || 0)} (Ticket #{auc.winning_ticket_number})
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="card-footer" style={{ justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {isLive ? 'Bidding active' : isClosed ? 'Settlement archived' : 'Awaiting start'}
                  </span>
                  <button
                    onClick={() => handleSelect(auc.id)}
                    className={`btn btn-sm ${isLive ? 'btn-primary' : 'btn-outline'}`}
                  >
                    {isLive ? (
                      <>
                        <span>Enter Chamber</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    ) : isClosed ? (
                      <>
                        <span>View Results</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        <span>Open Chamber</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
