import { useState, useEffect } from 'react';
import { OrderListTable } from '../components/business/OrderListTable';
import { ProductSelect } from '../components/business/ProductSelect';
import { ledgerApi } from '../services/api';

const DIR_OPTIONS = ['', 'in', 'out'];
const DIR_LABELS: Record<string, string> = { '': '全部', in: '入库', out: '出库' };
const REASON_OPTIONS = ['', 'purchase', 'retail', 'distribution', 'subscription', 'return', 'wastage', 'cancel', 'exchange', 'promo', 'inventory_check'];

export default function StockLedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [productId, setProductId] = useState<number | string>('');
  const [direction, setDirection] = useState('');
  const [reason, setReason] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [storeId, setStoreId] = useState<number | string>('');
  const [orderNumber, setOrderNumber] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [productId, storeId, direction, reason, dateFrom, dateTo, orderNumber]);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (productId) params.product_id = Number(productId);
      if (storeId) params.store_id = Number(storeId);
      if (direction) params.direction = direction;
      if (reason) params.reason = reason;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (orderNumber) params.order_number = orderNumber;
      const data = await ledgerApi.stock(params);
      setRows(data);
    } finally { setLoading(false); }
  };

  const columns = [
    { key: 'created_at', title: '时间', render: (r: any) => r.created_at?.slice(0, 19).replace('T', ' ') },
    { key: 'product_name', title: '产品' },
    { key: 'direction', title: '方向', render: (r: any) => (
      <span className={r.direction === 'in' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
        {r.direction === 'in' ? '入库' : '出库'}
      </span>
    )},
    { key: 'quantity', title: '数量', render: (r: any) => <span className="font-medium">{r.quantity}</span> },
    { key: 'balance', title: '库存余额', render: (r: any) => <span className="font-bold">{r.balance}</span> },
    { key: 'reason', title: '原因' },
    { key: 'order_number', title: '关联单号' },
    { key: 'unit_price', title: '单价', render: (r: any) => r.unit_price ? `¥${r.unit_price.toFixed(2)}` : '' },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">库存流水</h2>
      <div className="flex gap-3 mb-4 flex-wrap">
        <input type="number" placeholder="店铺ID" value={storeId} onChange={(e) => setStoreId(e.target.value ? Number(e.target.value) : '')} className="border rounded px-3 py-2 text-sm w-24" />
        <div className="w-48">
          <ProductSelect value={productId} onChange={(v) => setProductId(v)} />
        </div>
        <select value={direction} onChange={(e) => setDirection(e.target.value)} className="border rounded px-3 py-2 text-sm">
          {DIR_OPTIONS.map(d => <option key={d} value={d}>{DIR_LABELS[d]}</option>)}
        </select>
        <select value={reason} onChange={(e) => setReason(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">全部原因</option>
          {REASON_OPTIONS.filter(r => r).map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <span className="text-gray-400 self-center">~</span>
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <input type="text" placeholder="单号" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} className="border rounded px-3 py-2 text-sm w-40" />
      </div>
      <OrderListTable columns={columns} data={rows} rowKey={(r) => r.id} isLoading={loading} />
    </div>
  );
}
