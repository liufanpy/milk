import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import CsvImportModal from '../components/business/CsvImportModal';
import { storeApi, productApi, storeSalesApi } from '../services/api';
import type { StoreSalesOrder, StoreSalesDetail } from '../types';

export default function StoreSalesPage() {
  const [stores, setStores] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [storeId, setStoreId] = useState<number | string>('');
  const [checkDate, setCheckDate] = useState(new Date().toISOString().slice(0, 10));
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [checks, setChecks] = useState<StoreSalesOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<StoreSalesDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    storeApi.list().then((data: any) => {
      setStores(data);
      if (data.length === 1) setStoreId(data[0].id);
    });
    productApi.list().then(setProducts);
    loadChecks();
  }, []);

  const loadChecks = () => storeSalesApi.list().then(setChecks);

  const handleConfirm = async () => {
    if (!storeId) { alert('请选店铺'); return; }
    const items = Object.entries(quantities)
      .filter(([_, qty]) => qty > 0)
      .map(([pid, qty]) => ({ product_id: Number(pid), actual_quantity: qty }));
    if (items.length === 0) { alert('请至少填写一个产品的实盘数'); return; }

    setLoading(true);
    try {
      await storeSalesApi.create({ store_id: Number(storeId), check_date: checkDate, items });
      setQuantities({});
      loadChecks();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    } finally { setLoading(false); }
  };

  const openDetail = async (id: number) => {
    const d = await storeSalesApi.get(id);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async (id: number) => {
    if (!confirm('确定撤销？')) return;
    await storeSalesApi.cancel(id);
    loadChecks();
  };

  const columns = [
    { key: 'order_number', title: '单号', render: (c: any) => <span className="font-medium">{c.order_number}</span> },
    { key: 'store_name', title: '店铺' },
    { key: 'check_date', title: '日期' },
    { key: 'item_count', title: '品项数' },
    { key: 'status', title: '状态' },
    {
      key: 'actions', title: '操作',
      render: (c: any) => (
        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
          {c.status === 'confirmed' && (
            <Button variant="danger" size="sm" onClick={() => handleCancel(c.id)}>撤销</Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">巡店管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/store-sales/export')}>导出 CSV</Button>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4 mb-6">
        <h3 className="font-semibold mb-3">新建巡店</h3>
        <div className="flex gap-4 mb-4">
          <select
            value={storeId}
            onChange={(e) => setStoreId(Number(e.target.value))}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">选店铺</option>
            {stores.map((s: any) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <Input type="date" value={checkDate} onChange={(e) => setCheckDate(e.target.value)} />
        </div>
        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {products.map((p) => (
            <div key={p.id} className="border rounded p-2">
              <div className="text-xs text-gray-500 truncate">{p.name}</div>
              <input
                type="number"
                min="0"
                value={quantities[p.id] || ''}
                onChange={(e) => setQuantities(prev => ({
                  ...prev, [p.id]: e.target.value ? parseInt(e.target.value) : 0
                }))}
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                placeholder="实盘"
              />
            </div>
          ))}
        </div>
        <div className="mt-4">
          <Button onClick={handleConfirm} disabled={loading}>确认巡店</Button>
        </div>
      </div>

      <h3 className="text-lg font-semibold mb-2">巡店记录</h3>
      <OrderListTable
        columns={columns}
        data={checks}
        rowKey={(c) => c.id}
        onRowClick={(c) => openDetail(c.id)}
      />

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`巡店详情 — ${detail?.order_number || ''}`}
        headerInfo={
          <>
            <div>店铺: {detail?.store_name}</div>
            <div>日期: {detail?.check_date}</div>
          </>
        }
        items={detail?.items || []}
      />

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入巡店"
        onImport={(file) => storeSalesApi.importFile(file)}
        onConfirm={(rows) => storeSalesApi.confirmImport(rows)}
        onDone={() => loadChecks()}
      />
    </div>
  );
}
