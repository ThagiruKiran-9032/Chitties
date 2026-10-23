import React, { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export const DEMO_ACCOUNTS = {
  SUPER_ADMIN: {
    role: 'SUPER_ADMIN',
    label: 'Global Super Admin',
    email: 'superadmin@chitties.com',
    password: 'Admin@123',
    badge: 'Super Admin',
  },
  ORG_ADMIN: {
    role: 'ORG_ADMIN',
    label: 'Apex Chits Admin',
    email: 'admin@apexchits.com',
    password: 'Admin@123',
    badge: 'Org Admin',
  },
  BRANCH_MANAGER: {
    role: 'BRANCH_MANAGER',
    label: 'Bangalore Branch Manager',
    email: 'manager@apexchits.com',
    password: 'Admin@123',
    badge: 'Branch Mgr',
  },
  ACCOUNTANT: {
    role: 'ACCOUNTANT',
    label: 'Suresh Menon (Chief Accountant)',
    email: 'accountant@apexchits.com',
    password: 'Admin@123',
    badge: 'Accountant',
  },
  SUBSCRIBER: {
    role: 'SUBSCRIBER',
    label: 'Kiran Kumar (Ticket #1)',
    email: 'kiran.subscriber@gmail.com',
    password: 'Sub@123',
    badge: 'Subscriber',
  },
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('chitties_token'))
  const [loading, setLoading] = useState(true)

  // Verify and fetch profile on boot
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('chitties_token')
      if (!storedToken) {
        setLoading(false)
        return
      }

      try {
        const res = await authApi.getMe()
        setUser(res.data)
        setToken(storedToken)
      } catch (err) {
        console.warn('Session expired or invalid token. Clearing credentials.')
        localStorage.removeItem('chitties_token')
        setUser(null)
        setToken(null)
      } finally {
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  const login = async (email, password) => {
    const res = await authApi.login(email, password)
    const { access_token, user: userData } = res.data
    localStorage.setItem('chitties_token', access_token)
    setToken(access_token)
    setUser(userData)
    return userData
  }

  const register = async (registerData) => {
    const res = await authApi.register(registerData)
    return res.data
  }

  const forgotPassword = async (email) => {
    const res = await authApi.forgotPassword(email)
    return res.data
  }

  const resetPassword = async (token, newPassword) => {
    const res = await authApi.resetPassword(token, newPassword)
    return res.data
  }

  const quickDemoLogin = async (roleKey) => {
    const account = DEMO_ACCOUNTS[roleKey]
    if (!account) return

    try {
      return await login(account.email, account.password)
    } catch (err) {
      // If user doesn't exist yet, seed and retry
      try {
        await authApi.seedDemo()
        return await login(account.email, account.password)
      } catch (seedErr) {
        throw new Error('Demo login failed: ' + (err.response?.data?.detail || err.message))
      }
    }
  }

  const logout = () => {
    localStorage.removeItem('chitties_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        forgotPassword,
        resetPassword,
        quickDemoLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
