import { useState, useEffect } from 'react';
import { OrderListTable } from '../components/business/OrderListTable';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ledgerApi } from '../services/api';

const CAT_OPTIONS = ['', 'retail', 'distribution', 'subscription', 'payment', 'refund', 'purchase', 'wastage', 'promo', 'store_sales'];

export default function TransactionLedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [storeId, setStoreId] = useState<number | string>('');
  const [customerId, setCustomerId] = useState<number | string>('');
  const [category, setCategory] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [orderNumber, setOrderNumber] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [customerId, storeId, category, dateFrom, dateTo, orderNumber]);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (storeId) params.store_id = Number(storeId);
      if (customerId) params.customer_id = Number(customerId);
      if (category) params.category = category;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (orderNumber) params.order_number = orderNumber;
      const data = await ledgerApi.transactions(params);
      setRows(data);
    } finally { setLoading(false); }
  };

  const columns = [
    { key: 'created_at', title: '时间', render: (r: any) => r.created_at?.slice(0, 19).replace('T', ' ') },
    { key: 'customer_name', title: '客户/供应商', render: (r: any) => r.customer_name || '—' },
    { key: 'category', title: '类型' },
    { key: 'amount', title: '金额', render: (r: any) => (
      <span className={`font-medium ${r.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
        {r.amount > 0 ? '+' : ''}{r.amount.toFixed(2)}
      </span>
    )},
    { key: 'balance', title: '应收余额', render: (r: any) =>
      r.balance !== null ? <span className="font-bold">¥{r.balance.toFixed(2)}</span> : '—'
    },
    { key: 'order_number', title: '关联单号' },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">资金流水</h2>
      <div className="flex gap-3 mb-4">
        <input type="number" placeholder="店铺ID" value={storeId} onChange={(e) => setStoreId(e.target.value ? Number(e.target.value) : '')} className="border rounded px-3 py-2 text-sm w-24" />
        <div className="w-48">
          <CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">全部类别</option>
          {CAT_OPTIONS.filter(c => c).map(c => <option key={c} value={c}>{c}</option>)}
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
