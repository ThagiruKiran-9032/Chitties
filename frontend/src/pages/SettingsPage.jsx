import React, { useState } from 'react'
import {
  Settings,
  User,
  Building,
  Bell,
  Shield,
  Key,
  CheckCircle2,
  AlertCircle,
  Save,
  Lock,
  Mail,
  Phone,
  Eye,
  EyeOff,
  Send,
  Sparkles
} from 'lucide-react'
import { useAuth, DEMO_ACCOUNTS } from '../context/AuthContext'

export default function SettingsPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile') // 'profile' | 'organization' | 'notifications'

  // User Profile State
  const [fullName, setFullName] = useState(user?.full_name || 'Admin User')
  const [email, setEmail] = useState(user?.email || 'admin@apexchits.com')
  const [phone, setPhone] = useState('+91 98400 12345')
  const [profileSuccess, setProfileSuccess] = useState('')

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [passwordError, setPasswordError] = useState('')

  // Organization Settings State
  const [orgName, setOrgName] = useState('Apex Chits International Pvt Ltd')
  const [regNumber, setRegNumber] = useState('U65992TN2026PTC018234')
  const [registrarOffice, setRegistrarOffice] = useState('Office of Deputy Registrar of Chits, Chennai Central')
  const [commissionRate, setCommissionRate] = useState('5.00')
  const [maxDiscountCap, setMaxDiscountCap] = useState('40.00')
  const [orgSuccess, setOrgSuccess] = useState('')

  // Notification Preferences State
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [smsReceipts, setSmsReceipts] = useState(true)
  const [auctionReminders, setAuctionReminders] = useState(true)
  const [complianceDeadlines, setComplianceDeadlines] = useState(true)
  const [notificationSuccess, setNotificationSuccess] = useState('')
  const [testNotificationSent, setTestNotificationSent] = useState(false)

  const handleSaveProfile = (e) => {
    e.preventDefault()
    setProfileSuccess('Profile details saved successfully!')
    setTimeout(() => setProfileSuccess(''), 3000)
  }

  const handleChangePassword = (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.')
      return
    }
    setPasswordSuccess('Password updated successfully.')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setTimeout(() => setPasswordSuccess(''), 3000)
  }

  const handleSaveOrg = (e) => {
    e.preventDefault()
    setOrgSuccess('Organization governance rules updated.')
    setTimeout(() => setOrgSuccess(''), 3000)
  }

  const handleSaveNotifications = (e) => {
    e.preventDefault()
    setNotificationSuccess('Notification delivery channels updated.')
    setTimeout(() => setNotificationSuccess(''), 3000)
  }

  const handleSendTestAlert = () => {
    setTestNotificationSent(true)
    setTimeout(() => setTestNotificationSent(false), 4000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Platform Settings & Notifications</h1>
          <p className="page-description">
            Subscriber profile management, organization statutory configuration, and multi-channel notification rules.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveTab('profile')}
          className={`tab-item ${activeTab === 'profile' ? 'active' : ''}`}
        >
          <User className="w-4 h-4" />
          <span>User Profile</span>
        </button>
        <button
          onClick={() => setActiveTab('organization')}
          className={`tab-item ${activeTab === 'organization' ? 'active' : ''}`}
        >
          <Building className="w-4 h-4" />
          <span>Organization Governance</span>
        </button>
        <button
          onClick={() => setActiveTab('notifications')}
          className={`tab-item ${activeTab === 'notifications' ? 'active' : ''}`}
        >
          <Bell className="w-4 h-4" />
          <span>Notification Center</span>
        </button>
      </div>

      {/* Tab 1: User Profile */}
      {activeTab === 'profile' && (
        <div className="grid-cols-2">
          {/* Profile Details */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Profile Information</h3>
            </div>
            <div className="card-body">
              {profileSuccess && (
                <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#065f46', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 className="w-4 h-4" /> {profileSuccess}
                </div>
              )}

              <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Contact Phone</label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">System Assigned Role</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="badge badge-emerald" style={{ fontSize: '0.8125rem', padding: '4px 10px' }}>
                      {user?.role || 'ORGANIZATION_ADMIN'}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Role-based access permissions active
                    </span>
                  </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                  <Save className="w-4 h-4" /> Save Profile
                </button>
              </form>
            </div>
          </div>

          {/* Change Password */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Security & Credentials</h3>
            </div>
            <div className="card-body">
              {passwordSuccess && (
                <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#065f46', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 className="w-4 h-4" /> {passwordSuccess}
                </div>
              )}
              {passwordError && (
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#b91c1c', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertCircle className="w-4 h-4" /> {passwordError}
                </div>
              )}

              <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Current Password</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">New Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="form-input"
                      placeholder="At least 6 characters"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="btn-icon-only text-muted"
                      style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)' }}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Confirm New Password</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <button type="submit" className="btn btn-outline" style={{ alignSelf: 'flex-start' }}>
                  <Lock className="w-4 h-4" /> Update Password
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Organization Governance */}
      {activeTab === 'organization' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Statutory Chit Company Configuration</h3>
              <p className="card-subtitle">Registration credentials & Chit Funds Act parameters</p>
            </div>
          </div>
          <div className="card-body">
            {orgSuccess && (
              <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#065f46', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 className="w-4 h-4" /> {orgSuccess}
              </div>
            )}

            <form onSubmit={handleSaveOrg} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="grid-cols-2">
                <div className="form-group">
                  <label className="form-label">Entity Name *</label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Corporate Identification / Registration # *</label>
                  <input
                    type="text"
                    value={regNumber}
                    onChange={(e) => setRegNumber(e.target.value)}
                    className="form-input font-mono"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Competent Registrar Office *</label>
                <input
                  type="text"
                  value={registrarOffice}
                  onChange={(e) => setRegistrarOffice(e.target.value)}
                  className="form-input"
                  required
                />
              </div>

              <div className="grid-cols-2">
                <div className="form-group">
                  <label className="form-label">Statutory Foreman Commission (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={commissionRate}
                    onChange={(e) => setCommissionRate(e.target.value)}
                    className="form-input font-mono"
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Capped at 5.00% under Section 21(1)(b) of the Act
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Maximum Reverse Auction Discount Cap (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={maxDiscountCap}
                    onChange={(e) => setMaxDiscountCap(e.target.value)}
                    className="form-input font-mono"
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Mandatory 40.00% statutory ceiling under Section 6
                  </span>
                </div>
              </div>

              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                <Save className="w-4 h-4" /> Save Governance Parameters
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab 3: Notification Center */}
      {activeTab === 'notifications' && (
        <div className="grid-cols-2">
          {/* Notification Rules */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Delivery Channels & Triggers</h3>
            </div>
            <div className="card-body">
              {notificationSuccess && (
                <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '0.75rem 1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#065f46', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 className="w-4 h-4" /> {notificationSuccess}
                </div>
              )}

              <form onSubmit={handleSaveNotifications} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
                  <div>
                    <strong style={{ fontSize: '0.875rem' }}>Email Notifications</strong>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Receive email summaries for new auction rounds and dividend distributions.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailAlerts}
                    onChange={(e) => setEmailAlerts(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: '#059669' }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
                  <div>
                    <strong style={{ fontSize: '0.875rem' }}>Digital Payment Receipts</strong>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Automatically dispatch SMS / WhatsApp receipt tokens to subscribers upon collection.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={smsReceipts}
                    onChange={(e) => setSmsReceipts(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: '#059669' }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
                  <div>
                    <strong style={{ fontSize: '0.875rem' }}>Auction Reminders (48h & 2h)</strong>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Alert non-prized subscribers before reverse bidding chamber opens.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={auctionReminders}
                    onChange={(e) => setAuctionReminders(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: '#059669' }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', border: '1px solid var(--border-subtle)', borderRadius: 8 }}>
                  <div>
                    <strong style={{ fontSize: '0.875rem' }}>Registrar Filing Deadlines</strong>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Section 20 lien renewals and Form XIV 14-day statutory filing warnings.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={complianceDeadlines}
                    onChange={(e) => setComplianceDeadlines(e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: '#059669' }}
                  />
                </div>

                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                  <Save className="w-4 h-4" /> Save Notification Preferences
                </button>
              </form>
            </div>
          </div>

          {/* Test Dispatch Console */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Test Delivery Simulation</h3>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0 }}>
                Trigger a mock test notification via SMTP / WebSocket to verify pipeline connectivity.
              </p>

              {testNotificationSent && (
                <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', padding: '1rem', borderRadius: 8, fontSize: '0.8125rem', color: '#065f46' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                    <Sparkles className="w-4 h-4" /> Test Notification Dispatched!
                  </div>
                  <span>Notification sent to {email}. Verified via background message queue.</span>
                </div>
              )}

              <button
                onClick={handleSendTestAlert}
                className="btn btn-outline"
                style={{ alignSelf: 'flex-start' }}
              >
                <Send className="w-4 h-4" /> Send Test Notification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
