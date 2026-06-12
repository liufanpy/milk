import { useState, useEffect } from 'react';
import { OrderListTable } from '../components/business/OrderListTable';
import { ProductSelect } from '../components/business/ProductSelect';
import { StoreSelect } from '../components/business/StoreSelect';
import { ledgerApi } from '../services/api';

const DIR_OPTIONS = ['', 'in', 'out'];
const DIR_LABELS: Record<string, string> = { '': '全部', in: '入库', out: '出库' };
const SOURCE_OPTIONS = ['', 'purchase', 'retail', 'distribution', 'return_order', 'wastage', 'subscription', 'store_sales'];

export default function StockLedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [productId, setProductId] = useState<number | string>('');
  const [direction, setDirection] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [storeMode, setStoreMode] = useState<'all' | 'warehouse' | 'store'>('warehouse');
  const [storeId, setStoreId] = useState<number | string>('');
  const [hideCancelled, setHideCancelled] = useState(true);
  const [orderNumber, setOrderNumber] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [productId, direction, sourceType, dateFrom, dateTo, storeMode, storeId, hideCancelled, orderNumber]);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (productId) params.product_id = Number(productId);
      if (direction) params.direction = direction;
      if (sourceType) params.source_type = sourceType;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (storeMode === 'warehouse') params.store_id = 0;
      else if (storeMode === 'store') params.store_id = storeId ? Number(storeId) : -1;
      if (hideCancelled) params.hide_cancelled = true;
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
    { key: 'store_name', title: '店铺' },
    { key: 'source_type', title: '来源' },
    { key: 'order_number', title: '关联单号' },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">库存流水</h2>

      <div className="flex gap-1 mb-3">
        {([
          ['warehouse', '总仓'],
          ['store', '店铺'],
          ['all', '全部'],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => { setStoreMode(k); if (k !== 'store') setStoreId(''); }}
            className={`px-4 py-1 text-sm rounded ${storeMode === k ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="w-48">
          <ProductSelect value={productId} onChange={(v) => setProductId(v)} />
        </div>
        {storeMode === 'store' && (
          <div className="w-40">
            <StoreSelect value={storeId} onChange={(v) => setStoreId(v || '')} />
          </div>
        )}
        <select value={direction} onChange={(e) => setDirection(e.target.value)} className="border rounded px-3 py-2 text-sm">
          {DIR_OPTIONS.map(d => <option key={d} value={d}>{DIR_LABELS[d]}</option>)}
        </select>
        <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">全部来源</option>
          {SOURCE_OPTIONS.filter(r => r).map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <span className="text-gray-400 self-center">~</span>
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <input type="text" placeholder="单号" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} className="border rounded px-3 py-2 text-sm w-40" />
        <label className="flex items-center gap-1 text-sm self-center">
          <input type="checkbox" checked={hideCancelled} onChange={(e) => setHideCancelled(e.target.checked)} />
          隐藏已取消
        </label>
      </div>
      <OrderListTable columns={columns} data={rows} rowKey={(r) => r.id} isLoading={loading} />
    </div>
  );
}
