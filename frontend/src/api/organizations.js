import client from './client'

export const organizationsApi = {
  list: (params) => client.get('/organizations', { params }),
  get: (id) => client.get(`/organizations/${id}`),
  create: (data) => client.post('/organizations', data),
  update: (id, data) => client.patch(`/organizations/${id}`, data),
}
