import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { subscriptionApi, shelfApi } from '../services/api';

export default function SubscriptionsPage() {
  const [customerId, setCustomerId] = useState<number | string>('');
  const [totalAmount, setTotalAmount] = useState(0);
  const [totalBottles, setTotalBottles] = useState(0);
  const [paidBottles, setPaidBottles] = useState(0);
  const [freeBottles, setFreeBottles] = useState(0);
  const [orders, setOrders] = useState<any[]>([]);
  const [shelves, setShelves] = useState<any[]>([]);

  // Deduct state
  const [deductOpen, setDeductOpen] = useState(false);
  const [deductOrderId, setDeductOrderId] = useState<number>(0);
  const [deductItems, setDeductItems] = useState([{ product_id: 0, quantity: 1 }]);
  const [deductShelfId, setDeductShelfId] = useState<number | string>('');

  useEffect(() => { subscriptionApi.list().then(setOrders); shelfApi.list().then(setShelves); }, []);

  const handleCreate = async () => {
    if (!customerId || totalBottles <= 0) { alert('请填写完整'); return; }
    await subscriptionApi.create({ customer_id: Number(customerId), total_amount: totalAmount, total_bottles: totalBottles, paid_bottles: paidBottles, free_bottles: freeBottles });
    alert('订奶单创建成功');
    setCustomerId(''); setTotalAmount(0); setTotalBottles(0); setPaidBottles(0); setFreeBottles(0);
    subscriptionApi.list().then(setOrders);
  };

  const openDeduct = (order: any) => {
    setDeductOrderId(order.id);
    setDeductItems([{ product_id: 0, quantity: 1 }]);
    setDeductShelfId('');
    setDeductOpen(true);
  };

  const handleDeduct = async () => {
    if (!deductShelfId || deductItems.some(i => !i.product_id)) { alert('请填写完整'); return; }
    await subscriptionApi.deduct(deductOrderId, { items: deductItems, shelf_id: Number(deductShelfId) });
    alert('扣减成功');
    setDeductOpen(false);
    subscriptionApi.list().then(setOrders);
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">订奶管理</h2>
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <h3 className="font-semibold">新建订奶单</h3>
        <CustomerSelect value={customerId} onChange={setCustomerId} />
        <div className="grid grid-cols-2 gap-3">
          <Input label="收款金额" type="number" value={String(totalAmount)} onChange={(e) => setTotalAmount(Number(e.target.value))} />
          <Input label="总瓶数" type="number" value={String(totalBottles)} onChange={(e) => setTotalBottles(Number(e.target.value))} />
          <Input label="付费瓶数" type="number" value={String(paidBottles)} onChange={(e) => setPaidBottles(Number(e.target.value))} />
          <Input label="赠送瓶数" type="number" value={String(freeBottles)} onChange={(e) => setFreeBottles(Number(e.target.value))} />
        </div>
        <Button onClick={handleCreate}>创建订奶单</Button>
      </div>

      <h3 className="text-lg font-semibold mb-2">订奶单列表</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
            <th className="px-4 py-2">#</th><th className="px-4 py-2">客户</th><th className="px-4 py-2">金额</th><th className="px-4 py-2">总瓶数</th><th className="px-4 py-2">剩余</th><th className="px-4 py-2">状态</th><th className="px-4 py-2">操作</th>
          </tr></thead>
          <tbody>
            {orders.map((o: any) => (
              <tr key={o.id} className="border-b">
                <td className="px-4 py-2">#{o.id}</td>
                <td className="px-4 py-2">{o.customer_id}</td>
                <td className="px-4 py-2">¥{o.total_amount}</td>
                <td className="px-4 py-2">{o.total_bottles}</td>
                <td className="px-4 py-2 font-medium">{o.remaining_bottles}</td>
                <td className="px-4 py-2">{o.status === 'active' ? '进行中' : o.status}</td>
                <td className="px-4 py-2">
                  <Button size="sm" variant="secondary" onClick={() => openDeduct(o)} disabled={o.status !== 'active'}>扣减</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={deductOpen} onClose={() => setDeductOpen(false)} title="配送扣减">
        <div className="space-y-3">
          {deductItems.map((item, idx) => (
            <div key={idx} className="flex gap-2">
              <ProductSelect value={item.product_id} onChange={(v) => setDeductItems(prev => prev.map((it, i) => i === idx ? { ...it, product_id: v } : it))} onlyInStock />
              <Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => setDeductItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: Number(e.target.value) } : it))} className="w-20" />
              <Button variant="danger" size="sm" onClick={() => setDeductItems(deductItems.filter((_, i) => i !== idx))} disabled={deductItems.length <= 1}>×</Button>
            </div>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setDeductItems([...deductItems, { product_id: 0, quantity: 1 }])}>+</Button>
          <div>
            <label className="text-sm font-medium">货架</label>
            <select value={deductShelfId} onChange={(e) => setDeductShelfId(Number(e.target.value))} className="w-full border rounded px-3 py-2 text-sm mt-1">
              <option value="">选货架</option>
              {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <Button onClick={handleDeduct}>确认扣减</Button>
        </div>
      </Modal>
    </div>
  );
}
