import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import CsvImportModal from '../components/business/CsvImportModal';
import { purchaseApi, supplierApi, shelfApi } from '../services/api';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
}

export default function PurchasesPage() {
  const [importOpen, setImportOpen] = useState(false);
  const [supplierId, setSupplierId] = useState<number | string>('');
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [shelves, setShelves] = useState<any[]>([]);
  const [note, setNote] = useState('');
  const [purchases, setPurchases] = useState<any[]>([]);

  useEffect(() => {
    supplierApi.list().then(setSuppliers);
    shelfApi.list().then(setShelves);
    purchaseApi.list().then(setPurchases);
  }, []);

  const updateItem = (idx: number, field: keyof ItemRow, value: number) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };

  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (!supplierId || items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息');
      return;
    }
    await purchaseApi.create({ supplier_id: Number(supplierId), items, note });
    alert('进货成功');
    setSupplierId('');
    setItems([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
    setNote('');
    purchaseApi.list().then(setPurchases);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_cost, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">进货管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/purchases/export')}>导出 CSV</Button>
        </div></div>
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div>
          <label className="text-sm font-medium text-gray-700">供应商</label>
          <select value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))} className="w-full border rounded px-3 py-2 text-sm mt-1">
            <option value="">选供应商</option>
            {suppliers.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
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
        <Button onClick={handleSubmit}>提交进货</Button>
      </div>

      <h3 className="text-lg font-semibold mb-2">进货记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {purchases.map((p: any) => (
          <div key={p.id} className="px-4 py-2 border-b text-sm text-gray-600">
            #{p.id} — {p.direction} {p.reason} — qty: {p.quantity} — {new Date(p.created_at).toLocaleDateString()}
          </div>
        ))}
      </div>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入进货"
        onImport={(file) => purchaseApi.importFile(file)}
        onConfirm={(rows) => purchaseApi.confirmImport(rows)}
        onDone={() => { purchaseApi.list().then((data: any) => setPurchases(data)); }}
      />
    </div>
  );
}
