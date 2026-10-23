import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Gavel,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  Zap,
  DollarSign,
  Users,
  ShieldCheck,
  Radio,
  RefreshCw,
  Send,
  Sparkles
} from 'lucide-react'
import { auctionsApi, getAuctionWsUrl } from '../api/auctions'

export default function LiveAuctionRoom({ auctionId: propAuctionId, onBack: propOnBack }) {
  const params = useParams()
  const navigate = useNavigate()
  const auctionId = propAuctionId || params.auctionId || params.id

  const handleBack = () => {
    if (propOnBack) propOnBack()
    else navigate('/auctions')
  }

  const [auction, setAuction] = useState(null)
  const [bids, setBids] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submittingBid, setSubmittingBid] = useState(false)
  const [bidInput, setBidInput] = useState('')
  const [bidError, setBidError] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [settlementResult, setSettlementResult] = useState(null)

  const socketRef = useRef(null)

  // Fetch initial auction details
  const fetchAuction = useCallback(async () => {
    try {
      setLoading(true)
      const res = await auctionsApi.getAuctionDetail(auctionId)
      setAuction(res.data)
      setBids(res.data.recent_bids || [])
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load auction room data.')
    } finally {
      setLoading(false)
    }
  }, [auctionId])

  useEffect(() => {
    fetchAuction()
  }, [fetchAuction])

  // Establish WebSocket connection
  useEffect(() => {
    let isMounted = true

    const connectWebSocket = () => {
      try {
        const wsUrl = getAuctionWsUrl(auctionId)
        const ws = new WebSocket(wsUrl)
        socketRef.current = ws

        ws.onopen = () => {
          if (isMounted) setWsConnected(true)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'NEW_BID') {
              setBids((prev) => [data.bid, ...prev])
              setAuction((prev) => {
                if (!prev) return prev
                return {
                  ...prev,
                  current_highest_bid: data.bid.bid_discount_amount,
                }
              })
            } else if (data.type === 'AUCTION_STARTED') {
              setAuction((prev) => (prev ? { ...prev, status: 'OPEN', opened_at: data.opened_at } : prev))
            } else if (data.type === 'AUCTION_CLOSED') {
              setAuction((prev) => (prev ? { ...prev, status: 'CLOSED' } : prev))
              setSettlementResult(data)
              fetchAuction()
            }
          } catch (err) {
            console.error('Error handling WebSocket message:', err)
          }
        }

        ws.onclose = () => {
          if (isMounted) setWsConnected(false)
        }

        ws.onerror = () => {
          if (isMounted) setWsConnected(false)
        }
      } catch (e) {
        console.error('Failed to initialize WebSocket:', e)
      }
    }

    if (auctionId) {
      connectWebSocket()
    }

    return () => {
      isMounted = false
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [auctionId, fetchAuction])

  const handlePlaceBid = async (e) => {
    e.preventDefault()
    setBidError(null)
    const discountVal = parseFloat(bidInput)
    if (isNaN(discountVal)) {
      setBidError('Please enter a valid numeric discount amount.')
      return
    }

    if (auction) {
      if (discountVal < (auction.min_discount_amount || 0)) {
        setBidError(`Minimum legal discount is ₹${(auction.min_discount_amount || 0).toLocaleString('en-IN')}`)
        return
      }
      if (discountVal > (auction.max_discount_amount || 40000)) {
        setBidError(`Maximum statutory discount cap is ₹${(auction.max_discount_amount || 40000).toLocaleString('en-IN')} (40%)`)
        return
      }
    }

    setSubmittingBid(true)
    try {
      await auctionsApi.placeBid(auctionId, discountVal)
      setBidInput('')
      fetchAuction()
    } catch (err) {
      setBidError(err.response?.data?.detail || 'Failed to submit bid.')
    } finally {
      setSubmittingBid(false)
    }
  }

  const handleCloseAuction = async () => {
    if (!window.confirm('Are you sure you want to conclude and settle this auction round?')) return
    try {
      await auctionsApi.closeAuction(auctionId)
      fetchAuction()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to close auction.')
    }
  }

  const formatINR = (val) => {
    const num = parseFloat(val) || 0
    return '₹' + num.toLocaleString('en-IN')
  }

  if (loading || !auction) {
    return (
      <div className="card">
        <div className="card-body" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Entering auction chamber...
        </div>
      </div>
    )
  }

  const isLive = auction.status === 'OPEN' || auction.status === 'IN_PROGRESS'
  const isClosed = auction.status === 'CLOSED' || auction.status === 'COMPLETED'
  const currentDiscount = auction.current_highest_bid || auction.min_discount_amount || 0
  const prizeAmount = (auction.chit_value || 100000) - currentDiscount

  return (
    <div className="space-y-6">
      {/* Chamber Header */}
      <div className="card">
        <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={handleBack}
              className="btn btn-outline btn-sm"
              title="Return to auctions"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }} className="font-mono text-emerald-700">
                  {auction.group_code || 'CIRCLE'} - Round #{auction.round_number}
                </h1>
                {isLive ? (
                  <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Radio className="w-3.5 h-3.5 text-emerald-600 animate-pulse" /> Live Chamber Active
                  </span>
                ) : isClosed ? (
                  <span className="badge badge-slate">Concluded</span>
                ) : (
                  <span className="badge badge-blue">Scheduled</span>
                )}
              </div>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Chit Pool: <strong>{formatINR(auction.chit_value || 100000)}</strong> &bull; WebSocket: {wsConnected ? <span style={{ color: 'var(--emerald-600)', fontWeight: 600 }}>Connected</span> : <span style={{ color: 'var(--text-muted)' }}>Standby</span>}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {isLive && (
              <button
                onClick={handleCloseAuction}
                className="btn btn-danger btn-sm"
              >
                <CheckCircle2 className="w-4 h-4" /> Conclude Round & Settle
              </button>
            )}
            <button
              onClick={fetchAuction}
              className="btn btn-outline btn-sm"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Chamber Grid */}
      <div className="grid-cols-3">
        {/* Left 2 Cols: Live Bid Board & Bid Submission Form */}
        <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Price & Discount Spotlight Card */}
          <div className="card" style={{ background: 'linear-gradient(135deg, #064e3b, #059669)', color: '#ffffff' }}>
            <div className="card-body" style={{ padding: '1.75rem', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1.5rem' }}>
              <div>
                <span style={{ fontSize: '0.8125rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a7f3d0', fontWeight: 600 }}>
                  Current Standing Discount Offered
                </span>
                <div className="font-mono" style={{ fontSize: '2.5rem', fontWeight: 800, lineHeight: 1.1, marginTop: '0.25rem' }}>
                  {formatINR(currentDiscount)}
                </div>
                <div style={{ fontSize: '0.8125rem', color: '#d1fae5', marginTop: '0.35rem' }}>
                  Statutory Bounds: {formatINR(auction.min_discount_amount || 5000)} (5%) to {formatINR(auction.max_discount_amount || 40000)} (40%)
                </div>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.12)', backdropFilter: 'blur(8px)', borderRadius: 12, padding: '1rem 1.5rem', textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: '#a7f3d0', textTransform: 'uppercase', fontWeight: 600 }}>
                  Prize Money to Winner
                </span>
                <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fef08a' }}>
                  {formatINR(prizeAmount)}
                </div>
                <span style={{ fontSize: '0.75rem', color: '#d1fae5' }}>
                  Foreman Comm. 5%: {formatINR((auction.chit_value || 100000) * 0.05)}
                </span>
              </div>
            </div>
          </div>

          {/* Bid Submission Form (Active if chamber is open) */}
          {isLive ? (
            <div className="card">
              <div className="card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Gavel className="w-5 h-5 text-emerald-600" />
                  <h3 className="card-title">Place Competitive Bid</h3>
                </div>
                <span className="badge badge-emerald">Reverse Auction</span>
              </div>
              <div className="card-body">
                <form onSubmit={handlePlaceBid}>
                  {bidError && (
                    <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#b91c1c', marginBottom: '1rem' }}>
                      {bidError}
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                    <div className="form-group" style={{ flex: 1, margin: 0 }}>
                      <label className="form-label">
                        Discount Amount to Forgo (Min {formatINR(currentDiscount + 500)}) *
                      </label>
                      <input
                        type="number"
                        placeholder={`e.g. ${currentDiscount + 1000}`}
                        value={bidInput}
                        onChange={(e) => setBidInput(e.target.value)}
                        className="form-input font-mono"
                        required
                        disabled={submittingBid}
                      />
                    </div>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={submittingBid}
                      style={{ padding: '0.625rem 1.5rem' }}
                    >
                      <Send className="w-4 h-4" />
                      <span>{submittingBid ? 'Submitting...' : 'Submit Bid'}</span>
                    </button>
                  </div>
                </form>

                {/* Quick Bid Increments */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>Quick increments:</span>
                  {[500, 1000, 2000, 5000].map((inc) => (
                    <button
                      key={inc}
                      type="button"
                      onClick={() => setBidInput(String(currentDiscount + inc))}
                      className="btn btn-outline btn-sm"
                      style={{ padding: '2px 8px', fontSize: '0.6875rem' }}
                    >
                      +{formatINR(inc)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : isClosed ? (
            <div className="card" style={{ background: '#f8fafc' }}>
              <div className="card-body" style={{ padding: '1.5rem', textAlign: 'center' }}>
                <Award className="w-10 h-10 text-emerald-600" style={{ margin: '0 auto 0.75rem auto' }} />
                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Auction Settled: Ticket #{auction.winning_ticket_number || '1'} Won
                </h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', maxWidth: '420px', margin: '0.25rem auto 1rem auto' }}>
                  Prize payout of {formatINR(auction.prize_amount || 0)} allocated to subscriber after Section 31 surety verification.
                </p>
                <div style={{ display: 'inline-flex', gap: '1.5rem', background: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '0.75rem 1.5rem' }}>
                  <div>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Winning Discount</span>
                    <div className="font-mono font-bold text-emerald-700">{formatINR(auction.winning_bid_amount || 0)}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Dividend / Subscriber</span>
                    <div className="font-mono font-bold text-emerald-700">{formatINR(auction.dividend_per_subscriber || 0)}</div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="card-body" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                This round is scheduled for {new Date(auction.scheduled_date).toLocaleString()}. Bidding will open once the chamber begins.
              </div>
            </div>
          )}

          {/* Real-time Bid Stream Table */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                <h3 className="card-title">Live Chamber Feed</h3>
              </div>
              <span className="badge badge-slate" style={{ fontSize: '0.6875rem' }}>
                Monotonic FCFS Timestamp Ordering
              </span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Ticket #</th>
                      <th>Discount Bid</th>
                      <th>Prize Equivalent</th>
                      <th style={{ textAlign: 'right' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bids.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                          No bids submitted in this chamber yet.
                        </td>
                      </tr>
                    ) : (
                      bids.map((b, idx) => (
                        <tr key={b.id || idx}>
                          <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {b.bid_time ? new Date(b.bid_time).toLocaleTimeString() : 'Just now'}
                          </td>
                          <td className="font-mono font-semibold">
                            Ticket #{b.chit_membership?.ticket_number || b.ticket_number || idx + 1}
                          </td>
                          <td className="font-mono font-bold" style={{ color: 'var(--emerald-700)' }}>
                            {formatINR(b.bid_discount_amount)}
                          </td>
                          <td className="font-mono text-muted">
                            {formatINR((auction.chit_value || 100000) - b.bid_discount_amount)}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            {idx === 0 ? (
                              <span className="badge badge-emerald">Leading Bid</span>
                            ) : (
                              <span className="badge badge-slate">Outbid</span>
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
        </div>

        {/* Right 1 Col: Statutory Rules & Round Meta */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Statutory Chit Rules */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <h3 className="card-title">Chit Funds Act Rules</h3>
              </div>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              <div>
                <strong style={{ color: 'var(--text-primary)' }}>Reverse Bidding Model:</strong> Subscribers bid the discount they are willing to surrender from the chit value.
              </div>
              <div>
                <strong style={{ color: 'var(--text-primary)' }}>40% Statutory Cap:</strong> The maximum permissible discount cannot exceed 40% of the gross chit value.
              </div>
              <div>
                <strong style={{ color: 'var(--text-primary)' }}>Dividend Sharing:</strong> After deduction of 5% foreman commission, the entire discount balance is equally credited back to all non-prized and prized subscribers.
              </div>
              <div>
                <strong style={{ color: 'var(--text-primary)' }}>Monotonic Tie-breaking:</strong> If two subscribers place identical bids, First-Come First-Served (FCFS) timestamp priority decides the round winner.
              </div>
            </div>
          </div>

          {/* Quick Round Details */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Round Specifications</h3>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Circle Code</span>
                <span className="font-mono font-bold">{auction.group_code || 'APEX-GOLD'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Round Number</span>
                <span className="font-mono font-bold">#{auction.round_number}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Chit Value</span>
                <span className="font-mono font-bold">{formatINR(auction.chit_value || 100000)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Foreman Commission</span>
                <span className="font-mono">5% ({formatINR((auction.chit_value || 100000) * 0.05)})</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
