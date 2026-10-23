import client from './client'

export const membersApi = {
  list: (params) => client.get('/members', { params }),
  get: (id) => client.get(`/members/${id}`),
  onboard: (data) => client.post('/members', data),
  submitKyc: (id, data) => client.post(`/members/${id}/kyc`, data),
  updateKycStatus: (id, data) => client.patch(`/members/${id}/kyc-status`, data),
}
