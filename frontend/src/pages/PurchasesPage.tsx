import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import CsvImportModal from '../components/business/CsvImportModal';
import { purchaseApi, supplierApi, productApi } from '../services/api';
import type { PurchaseOrder, PurchaseOrderDetail } from '../types';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
}

const purchaseStatusConfig = {
  draft: { label: '草稿', variant: 'warning' as const },
  confirmed: { label: '已确认', variant: 'success' as const },
  cancelled: { label: '已撤销', variant: 'default' as const },
};

export default function PurchasesPage() {
  const [importOpen, setImportOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [supplierId, setSupplierId] = useState<number | string>('');
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0 }]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [note, setNote] = useState('');
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [products, setProducts] = useState<any[]>([]);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<PurchaseOrderDetail | null>(null);

  useEffect(() => {
    supplierApi.list().then((data: any) => {
      setSuppliers(data);
      if (data.length === 1) setSupplierId(data[0].id);
    });
    productApi.list().then((data: any) => setProducts(data));
    purchaseApi.list().then(setOrders);
  }, []);

  const refreshOrders = () => purchaseApi.list().then(setOrders);

  const updateItem = (idx: number, field: keyof ItemRow, value: number | boolean) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };

  const onProductChange = (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId as number);
    if (productId) {
      const product = products.find(p => p.id === productId);
      if (product?.default_purchase_price) {
        updateItem(idx, 'unit_price', product.default_purchase_price);
      }
    }
  };

  const resetForm = () => {
    setSupplierId('');
    setPurchaseDate(new Date().toISOString().slice(0, 10));
    setItems([{ product_id: 0, quantity: 1, unit_price: 0 }]);
    setNote('');
  };

  const handleSubmit = async (status: 'draft' | 'confirmed') => {
    if (!supplierId || !purchaseDate || items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await purchaseApi.create({ supplier_id: Number(supplierId), purchase_date: purchaseDate, items, note, status });
      alert(status === 'draft' ? '草稿已保存' : '入库成功');
      resetForm();
      setFormOpen(false);
      refreshOrders();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const handleConfirm = async (orderId: number) => {
    if (!confirm('确定确认入库？')) return;
    await purchaseApi.confirm(orderId);
    refreshOrders();
  };

  const handleCancel = async (orderId: number, status: string) => {
    const msg = status === 'draft' ? '确定作废此草稿？' : '确定撤销此进货单？（将反向冲抵库存）';
    if (!confirm(msg)) return;
    try {
      await purchaseApi.cancel(orderId);
      refreshOrders();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '撤销失败');
    }
  };

  const openDetail = async (orderId: number) => {
    const d = await purchaseApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const columns = [
    { key: 'order_number', title: '单号', render: (o: any) => <span className="font-medium">{o.order_number}</span> },
    { key: 'supplier_name', title: '供应商' },
    { key: 'purchase_date', title: '日期' },
    { key: 'total_amount', title: '金额', render: (o: any) => `¥${o.total_amount.toFixed(2)}` },
    { key: 'status', title: '状态', render: (o: any) => <StatusBadge status={o.status} config={purchaseStatusConfig} /> },
    {
      key: 'actions', title: '操作',
      render: (o: any) => (
        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
          {o.status === 'draft' && (
            <Button variant="primary" size="sm" onClick={() => handleConfirm(o.id)}>确认</Button>
          )}
          {(o.status === 'draft' || o.status === 'confirmed') && (
            <Button variant="danger" size="sm" onClick={() => handleCancel(o.id, o.status)}>
              {o.status === 'draft' ? '作废' : '撤销'}
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">进货管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/purchases/export')}>导出 CSV</Button>
          <Button onClick={() => setFormOpen(true)}>+ 新建进货</Button>
        </div>
      </div>

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建进货单"
        onSubmit={() => {}}
        hideFooter
      >
        <div className="space-y-3">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-700">供应商</label>
              <select value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))} className="w-full border rounded px-3 py-2 text-sm mt-1">
                <option value="">选供应商</option>
                {suppliers.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div className="w-40">
              <label className="text-sm font-medium text-gray-700">进货日期</label>
              <Input type="date" value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} />
            </div>
          </div>

          <ItemRowEditor
            items={items}
            onUpdate={updateItem}
            onProductChange={onProductChange}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0 }])}
          />

          <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />

          <div className="flex gap-2 pt-2 border-t">
            <Button variant="secondary" onClick={() => handleSubmit('draft')}>保存草稿</Button>
            <Button onClick={() => handleSubmit('confirmed')}>确认入库</Button>
            <Button variant="secondary" onClick={() => setFormOpen(false)}>取消</Button>
          </div>
        </div>
      </OrderFormModal>

      <h3 className="text-lg font-semibold mb-2">进货单列表</h3>
      <OrderListTable
        columns={columns}
        data={orders}
        rowKey={(o) => o.id}
        onRowClick={(o) => openDetail(o.id)}
      />

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`进货单详情 — ${detail?.order_number || ''}`}
        headerInfo={
          <>
            <div>供应商: {detail?.supplier_name}</div>
            <div>日期: {detail?.purchase_date}</div>
            {detail?.note && <div>备注: {detail.note}</div>}
          </>
        }
        items={detail?.items || []}
        status={detail?.status}
        statusConfig={purchaseStatusConfig}
      />

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入进货"
        onImport={(file) => purchaseApi.importFile(file)}
        onConfirm={(rows) => purchaseApi.confirmImport(rows)}
        onDone={refreshOrders}
      />
    </div>
  );
}
