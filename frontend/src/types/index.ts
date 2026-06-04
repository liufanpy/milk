export interface Product {
  id: number;
  name: string;
  brand: string;
  category: string;
  unit: string;
  barcode: string;
  spec: string;
  default_purchase_price: number;
  default_retail_price: number;
  default_wholesale_price: number;
  shelf_life_days: number;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  contact: string;
  address: string;
  price_tier: string;
  default_payment: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact: string;
  phone: string;
}

export interface Shelf {
  id: number;
  name: string;
  customer_id: number | null;
}

export interface Delivery {
  id: number;
  customer_id: number;
  delivery_date: string;
  status: string;
  total_amount: number;
  paid_amount: number;
  unpaid_amount: number;
  note: string;
  items?: DeliveryItem[];
  transactions?: Transaction[];
}

export interface DeliveryItem {
  product_id: number;
  quantity: number;
  reason?: string;
  direction?: string;
}

export interface Transaction {
  id: number;
  category: string;
  amount: number;
  created_at: string;
}

export interface StockMovement {
  id: number;
  product_id: number;
  shelf_id: number;
  direction: string;
  reason: string;
  quantity: number;
}

export interface SubscriptionOrder {
  id: number;
  customer_id: number;
  total_amount: number;
  total_bottles: number;
  remaining_bottles: number;
  status: string;
}

export interface ProductCustomerPrice {
  id: number;
  product_id: number;
  customer_id: number;
  price: number;
}

export interface CreateProductData {
  name: string;
  brand?: string;
  category?: string;
  unit?: string;
  spec?: string;
  default_purchase_price?: number;
  default_retail_price?: number;
  default_wholesale_price?: number;
  shelf_life_days?: number;
}

export interface CreateCustomerData {
  name: string;
  phone?: string;
  contact?: string;
  address?: string;
  price_tier?: string;
  default_payment?: string;
}

export interface PurchaseItem {
  product_id: number;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
}

export interface SaleItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
}

export interface DeliveryCreateItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
}

export interface PurchaseOrder {
  id: number;
  order_number: string;
  supplier_id: number;
  supplier_name: string;
  purchase_date: string;
  total_amount: number;
  status: string;
  note: string;
  created_at: string;
}

export interface PurchaseOrderDetail extends PurchaseOrder {
  items: PurchaseOrderDetailItem[];
}

export interface PurchaseOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
  shelf_name: string;
}
