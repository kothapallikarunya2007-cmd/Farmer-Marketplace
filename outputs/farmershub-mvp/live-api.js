(() => {
  const API = (window.FARMERSHUB_API_URL || '').replace(/\/$/, '');
  const statusMap = {New: 'pending', Confirmed: 'confirmed', Ready: 'ready', Delivered: 'delivered', Declined: 'declined'};
  async function request(path, options = {}) {
    if (!API) throw new Error('Backend URL is not configured. Set it in api-config.js.');
    const response = await fetch(API + path, {headers: {'Content-Type': 'application/json', ...(options.headers || {})}, ...options});
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) throw new Error(body?.error || 'The server could not complete that request.');
    return body;
  }
  const imageFor = item => item.image_url || item.photo_url || 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=500&q=80';
  const mapOrder = order => ({id: order.order_number, customer: order.customer_name || 'Customer', items: (order.items || []).map(item => `${item.quantity}${item.unit ? ` ${item.unit}` : ''} ${item.name}`).join(', '), total: order.total, status: {pending: 'New', confirmed: 'Confirmed', ready: 'Ready', delivered: 'Delivered', declined: 'Declined'}[order.status] || order.status, time: order.created_at || ''});
  async function loadLiveData() {
    if (!API) return;
    const farmerRows = await request('/api/farmers');
    const farmerProducts = await Promise.all(farmerRows.map(farmer => request(`/api/farmers/${farmer.id}/products`)));
    farmers.splice(0, farmers.length, ...farmerRows.map(farmer => ({id: farmer.id, name: farmer.name, village: farmer.village, rating: String(farmer.rating), reviews: farmer.review_count, products: farmer.product_count, img: imageFor(farmer), bio: farmer.bio || ''})));
    products.splice(0, products.length, ...farmerProducts.flat().map(product => ({id: product.id, farmer: product.farmer_id, name: product.name, category: product.category, price: product.price, unit: product.unit, stock: product.stock, img: imageFor(product)})));
    const orderRows = await request('/api/farmers/1/orders');
    orders.splice(0, orders.length, ...orderRows.map(mapOrder));
    render();
  }
  window.placeOrder = async event => {
    event.preventDefault();
    try {
      const form = new FormData(event.currentTarget), selected = event.currentTarget.querySelector('input[name="slot"]:checked');
      const order = await request('/api/orders', {method: 'POST', body: JSON.stringify({customer: {name: form.get('name') || event.currentTarget.querySelector('input[type="text"]')?.value || 'Customer', phone: form.get('phone') || event.currentTarget.querySelector('input[type="tel"]')?.value || ''}, address: event.currentTarget.querySelector('textarea')?.value || '', delivery_window: selected?.parentElement?.textContent.trim() || 'Today, 6-8 PM', special_instructions: event.currentTarget.querySelectorAll('input[type="text"]')[1]?.value || '', items: cart.map(item => ({product_id: item.id, quantity: item.qty}))})});
      localStorage.setItem('fh-lastOrder', order.order_number); cart = []; persist(); showModal(order.order_number);
    } catch (error) { toast(error.message); }
  };
  window.updateOrder = async (orderNumber, status) => {
    try {
      await request(`/api/orders/${encodeURIComponent(orderNumber)}/status`, {method: 'PATCH', body: JSON.stringify({status: statusMap[status] || status.toLowerCase()})});
      const updated = await request('/api/farmers/1/orders'); orders.splice(0, orders.length, ...updated.map(mapOrder)); render(); toast(`Order ${status.toLowerCase()}.`);
    } catch (error) { toast(error.message); }
  };
  window.addProduct = payload => request('/api/farmers/1/products', {method: 'POST', body: JSON.stringify(payload)});
  window.editProduct = (productId, payload) => request(`/api/farmers/1/products/${productId}`, {method: 'PATCH', body: JSON.stringify(payload)});
  window.deleteProduct = productId => request(`/api/farmers/1/products/${productId}`, {method: 'DELETE'});
  window.productManagement = () => `${nav()}<main class="shell"><div class="section-head"><div><h1 class="page-title">My products</h1><p class="sub">Manage the products customers see in your store.</p></div></div><section class="card"><form onsubmit="saveProduct(event)" class="formgrid"><div class="field"><label>Product name</label><input name="name" required></div><div class="field"><label>Category</label><input name="category" required value="Vegetables"></div><div class="field"><label>Price</label><input name="price" type="number" min="0" step="0.01" required></div><div class="field"><label>Unit</label><input name="unit" required value="kg"></div><div class="field"><label>Stock</label><input name="stock" type="number" min="0" required></div><div class="field"><label>Image URL</label><input name="image_url"></div><div class="field full"><label>Description</label><input name="description"></div><div class="field full"><button class="primary" type="submit">Add product</button></div></form></section><section class="card"><table class="table"><thead><tr><th>PRODUCT</th><th>PRICE</th><th>STOCK</th><th>STATUS</th><th></th></tr></thead><tbody>${products.map(p => `<tr><td><div class="product-row"><img src="${p.img}" alt=""><b>${p.name}</b></div></td><td>${money(p.price)}/${p.unit}</td><td><span class="badge ${p.stock < 10 ? 'red' : 'green'}">${p.stock} available</span></td><td><span class="badge green">Active</span></td><td><button class="linkbtn" onclick="editExistingProduct(${p.id})">Edit</button> <button class="linkbtn" onclick="removeProduct(${p.id})">Delete</button></td></tr>`).join('')}</tbody></table></section></main>${footer()}`;
  window.saveProduct = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); data.price = Number(data.price); data.stock = Number(data.stock); try { await addProduct(data); await loadLiveData(); toast('Product added.'); } catch (error) { toast(error.message); } };
  window.editExistingProduct = async productId => { const product = products.find(item => item.id === productId); const price = prompt(`Price for ${product.name}`, product.price); const stock = prompt(`Stock for ${product.name}`, product.stock); if (price === null || stock === null) return; try { await editProduct(productId, {price: Number(price), stock: Number(stock)}); await loadLiveData(); toast('Product updated.'); } catch (error) { toast(error.message); } };
  window.removeProduct = async productId => { if (!confirm('Remove this product from the store?')) return; try { await deleteProduct(productId); await loadLiveData(); toast('Product removed.'); } catch (error) { toast(error.message); } };
  window.loadFarmersHubData = loadLiveData;
  loadLiveData().catch(error => toast(error.message));
})();