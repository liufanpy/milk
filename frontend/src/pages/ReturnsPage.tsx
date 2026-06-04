import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { returnApi, shelfApi } from '../services/api';

interface ReturnItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
  is_wasted: boolean;
}

export default function ReturnsPage() {
  const [customerId, setCustomerId] = useState<number | string>('');
  const [deliveryId, setDeliveryId] = useState('');
  const [items, setItems] = useState<ReturnItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0, is_wasted: false }]);
  const [note, setNote] = useState('');
  const [shelves, setShelves] = useState<any[]>([]);
  const [returns, setReturns] = useState<any[]>([]);

  useEffect(() => { shelfApi.list().then(setShelves); returnApi.list().then(setReturns); }, []);

  const updateItem = (idx: number, field: string, value: any) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (!customerId || items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    await returnApi.create({
      customer_id: Number(customerId),
      delivery_id: deliveryId ? Number(deliveryId) : null,
      items,
      note,
    });
    alert('退货成功');
    setCustomerId(''); setDeliveryId(''); setItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0, is_wasted: false }]); setNote('');
    returnApi.list().then(setReturns);
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">退货管理</h2>
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-sm font-medium">客户</label><CustomerSelect value={customerId} onChange={setCustomerId} /></div>
          <div><label className="text-sm font-medium">关联送货单ID(可选)</label><Input value={deliveryId} onChange={(e) => setDeliveryId(e.target.value)} /></div>
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1"><ProductSelect value={item.product_id} onChange={(v) => updateItem(idx, 'product_id', v)} /></div>
            <div className="w-20"><Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} /></div>
            <div className="w-24"><Input type="number" placeholder="单价" value={String(item.unit_price)} onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))} /></div>
            <div className="flex-1">
              <select value={item.shelf_id} onChange={(e) => updateItem(idx, 'shelf_id', Number(e.target.value))} className="w-full border rounded px-2 py-1 text-sm">
                <option value="">选货架</option>
                {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={item.is_wasted} onChange={(e) => updateItem(idx, 'is_wasted', e.target.checked)} />报废</label>
            <Button variant="danger" size="sm" onClick={() => setItems(items.filter((_, i) => i !== idx))} disabled={items.length <= 1}>×</Button>
          </div>
        ))}
        <Button variant="secondary" size="sm" onClick={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0, is_wasted: false }])}>+ 加行</Button>
        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleSubmit}>提交退货</Button>
      </div>
      <h3 className="text-lg font-semibold mb-2">退货记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {returns.map((r: any) => (
          <div key={r.id} className="px-4 py-2 border-b text-sm text-gray-600">#{r.id} — {r.direction} {r.reason} — qty: {r.quantity} — {new Date(r.created_at).toLocaleDateString()}</div>
        ))}
      </div>
    </div>
  );
}
