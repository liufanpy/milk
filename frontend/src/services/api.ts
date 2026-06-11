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
  list: (keyword = '', priceTier = '') => api.get('/customers', { params: { keyword, price_tier: priceTier } }).then(r => r.data),
  get: (id: number) => api.get(`/customers/${id}`).then(r => r.data),
  create: (data: any) => api.post('/customers', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/customers/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/customers/${id}`),
  getPrices: (id: number) => api.get(`/customers/${id}/prices`).then(r => r.data),
  addPrice: (customerId: number, productId: number, price: number) =>
    api.post(`/customers/${customerId}/prices?product_id=${productId}&price=${price}`).then(r => r.data),
  deletePrice: (customerId: number, priceId: number) => api.delete(`/customers/${customerId}/prices/${priceId}`),
  resolvePrice: (customerId: number, productId: number) =>
    api.get(`/customers/${customerId}/resolve-price`, { params: { product_id: productId } }).then(r => r.data),
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

// Purchases
export const purchaseApi = {
  create: (data: any) => api.post('/purchases', data).then(r => r.data),
  list: () => api.get('/purchases').then(r => r.data),
  get: (id: number) => api.get(`/purchases/${id}`).then(r => r.data),
  confirm: (id: number, items?: any[]) => api.post(`/purchases/${id}/confirm`, { items }).then(r => r.data),
  cancel: (id: number) => api.post(`/purchases/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/purchases/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/purchases/import/confirm', { rows }).then(r => r.data),
};

// Sales
export const saleApi = {
  create: (data: any) => api.post('/sales', data).then(r => r.data),
  list: () => api.get('/sales').then(r => r.data),
  get: (id: number) => api.get(`/sales/${id}`).then(r => r.data),
  pay: (id: number) => api.post(`/sales/${id}/pay`).then(r => r.data),
  cancel: (id: number) => api.post(`/sales/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/sales/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/sales/import/confirm', { rows }).then(r => r.data),
};

// Distribution Orders (铺货管理)
export const distributionApi = {
  create: (data: any) => api.post('/distribution-orders', data).then(r => r.data),
  list: (params?: any) => api.get('/distribution-orders', { params }).then(r => r.data),
  get: (id: number) => api.get(`/distribution-orders/${id}`).then(r => r.data),
  exchange: (id: number, data: any) => api.post(`/distribution-orders/${id}/exchange`, data).then(r => r.data),
  settle: (id: number, amount: number) => api.post(`/distribution-orders/${id}/settle`, { amount }).then(r => r.data),
  batchSettle: (customerId: number, items: any[]) => api.post('/distribution-orders/batch-settle', { customer_id: customerId, items }).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/distribution-orders/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/distribution-orders/import/confirm', { rows }).then(r => r.data),
};

// Returns
export const returnApi = {
  create: (data: any) => api.post('/returns', data).then(r => r.data),
  list: () => api.get('/returns').then(r => r.data),
  get: (id: number) => api.get(`/returns/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/returns/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/returns/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/returns/import/confirm', { rows }).then(r => r.data),
};

// Wastage
export const wastageApi = {
  create: (data: any) => api.post('/wastage', data).then(r => r.data),
  list: () => api.get('/wastage').then(r => r.data),
  get: (id: number) => api.get(`/wastage/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/wastage/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/wastage/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/wastage/import/confirm', { rows }).then(r => r.data),
};

// Inventory
export const inventoryApi = {
  list: () => api.get('/inventory').then(r => r.data),
};

// Subscription
export const subscriptionApi = {
  create: (data: any) => api.post('/subscription-orders', data).then(r => r.data),
  deduct: (id: number, data: any) => api.post(`/subscription-orders/${id}/deduct`, data).then(r => r.data),
  list: () => api.get('/subscription-orders').then(r => r.data),
  get: (id: number) => api.get(`/subscription-orders/${id}`).then(r => r.data),
};

// Dashboard & queries
export const dashboardApi = {
  get: (date_from: string, date_to: string) =>
    api.get('/dashboard', { params: { date_from, date_to } }).then(r => r.data),
  getReceivables: () => api.get('/receivables').then(r => r.data),
  getInventory: () => api.get('/inventory').then(r => r.data),
  getOperationLogs: () => api.get('/operation-logs').then(r => r.data),
};

// Stores
export const storeApi = {
  list: () => api.get('/stores').then(r => r.data),
  get: (id: number) => api.get(`/stores/${id}`).then(r => r.data),
  create: (data: any) => api.post('/stores', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/stores/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/stores/${id}`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/stores/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/stores/import/confirm', { rows }).then(r => r.data),
};

// Store Sales (巡店记录)
export const storeSalesApi = {
  create: (data: any) => api.post('/store-sales', data).then(r => r.data),
  list: (params?: any) => api.get('/store-sales', { params }).then(r => r.data),
  get: (id: number) => api.get(`/store-sales/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/store-sales/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/store-sales/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/store-sales/import/confirm', { rows }).then(r => r.data),
};

// Ledger queries
export const ledgerApi = {
  stock: (params?: any) => api.get('/stock-ledger', { params }).then(r => r.data),
  transactions: (params?: any) => api.get('/transaction-ledger', { params }).then(r => r.data),
};
