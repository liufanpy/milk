import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import { wastageApi, shelfApi, productApi } from '../services/api';

const REASONS = ['expired', 'damaged', 'self_consumed', 'giveaway', 'promotion'];
const REASON_LABELS: Record<string, string> = { expired: '过期', damaged: '破损', self_consumed: '自喝', giveaway: '赠送', promotion: '促销' };

interface WastageItem {
  product_id: number;
  quantity: number;
  shelf_id: number;
  reason: string;
}

export default function WastagePage() {
  const [items, setItems] = useState<WastageItem[]>([{ product_id: 0, quantity: 1, shelf_id: 0, reason: 'expired' }]);
  const [note, setNote] = useState('');
  const [shelves, setShelves] = useState<any[]>([]);
  const [records, setRecords] = useState<any[]>([]);
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  useEffect(() => {
    shelfApi.list().then(setShelves);
    wastageApi.list().then(setRecords);
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
  }, []);

  const updateItem = (idx: number, field: string, value: any) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) { alert('请填写完整'); return; }
    await wastageApi.create({ items, note });
    alert('损耗记录成功');
    setItems([{ product_id: 0, quantity: 1, shelf_id: 0, reason: 'expired' }]); setNote('');
    wastageApi.list().then(setRecords);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">损耗管理</h2><Button variant="secondary" size="sm" onClick={() => window.open('/api/wastage/export')}>导出 CSV</Button></div>
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1"><ProductSelect value={item.product_id} onChange={(v) => updateItem(idx, 'product_id', v)} onlyInStock /></div>
            <div className="w-20"><Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} /></div>
            <div className="flex-1">
              <select value={item.shelf_id} onChange={(e) => updateItem(idx, 'shelf_id', Number(e.target.value))} className="w-full border rounded px-2 py-1 text-sm">
                <option value="">选货架</option>
                {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div className="w-28">
              <select value={item.reason} onChange={(e) => updateItem(idx, 'reason', e.target.value)} className="w-full border rounded px-2 py-1 text-sm">
                {REASONS.map(r => <option key={r} value={r}>{REASON_LABELS[r]}</option>)}
              </select>
            </div>
            <Button variant="danger" size="sm" onClick={() => setItems(items.filter((_, i) => i !== idx))} disabled={items.length <= 1}>×</Button>
          </div>
        ))}
        <Button variant="secondary" size="sm" onClick={() => setItems([...items, { product_id: 0, quantity: 1, shelf_id: 0, reason: 'expired' }])}>+ 加行</Button>
        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleSubmit}>提交损耗</Button>
      </div>
      <h3 className="text-lg font-semibold mb-2">损耗记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {records.map((r: any) => (
          <div key={r.id} className="px-4 py-2 border-b text-sm text-gray-600">{productNames[r.product_id] || `产品#${r.product_id}`} 损耗 {r.quantity} — {REASON_LABELS[r.reason] || r.reason} — {new Date(r.created_at).toLocaleDateString()}</div>
        ))}
      </div>
    </div>
  );
}
