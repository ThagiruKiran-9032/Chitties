import client from './client'

export const groupsApi = {
  list: (params) => client.get('/groups', { params }),
  get: (id) => client.get(`/groups/${id}`),
  create: (data) => client.post('/groups', data),
  updateStatus: (id, status) => client.patch(`/groups/${id}/status`, { status }),
  enroll: (id, data) => client.post(`/groups/${id}/enroll`, data),
  removeMember: (id, membershipId) => client.delete(`/groups/${id}/enroll/${membershipId}`),
  getMemberships: (id) => client.get(`/groups/${id}/memberships`),
}
