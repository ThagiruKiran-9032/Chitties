import client from './client'

export const complianceApi = {
  // Section 20 Security Deposits
  listDeposits: (params) => client.get('/compliance/deposits', { params }),
  lodgeDeposit: (data) => client.post('/compliance/deposits', data),
  verifyDeposit: (id, data) => client.patch(`/compliance/deposits/${id}/verify`, data),

  // Statutory Filings & Form XIV
  listFilings: (params) => client.get('/compliance/filings', { params }),
  recordFiling: (data) => client.post('/compliance/filings', data),
  updateFiling: (id, data) => client.patch(`/compliance/filings/${id}`, data),
  getFormXIV: (auctionId) => client.get(`/compliance/auctions/${auctionId}/form-xiv`),

  // Audit, Balance Sheets & Risk
  getBalanceSheet: (groupId) => client.get(`/compliance/groups/${groupId}/balance-sheet`),
  getDelinquencyReport: (groupId) => client.get(`/compliance/groups/${groupId}/delinquency-report`),
  getSystemSummary: () => client.get('/compliance/system-summary'),
}
