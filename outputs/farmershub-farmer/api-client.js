/* Set window.FARMERSHUB_API_URL before this script in production, for example:
   window.FARMERSHUB_API_URL = 'https://api.farmershub.in'; */
(() => {
  const API = window.FARMERSHUB_API_URL || 'http://localhost:5000';
  const request = async (path, options = {}) => {
    const response = await fetch(API + path, {headers: {'Content-Type': 'application/json'}, ...options});
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) throw new Error(body?.error || 'The server could not complete that request.');
    return body;
  };
  const demoStatusUpdate = window.updateOrder;
  window.updateOrder = async (orderNumber, status) => {
    const serverStatus = {New: 'pending', Confirmed: 'confirmed', Ready: 'ready', Delivered: 'delivered', Declined: 'declined'}[status] || status.toLowerCase();
    try {
      await request(`/api/orders/${encodeURIComponent(orderNumber)}/status`, {method: 'PATCH', body: JSON.stringify({status: serverStatus})});
      demoStatusUpdate(orderNumber, status);
    } catch (error) {
      toast(error.message + ' Using demo order state instead.');
      demoStatusUpdate(orderNumber, status);
    }
  };
})();
