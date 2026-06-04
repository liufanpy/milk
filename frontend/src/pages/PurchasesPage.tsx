import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import CsvImportModal from '../components/business/CsvImportModal';
import { purchaseApi, supplierApi, shelfApi, productApi } from '../services/api';
import type { PurchaseOrder, PurchaseOrderDetail } from '../types';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
}

const STATUS_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  draft: 'warning',
  confirmed: 'success',
  cancelled: 'default',
};
const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  confirmed: '已确认',
  cancelled: '已撤销',
};

export default function PurchasesPage() {
  const [importOpen, setImportOpen] = useState(false);
  const [supplierId, setSupplierId] = useState<number | string>('');
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [shelves, setShelves] = useState<any[]>([]);
  const [note, setNote] = useState('');
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [productNames, setProductNames] = useState<Record<number, string>>({});
  const [shelfNames, setShelfNames] = useState<Record<number, string>>({});

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<PurchaseOrderDetail | null>(null);

  useEffect(() => {
    supplierApi.list().then(setSuppliers);
    shelfApi.list().then((data: any) => { setShelves(data); setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))); });
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
    purchaseApi.list().then(setOrders);
  }, []);

  const refreshOrders = () => purchaseApi.list().then(setOrders);

  const updateItem = (idx: number, field: keyof ItemRow, value: number) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };

  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const resetForm = () => {
    setSupplierId('');
    setPurchaseDate(new Date().toISOString().slice(0, 10));
    setItems([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
    setNote('');
  };

  const handleSubmit = async (status: 'draft' | 'confirmed') => {
    if (!supplierId || !purchaseDate || items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息');
      return;
    }
    await purchaseApi.create({ supplier_id: Number(supplierId), purchase_date: purchaseDate, items, note, status });
    alert(status === 'draft' ? '草稿已保存' : '入库成功');
    resetForm();
    refreshOrders();
  };

  const handleConfirm = async (orderId: number) => {
    if (!confirm('确定确认入库？')) return;
    await purchaseApi.confirm(orderId);
    refreshOrders();
  };

  const handleCancel = async (orderId: number, status: string) => {
    const msg = status === 'draft' ? '确定作废此草稿？' : '确定撤销此进货单？（将反向冲抵库存）';
    if (!confirm(msg)) return;
    await purchaseApi.cancel(orderId);
    refreshOrders();
  };

  const openDetail = async (orderId: number) => {
    const d = await purchaseApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_cost, 0);
  const statusBadge = (status: string) => (
    <Badge variant={STATUS_VARIANT[status] || 'default'}>{STATUS_LABEL[status] || status}</Badge>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">进货管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/purchases/export')}>导出 CSV</Button>
        </div>
      </div>

      {/* 新建进货单 */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
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

        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500">产品</label>
              <ProductSelect value={item.product_id} onChange={(v) => updateItem(idx, 'product_id', v)} />
            </div>
            <div className="w-20">
              <label className="text-xs text-gray-500">数量</label>
              <Input type="number" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} />
            </div>
            <div className="w-24">
              <label className="text-xs text-gray-500">进价</label>
              <Input type="number" value={String(item.unit_cost)} onChange={(e) => updateItem(idx, 'unit_cost', Number(e.target.value))} />
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-500">货架</label>
              <select value={item.shelf_id} onChange={(e) => updateItem(idx, 'shelf_id', Number(e.target.value))} className="w-full border rounded px-2 py-1 text-sm">
                <option value="">选货架</option>
                {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <Button variant="danger" size="sm" onClick={() => removeRow(idx)} disabled={items.length <= 1}>×</Button>
          </div>
        ))}

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={addRow}>+ 加行</Button>
          <span className="text-sm text-gray-500 ml-auto">合计: ¥{total.toFixed(2)}</span>
        </div>

        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />

        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => handleSubmit('draft')}>保存草稿</Button>
          <Button onClick={() => handleSubmit('confirmed')}>确认入库</Button>
        </div>
      </div>

      {/* 进货单列表 */}
      <h3 className="text-lg font-semibold mb-2">进货单列表</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="px-4 py-2 text-left">单号</th>
              <th className="px-4 py-2 text-left">供应商</th>
              <th className="px-4 py-2 text-left">日期</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(o.id)}>
                <td className="px-4 py-2 font-medium">{o.order_number}</td>
                <td className="px-4 py-2 text-gray-600">{o.supplier_name}</td>
                <td className="px-4 py-2 text-gray-600">{o.purchase_date}</td>
                <td className="px-4 py-2 text-right">¥{o.total_amount.toFixed(2)}</td>
                <td className="px-4 py-2 text-center">{statusBadge(o.status)}</td>
                <td className="px-4 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                  {o.status === 'draft' && (
                    <Button variant="primary" size="sm" onClick={() => handleConfirm(o.id)}>确认</Button>
                  )}
                  {(o.status === 'draft' || o.status === 'confirmed') && (
                    <span className="ml-2">
                      <Button variant="danger" size="sm" onClick={() => handleCancel(o.id, o.status)}>
                        {o.status === 'draft' ? '作废' : '撤销'}
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">暂无进货单</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 详情弹窗 */}
      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`进货单详情 — ${detail?.order_number || ''}`}>
        {detail && (
          <div className="space-y-3">
            <div className="flex gap-4 text-sm">
              <span>供应商: {detail.supplier_name}</span>
              <span>日期: {detail.purchase_date}</span>
              <span>状态: {statusBadge(detail.status)}</span>
            </div>
            {detail.note && <div className="text-sm text-gray-500">备注: {detail.note}</div>}
            <table className="w-full text-sm border-t mt-2">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left">产品</th>
                  <th className="px-2 py-1 text-right">数量</th>
                  <th className="px-2 py-1 text-right">进价</th>
                  <th className="px-2 py-1 text-right">小计</th>
                  <th className="px-2 py-1 text-left">货架</th>
                </tr>
              </thead>
              <tbody>
                {detail.items.map((it, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">{it.product_name}</td>
                    <td className="px-2 py-1 text-right">{it.quantity}</td>
                    <td className="px-2 py-1 text-right">¥{it.unit_cost.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_cost).toFixed(2)}</td>
                    <td className="px-2 py-1">{it.shelf_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-right font-bold">合计: ¥{detail.total_amount.toFixed(2)}</div>
          </div>
        )}
      </Modal>

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
