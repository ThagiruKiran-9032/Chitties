import React, { useState, useEffect } from 'react'
import { Building2, Plus, Phone, MapPin, CheckCircle2 } from 'lucide-react'
import { branchesApi } from '../api/branches'

export default function BranchesPage() {
  const [branches, setBranches] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ branch_code: '', name: '', address: '', phone: '' })
  const [submitting, setSubmitting] = useState(false)

  const fetchBranches = async () => {
    setLoading(true)
    try {
      const res = await branchesApi.list()
      setBranches(res.data.items || [])
    } catch (err) {
      console.error('Failed to load branches:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBranches()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await branchesApi.create(formData)
      setShowModal(false)
      setFormData({ branch_code: '', name: '', address: '', phone: '' })
      fetchBranches()
    } catch (err) {
      alert('Failed to create branch: ' + (err.response?.data?.detail || err.message))
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
            <Building2 className="w-6 h-6 text-emerald-400" /> Branch Directory
          </h1>
          <p className="text-sm text-slate-400">Manage regional and physical branch offices across your organization.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-emerald-900/30"
        >
          <Plus className="w-4 h-4" /> Add Branch
        </button>
      </div>

      {/* Grid of Branch Cards */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading branch directory...</div>
      ) : branches.length === 0 ? (
        <div className="text-center py-12 text-slate-500">No branches found. Click 'Add Branch' to create one.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {branches.map((b) => (
            <div key={b.id} className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3 shadow-xl hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                    {b.branch_code}
                  </span>
                  <h3 className="font-semibold text-lg text-white mt-1.5">{b.name}</h3>
                </div>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" /> {b.status}
                </span>
              </div>
              <div className="text-xs text-slate-400 space-y-1.5 pt-2 border-t border-slate-800/60">
                {b.address && (
                  <p className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                    <span>{b.address}</span>
                  </p>
                )}
                {b.phone && (
                  <p className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                    <span className="font-mono">{b.phone}</span>
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Branch Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white">Create New Branch</h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-slate-500 hover:text-slate-300">✕</button>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Branch Code (Unique)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. KOCHI-01"
                  value={formData.branch_code}
                  onChange={(e) => setFormData({ ...formData, branch_code: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500 uppercase"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Branch Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Kochi Central Office"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Address</label>
                <textarea
                  rows="2"
                  placeholder="Physical street address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                ></textarea>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Contact Phone</label>
                <input
                  type="text"
                  placeholder="0484-1234567"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
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
                {submitting ? 'Creating...' : 'Save Branch'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
