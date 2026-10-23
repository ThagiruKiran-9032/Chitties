import client from './client'

export const payoutsApi = {
  list: (params) => client.get('/payouts', { params }),
  getAuctionPayout: (auctionId) => client.get(`/payouts/auction/${auctionId}`),
  addSurety: (payoutId, data) => client.post(`/payouts/${payoutId}/sureties`, data),
  verifySurety: (suretyId, data) => client.patch(`/payouts/sureties/${suretyId}/verify`, data),
  disburse: (payoutId, data) => client.post(`/payouts/${payoutId}/disburse`, data),
  substitute: (data) => client.post('/payouts/substitute', data),
}
