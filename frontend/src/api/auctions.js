import client from './client'

export const auctionsApi = {
  list: (params) => client.get('/auctions', { params }),
  getGroupAuctions: (groupId) => client.get(`/auctions/group/${groupId}`),
  getAuctionDetail: (auctionId) => client.get(`/auctions/${auctionId}`),
  startAuction: (auctionId) => client.post(`/auctions/${auctionId}/start`),
  placeBid: (auctionId, bidDiscountAmount, chitMembershipId = null) =>
    client.post(`/auctions/${auctionId}/bids`, {
      bid_discount_amount: bidDiscountAmount,
      chit_membership_id: chitMembershipId,
    }),
  getAuctionBids: (auctionId) => client.get(`/auctions/${auctionId}/bids`),
  closeAuction: (auctionId) => client.post(`/auctions/${auctionId}/close`),
}

export const getAuctionWsUrl = (auctionId) => {
  const isSecure = window.location.protocol === 'https:'
  const protocol = isSecure ? 'wss:' : 'ws:'
  const host = window.location.host
  const token = localStorage.getItem('chitties_token') || ''
  return `${protocol}//${host}/api/v1/auctions/ws/${auctionId}?token=${encodeURIComponent(token)}`
}
