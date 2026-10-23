import client from './client'

export const schemesApi = {
  list: (params) => client.get('/schemes', { params }),
  get: (id) => client.get(`/schemes/${id}`),
  create: (data) => client.post('/schemes', data),
  update: (id, data) => client.patch(`/schemes/${id}`, data),
}
