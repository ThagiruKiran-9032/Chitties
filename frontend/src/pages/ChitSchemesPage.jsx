import React, { useState, useEffect } from 'react'
import { Layers, Plus, Calendar, Percent, ArrowUpRight, CheckCircle2 } from 'lucide-react'
import { schemesApi } from '../api/schemes'

export default function ChitSchemesPage() {
  const [schemes, setSchemes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    total_value: '',
    duration_months: 50,
    foreman_commission_pct: '5.00',
    max_bid_discount_pct: '30.00',
    min_bid_discount_pct: '5.00',
    foreman_month_one_reserved: true,
  })
  const [submitting, setSubmitting] = useState(false)

  const fetchSchemes = async () => {
    setLoading(true)
    try {
      const res = await schemesApi.list()
      setSchemes(res.data.items || [])
    } catch (err) {
      console.error('Failed to load schemes:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSchemes()
  }, [])

  const computedInstallment = () => {
    const val = parseFloat(formData.total_value)
    const dur = parseInt(formData.duration_months)
    if (!isNaN(val) && !isNaN(dur) && dur > 0) {
      return (val / dur).toFixed(2)
    }
    return '0.00'
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const payload = {
        ...formData,
        total_value: parseFloat(formData.total_value),
        duration_months: parseInt(formData.duration_months),
        monthly_installment: parseFloat(computedInstallment()),
        foreman_commission_pct: parseFloat(formData.foreman_commission_pct),
        max_bid_discount_pct: parseFloat(formData.max_bid_discount_pct),
        min_bid_discount_pct: parseFloat(formData.min_bid_discount_pct),
      }
      await schemesApi.create(payload)
      setShowModal(false)
      setFormData({
        name: '',
        total_value: '',
        duration_months: 50,
        foreman_commission_pct: '5.00',
        max_bid_discount_pct: '30.00',
        min_bid_discount_pct: '5.00',
        foreman_month_one_reserved: true,
      })
      fetchSchemes()
    } catch (err) {
      alert('Failed to create scheme: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Layers className="w-6 h-6 text-emerald-400" /> Chit Scheme Templates
          </h1>
          <p className="text-sm text-slate-400">Configure standard chit products, commission rules, and duration terms.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-emerald-900/30"
        >
          <Plus className="w-4 h-4" /> New Scheme
        </button>
      </div>

      {/* Schemes Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading scheme blueprints...</div>
      ) : schemes.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No schemes defined. Click 'New Scheme' to create your first template.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {schemes.map((s) => (
            <div key={s.id} className="p-6 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4 shadow-xl hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg text-white">{s.name}</h3>
                  <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" /> {s.duration_months} Months Duration
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Active
                </span>
              </div>

              {/* Financial Metrics */}
              <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-slate-500">Total Value</div>
                  <div className="text-base font-bold text-emerald-400 font-mono">
                    ₹{Number(s.total_value).toLocaleString('en-IN')}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Monthly Dues</div>
                  <div className="text-base font-bold text-slate-200 font-mono">
                    ₹{Number(s.monthly_installment).toLocaleString('en-IN')}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Foreman Fee</div>
                  <div className="text-slate-300 font-medium font-mono">{s.foreman_commission_pct}%</div>
                </div>
                <div>
                  <div className="text-slate-500">Max Bid Discount</div>
                  <div className="text-slate-300 font-medium font-mono">{s.max_bid_discount_pct}%</div>
                </div>
              </div>

              {/* Feature Badges */}
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {s.foreman_month_one_reserved ? (
                  <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Month 1: Foreman Reserved
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Month 1: Auctioned
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Scheme Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Create Scheme Blueprint</h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-slate-500 hover:text-slate-300">✕</button>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Scheme Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Super Saver 5 Lakhs 50M"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Total Chit Value (₹)</label>
                  <input
                    type="number"
                    step="1000"
                    required
                    placeholder="500000"
                    value={formData.total_value}
                    onChange={(e) => setFormData({ ...formData, total_value: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Duration (Months = Tickets)</label>
                  <input
                    type="number"
                    required
                    min="2"
                    max="120"
                    value={formData.duration_months}
                    onChange={(e) => setFormData({ ...formData, duration_months: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
              </div>

              {/* Calculated Monthly Installment Preview */}
              <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-lg text-xs flex justify-between items-center text-emerald-300">
                <span>Calculated Base Installment:</span>
                <span className="font-bold text-sm font-mono">₹{computedInstallment()} / month</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Foreman Commission (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.foreman_commission_pct}
                    onChange={(e) => setFormData({ ...formData, foreman_commission_pct: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Max Bid Discount Cap (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.max_bid_discount_pct}
                    onChange={(e) => setFormData({ ...formData, max_bid_discount_pct: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.foreman_month_one_reserved}
                    onChange={(e) => setFormData({ ...formData, foreman_month_one_reserved: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-emerald-500 focus:ring-emerald-500"
                  />
                  <span>Month 1 is strictly reserved for Foreman without auction (Statutory standard)</span>
                </label>
              </div>
            </div>

            <div className="flex gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition"
              >
                {submitting ? 'Saving...' : 'Save Scheme'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
