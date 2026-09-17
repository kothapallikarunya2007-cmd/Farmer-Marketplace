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

  const demoCheckout = window.placeOrder;
  window.placeOrder = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const selected = event.currentTarget.querySelector('input[name="slot"]:checked');
    try {
      const order = await request('/api/orders', {method: 'POST', body: JSON.stringify({
        customer: {name: form.get('name') || event.currentTarget.querySelector('input[type="text"]')?.value || 'Customer', phone: form.get('phone') || event.currentTarget.querySelector('input[type="tel"]')?.value || ''},
        address: event.currentTarget.querySelector('textarea')?.value || '',
        delivery_window: selected?.parentElement?.textContent.trim() || 'Today, 6–8 PM',
        special_instructions: event.currentTarget.querySelectorAll('input[type="text"]')[1]?.value || '',
        items: cart.map(item => ({product_id: item.id, quantity: item.qty}))
      })});
      localStorage.setItem('fh-lastOrder', order.order_number);
      cart = []; persist(); showModal(order.order_number);
    } catch (error) {
      toast(error.message + ' Using demo checkout instead.');
      demoCheckout(event);
    }
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
