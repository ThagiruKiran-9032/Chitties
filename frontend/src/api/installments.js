import client from './client'

export const installmentsApi = {
  getGroupInstallments: (groupId, params) => client.get(`/installments/group/${groupId}`, { params }),
  getMemberLedger: (membershipId) => client.get(`/installments/membership/${membershipId}`),
  applyPenalty: (installmentId, data) => client.post(`/installments/${installmentId}/penalty`, data),
}

export default installmentsApi
