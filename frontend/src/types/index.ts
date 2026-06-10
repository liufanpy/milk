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

export interface DistributionOrder {
  id: number;
  order_number: string;
  customer_id: number;
  delivery_date: string;
  status: string;
  total_amount: number;
  paid_amount: number;
  unpaid_amount: number;
  note: string;
  items?: DistributionOrderItem[];
  transactions?: Transaction[];
}

export interface DistributionOrderItem {
  product_id: number;
  quantity: number;
  unit_price?: number;
  type?: string;
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
  direction: string;
  quantity: number;
}

export interface SubscriptionOrder {
  id: number;
  customer_id: number;
  paid_amount: number;
  remaining_amount: number;
  note: string;
  status: string;
  created_at: string;
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

export interface SaleItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

export interface DistributionCreateItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

export interface PurchaseItem {
  product_id: number;
  quantity: number;
  unit_price: number;
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
  unit_price: number;
}

export interface RetailOrder {
  id: number;
  customer_id: number | null;
  customer_name: string;
  item_count: number;
  total_amount: number;
  paid: boolean;
  status: string;
  items_summary: string;
  created_at: string;
}

export interface RetailOrderDetail extends RetailOrder {
  items: RetailOrderDetailItem[];
}

export interface RetailOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}

export interface Store {
  id: number;
  name: string;
  customer_id: number | null;
  customer_name: string;
  address: string;
  status: string;
  created_at: string;
}

export interface StoreSalesOrder {
  id: number;
  order_number: string;
  store_id: number;
  store_name: string;
  check_date: string;
  status: string;
  item_count: number;
  note: string;
  created_at: string;
}

export interface StoreSalesItem {
  product_id: number;
  product_name?: string;
  actual_quantity: number;
}

export interface StoreSalesDetail extends StoreSalesOrder {
  items: any[];
}
