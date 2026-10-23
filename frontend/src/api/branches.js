import client from './client'

export const branchesApi = {
  list: (params) => client.get('/branches', { params }),
  get: (id) => client.get(`/branches/${id}`),
  create: (data) => client.post('/branches', data),
  update: (id, data) => client.patch(`/branches/${id}`, data),
}
