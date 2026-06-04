import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Products
export const productApi = {
  list: (keyword = '') => api.get('/products', { params: { keyword } }).then(r => r.data),
  get: (id: number) => api.get(`/products/${id}`).then(r => r.data),
  create: (data: any) => api.post('/products', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/products/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/products/${id}`),
  importFile: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/products/import', fd).then(r => r.data);
  },
  confirmImport: (rows: any[]) => api.post('/products/import/confirm', { rows }).then(r => r.data),
};

// Customers
export const customerApi = {
  list: (keyword = '') => api.get('/customers', { params: { keyword } }).then(r => r.data),
  get: (id: number) => api.get(`/customers/${id}`).then(r => r.data),
  create: (data: any) => api.post('/customers', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/customers/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/customers/${id}`),
  getPrices: (id: number) => api.get(`/customers/${id}/prices`).then(r => r.data),
  addPrice: (customerId: number, productId: number, price: number) =>
    api.post(`/customers/${customerId}/prices?product_id=${productId}&price=${price}`).then(r => r.data),
  deletePrice: (customerId: number, priceId: number) => api.delete(`/customers/${customerId}/prices/${priceId}`),
  importFile: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/customers/import', fd).then(r => r.data);
  },
  confirmImport: (rows: any[]) => api.post('/customers/import/confirm', { rows }).then(r => r.data),
};

// Suppliers
export const supplierApi = {
  list: (keyword = '') => api.get('/suppliers', { params: { keyword } }).then(r => r.data),
  create: (data: any) => api.post('/suppliers', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/suppliers/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/suppliers/${id}`),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/suppliers/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/suppliers/import/confirm', { rows }).then(r => r.data),
};

// Shelves
export const shelfApi = {
  list: () => api.get('/shelves').then(r => r.data),
  create: (data: any) => api.post('/shelves', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/shelves/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/shelves/${id}`),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/shelves/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/shelves/import/confirm', { rows }).then(r => r.data),
};

// Purchases
export const purchaseApi = {
  create: (data: any) => api.post('/purchases', data).then(r => r.data),
  list: () => api.get('/purchases').then(r => r.data),
};

// Sales
export const saleApi = {
  create: (data: any) => api.post('/sales', data).then(r => r.data),
  list: () => api.get('/sales').then(r => r.data),
};

// Deliveries
export const deliveryApi = {
  create: (data: any) => api.post('/deliveries', data).then(r => r.data),
  list: (params?: any) => api.get('/deliveries', { params }).then(r => r.data),
  get: (id: number) => api.get(`/deliveries/${id}`).then(r => r.data),
  exchange: (id: number, data: any) => api.post(`/deliveries/${id}/exchange`, data).then(r => r.data),
  settle: (id: number, amount: number) => api.post(`/deliveries/${id}/settle`, { amount }).then(r => r.data),
};

// Returns
export const returnApi = {
  create: (data: any) => api.post('/returns', data).then(r => r.data),
  list: () => api.get('/returns').then(r => r.data),
};

// Wastage
export const wastageApi = {
  create: (data: any) => api.post('/wastage', data).then(r => r.data),
  list: () => api.get('/wastage').then(r => r.data),
};

// Subscription
export const subscriptionApi = {
  create: (data: any) => api.post('/subscription-orders', data).then(r => r.data),
  deduct: (id: number, data: any) => api.post(`/subscription-orders/${id}/deduct`, data).then(r => r.data),
  list: () => api.get('/subscription-orders').then(r => r.data),
};

// Dashboard & queries
export const dashboardApi = {
  get: () => api.get('/dashboard').then(r => r.data),
  getReceivables: () => api.get('/receivables').then(r => r.data),
  getInventory: () => api.get('/inventory').then(r => r.data),
  getOperationLogs: () => api.get('/operation-logs').then(r => r.data),
};
