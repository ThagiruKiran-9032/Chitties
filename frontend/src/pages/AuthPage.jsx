import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Lock,
  Mail,
  User,
  Phone,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Building,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react'
import { useAuth, DEMO_ACCOUNTS } from '../context/AuthContext'
import { getRoleHomeRoute } from '../utils/rbac'

export default function AuthPage() {
  const { login, register, forgotPassword, resetPassword, quickDemoLogin } = useAuth()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('login') // 'login' | 'register' | 'forgot' | 'reset'

  // Login form state
  const [loginEmail, setLoginEmail] = useState('admin@apexchits.com')
  const [loginPassword, setLoginPassword] = useState('Admin@123')
  const [showPassword, setShowPassword] = useState(false)

  // Registration form state
  const [regFullName, setRegFullName] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPhone, setRegPhone] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regOrgName, setRegOrgName] = useState('Apex Chits International')

  // Password recovery state
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')

  // UI state
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    setLoading(true)

    try {
      const userData = await login(loginEmail, loginPassword)
      const target = getRoleHomeRoute(userData)
      navigate(target, { replace: true })
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Login failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    setLoading(true)

    try {
      await register({
        full_name: regFullName,
        email: regEmail,
        phone: regPhone,
        password: regPassword,
      })
      setSuccessMsg('Account created successfully! You can now log in.')
      setActiveTab('login')
      setLoginEmail(regEmail)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    setLoading(true)

    try {
      await forgotPassword(recoveryEmail)
      setSuccessMsg(`Password recovery token sent to ${recoveryEmail}. Please check inbox or use token to reset.`)
      setActiveTab('reset')
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to send recovery token.')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    setLoading(true)

    try {
      await resetPassword(resetToken, newPassword)
      setSuccessMsg('Password has been successfully updated! Please log in.')
      setActiveTab('login')
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to reset password.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoClick = async (roleKey) => {
    setErrorMsg('')
    setSuccessMsg('')
    setDemoLoading(roleKey)
    try {
      const userData = await quickDemoLogin(roleKey)
      const target = getRoleHomeRoute(userData)
      navigate(target, { replace: true })
    } catch (err) {
      setErrorMsg(err.message || 'Demo login failed.')
    } finally {
      setDemoLoading('')
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-app)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1rem',
      }}
    >
      {/* Brand Logo Header */}
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: 'var(--radius-lg)',
            background: 'linear-gradient(135deg, var(--emerald-500), var(--emerald-800))',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            fontWeight: 800,
            margin: '0 auto 0.75rem',
            boxShadow: '0 4px 14px rgba(4, 120, 87, 0.3)',
          }}
        >
          Ch
        </div>
        <h1 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--text-primary)' }}>
          Chitties
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
          Enterprise Chit Fund & Reverse Auction Management Platform
        </p>
      </div>

      {/* Main Auth Card (Clean White on Neutral Background) */}
      <div
        className="card"
        style={{
          maxWidth: '460px',
          width: '100%',
          boxShadow: 'var(--shadow-xl)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
        }}
      >
        {/* Navigation Tabs Header */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: '#fafbfc',
          }}
        >
          <button
            onClick={() => { setActiveTab('login'); setErrorMsg(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '0.875rem',
              fontSize: '0.8125rem',
              fontWeight: 700,
              color: activeTab === 'login' ? 'var(--emerald-700)' : 'var(--text-muted)',
              borderBottom: activeTab === 'login' ? '2px solid var(--emerald-600)' : 'none',
              backgroundColor: activeTab === 'login' ? '#ffffff' : 'transparent',
            }}
          >
            Sign In
          </button>
          <button
            onClick={() => { setActiveTab('register'); setErrorMsg(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '0.875rem',
              fontSize: '0.8125rem',
              fontWeight: 700,
              color: activeTab === 'register' ? 'var(--emerald-700)' : 'var(--text-muted)',
              borderBottom: activeTab === 'register' ? '2px solid var(--emerald-600)' : 'none',
              backgroundColor: activeTab === 'register' ? '#ffffff' : 'transparent',
            }}
          >
            Register
          </button>
          <button
            onClick={() => { setActiveTab('forgot'); setErrorMsg(''); setSuccessMsg(''); }}
            style={{
              flex: 1,
              padding: '0.875rem',
              fontSize: '0.8125rem',
              fontWeight: 700,
              color: activeTab === 'forgot' ? 'var(--emerald-700)' : 'var(--text-muted)',
              borderBottom: activeTab === 'forgot' ? '2px solid var(--emerald-600)' : 'none',
              backgroundColor: activeTab === 'forgot' ? '#ffffff' : 'transparent',
            }}
          >
            Recover
          </button>
        </div>

        <div className="card-body" style={{ padding: '2rem' }}>
          {/* Feedback Messages */}
          {errorMsg && (
            <div className="alert-banner alert-warning" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div
              className="alert-banner"
              style={{
                backgroundColor: 'var(--status-success-bg)',
                borderColor: 'var(--status-success-border)',
                color: 'var(--status-success-text)',
                marginBottom: '1.25rem',
              }}
            >
              <CheckCircle2 size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* TAB 1: LOGIN FORM */}
          {activeTab === 'login' && (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label className="form-label form-label-required">Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type="email"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem' }}
                  />
                </div>
              </div>

              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="form-label form-label-required">Password</label>
                  <button
                    type="button"
                    onClick={() => setActiveTab('forgot')}
                    style={{ fontSize: '0.75rem', color: 'var(--emerald-700)', fontWeight: 600 }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your account password"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem', paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '10px',
                      color: 'var(--text-muted)',
                      padding: '2px',
                    }}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem', padding: '0.6875rem' }}
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                <span>{loading ? 'Authenticating...' : 'Sign In to Chitties'}</span>
              </button>
            </form>
          )}

          {/* TAB 2: REGISTRATION FORM */}
          {activeTab === 'register' && (
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label className="form-label form-label-required">Full Legal Name</label>
                <div style={{ position: 'relative' }}>
                  <User
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type="text"
                    required
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. Anand Mahindra"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem' }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label form-label-required">Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="anand@example.com"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem' }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <div style={{ position: 'relative' }}>
                  <Phone
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type="tel"
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem' }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label form-label-required">Create Password</label>
                <div style={{ position: 'relative' }}>
                  <Lock
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem', paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '10px',
                      color: 'var(--text-muted)',
                      padding: '2px',
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem', padding: '0.6875rem' }}
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                <span>{loading ? 'Creating Account...' : 'Complete Subscriber Registration'}</span>
              </button>
            </form>
          )}

          {/* TAB 3: FORGOT PASSWORD */}
          {activeTab === 'forgot' && (
            <form onSubmit={handleForgotPassword}>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
                Enter your registered email address and we'll dispatch an official password reset token.
              </p>
              <div className="form-group">
                <label className="form-label form-label-required">Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail
                    size={16}
                    color="var(--text-light)"
                    style={{ position: 'absolute', left: '12px', top: '12px', pointerEvents: 'none' }}
                  />
                  <input
                    type="email"
                    required
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    placeholder="registered@email.com"
                    className="form-input"
                    style={{ paddingLeft: '2.4rem' }}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem' }}
              >
                {loading ? 'Sending...' : 'Send Recovery Token'}
              </button>
            </form>
          )}

          {/* TAB 4: RESET PASSWORD */}
          {activeTab === 'reset' && (
            <form onSubmit={handleResetPassword}>
              <div className="form-group">
                <label className="form-label form-label-required">Reset Token</label>
                <input
                  type="text"
                  required
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="Paste token received in email"
                  className="form-input font-mono"
                />
              </div>

              <div className="form-group">
                <label className="form-label form-label-required">New Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter strong password"
                  className="form-input"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem' }}
              >
                {loading ? 'Updating...' : 'Set New Password'}
              </button>
            </form>
          )}

          {/* 1-Click Demo Profiles for Rapid Testing */}
          <div
            style={{
              marginTop: '1.75rem',
              paddingTop: '1.25rem',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                1-Click Demo Sign-In
              </span>
              <span className="badge badge-success" style={{ fontSize: '0.625rem' }}>
                Instant Access
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
              {Object.entries(DEMO_ACCOUNTS).map(([key, acc]) => (
                <button
                  key={key}
                  type="button"
                  disabled={demoLoading !== ''}
                  onClick={() => handleDemoClick(key)}
                  className="btn btn-outline btn-sm"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '0.5rem 0.625rem',
                    textAlign: 'left',
                    height: 'auto',
                    backgroundColor: '#ffffff',
                  }}
                >
                  <span style={{ fontWeight: 700, fontSize: '0.75rem', color: 'var(--emerald-800)' }}>
                    {demoLoading === key ? 'Logging in...' : acc.badge}
                  </span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{acc.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <p style={{ marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Strictly compliant with the Chit Funds Act, 1982 &bull; Enterprise Encryption
      </p>
    </div>
  )
}
