import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { saleApi, shelfApi } from '../services/api';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
}

export default function SalesPage() {
  const [customerId, setCustomerId] = useState<number | string>('');
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
  const [paid, setPaid] = useState(true);
  const [shelves, setShelves] = useState<any[]>([]);
  const [note, setNote] = useState('');
  const [sales, setSales] = useState<any[]>([]);

  useEffect(() => {
    shelfApi.list().then(setShelves);
    saleApi.list().then(setSales);
  }, []);

  const updateItem = (idx: number, field: keyof ItemRow, value: number) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };
  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息');
      return;
    }
    await saleApi.create({
      customer_id: customerId ? Number(customerId) : null,
      items,
      paid,
      note,
    });
    alert('销售成功');
    setCustomerId('');
    setItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
    setPaid(true);
    setNote('');
    saleApi.list().then(setSales);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">直接销售（零售/自取）</h2><Button variant="secondary" size="sm" onClick={() => window.open('/api/sales/export')}>导出 CSV</Button></div>
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div>
          <label className="text-sm font-medium text-gray-700">客户（留空为散客）</label>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
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
              <label className="text-xs text-gray-500">售价</label>
              <Input type="number" value={String(item.unit_price)} onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))} />
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
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
          已收款
        </label>
        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleSubmit}>提交销售</Button>
      </div>

      <h3 className="text-lg font-semibold mb-2">销售记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {sales.map((s: any) => (
          <div key={s.id} className="px-4 py-2 border-b text-sm text-gray-600">
            #{s.id} — {s.category} — ¥{s.amount} — {new Date(s.created_at).toLocaleDateString()}
          </div>
        ))}
      </div>
    </div>
  );
}
