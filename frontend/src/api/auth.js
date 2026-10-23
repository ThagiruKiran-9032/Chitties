import client from './client'

export const authApi = {
  login: (email, password) => client.post('/auth/login', { email, password }),
  register: (data) => client.post('/auth/register', data),
  getMe: () => client.get('/auth/me'),
  seedDemo: () => client.post('/auth/seed-demo'),
  forgotPassword: (email) => client.post('/auth/forgot-password', { email }),
  resetPassword: (token, new_password) => client.post('/auth/reset-password', { token, new_password }),
  verifyEmail: (token) => client.post('/auth/verify-email', { token }),
}
