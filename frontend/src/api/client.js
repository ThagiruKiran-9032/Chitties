import axios from 'axios'

const API_BASE = '/api/v1'

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to inject JWT bearer token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('chitties_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle token expiration & 401 Unauthorized
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isPublicAuth =
        error.config?.url?.includes('/auth/login') ||
        error.config?.url?.includes('/auth/seed-demo') ||
        error.config?.url?.includes('/auth/register') ||
        error.config?.url?.includes('/auth/forgot-password') ||
        error.config?.url?.includes('/auth/reset-password')
      if (!isPublicAuth) {
        localStorage.removeItem('chitties_token')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
