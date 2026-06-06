import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { subscriptionApi, customerApi, productApi } from '../services/api';

interface DeductItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

export default function SubscriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<any>(null);
  const [customerName, setCustomerName] = useState('');
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  // 扣减弹窗
  const [deductOpen, setDeductOpen] = useState(false);
  const [deductItems, setDeductItems] = useState<DeductItemRow[]>([
    { product_id: 0, quantity: 1, unit_price: 0, is_promo: false },
  ]);

  const loadOrder = async () => {
    const data = await subscriptionApi.get(Number(id));
    setOrder(data);
    customerApi.get(data.customer_id).then((c: any) => setCustomerName(c.name));
  };

  useEffect(() => {
    loadOrder();
    productApi.list().then((data: any) =>
      setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name])))
    );
  }, [id]);

  const updateDeductItem = (idx: number, field: keyof DeductItemRow, value: number | boolean) => {
    setDeductItems(prev =>
      prev.map((item, i) => {
        if (i !== idx) return item;
        const updated = { ...item, [field]: value };
        // 选赠送时 unit_price 强制为 0
        if (field === 'is_promo' && value === true) {
          updated.unit_price = 0;
        }
        return updated;
      })
    );
  };

  const paidTotal = deductItems
    .filter(i => !i.is_promo)
    .reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  const handleDeduct = async () => {
    if (deductItems.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await subscriptionApi.deduct(Number(id), { items: deductItems });
      alert('扣减成功');
      setDeductOpen(false);
      setDeductItems([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
      loadOrder();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '扣减失败');
    }
  };

  if (!order) return <div className="text-center py-8 text-gray-400">加载中...</div>;

  const statusLabel = (s: string) =>
    s === 'active' ? '进行中' : s === 'completed' ? '已完成' : s === 'cancelled' ? '已取消' : s;

  return (
    <div>
      <button onClick={() => navigate('/subscriptions')} className="text-blue-600 text-sm mb-4 block">
        &larr; 返回订奶列表
      </button>

      {/* 概要 */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <h2 className="text-lg font-bold mb-3">订奶单 #{order.id}</h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div><span className="text-gray-500">客户:</span> {customerName}</div>
          <div><span className="text-gray-500">实付金额:</span> ¥{order.paid_amount}</div>
          <div>
            <span className="text-gray-500">剩余金额:</span>{' '}
            <strong className={order.remaining_amount > 0 ? 'text-green-600' : 'text-gray-400'}>
              ¥{order.remaining_amount}
            </strong>
          </div>
          <div><span className="text-gray-500">状态:</span> {statusLabel(order.status)}</div>
          <div><span className="text-gray-500">备注:</span> {order.note || '-'}</div>
          <div><span className="text-gray-500">创建时间:</span> {new Date(order.created_at).toLocaleDateString()}</div>
        </div>
        {order.status === 'active' && (
          <div className="mt-4">
            <Button onClick={() => setDeductOpen(true)}>配送扣减</Button>
          </div>
        )}
      </div>

      {/* 扣减记录 */}
      <h3 className="text-lg font-semibold mb-2">扣减记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {order.deductions?.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-gray-600">
                <th className="px-4 py-2">产品</th>
                <th className="px-4 py-2">数量</th>
                <th className="px-4 py-2">单价</th>
                <th className="px-4 py-2">小计</th>
                <th className="px-4 py-2">时间</th>
              </tr>
            </thead>
            <tbody>
              {order.deductions.map((d: any) => (
                <tr key={d.id} className="border-b">
                  <td className="px-4 py-2">{productNames[d.product_id] || `产品#${d.product_id}`}</td>
                  <td className="px-4 py-2">{d.quantity}</td>
                  <td className="px-4 py-2">¥{d.unit_price}</td>
                  <td className="px-4 py-2">¥{(d.quantity * d.unit_price).toFixed(2)}</td>
                  <td className="px-4 py-2">{new Date(d.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-8 text-gray-400">暂无扣减记录</div>
        )}
      </div>

      {/* 扣减弹窗 */}
      <Modal open={deductOpen} onClose={() => setDeductOpen(false)} title="配送扣减">
        <div className="space-y-3">
          {deductItems.map((item, idx) => (
            <div key={idx} className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-gray-500">产品</label>
                <ProductSelect value={item.product_id} onChange={(v) => updateDeductItem(idx, 'product_id', v)} onlyInStock />
              </div>
              <div className="w-20">
                <label className="text-xs text-gray-500">数量</label>
                <Input type="number" value={String(item.quantity)} onChange={(e) => updateDeductItem(idx, 'quantity', Number(e.target.value))} />
              </div>
              <div className="w-24">
                <label className="text-xs text-gray-500">单价</label>
                <Input type="number" value={String(item.unit_price)} onChange={(e) => updateDeductItem(idx, 'unit_price', Number(e.target.value))} disabled={item.is_promo} />
              </div>
              <label className="flex items-center gap-1 text-xs pb-2">
                <input type="checkbox" checked={item.is_promo} onChange={(e) => updateDeductItem(idx, 'is_promo', e.target.checked)} />
                赠送
              </label>
              <Button variant="danger" size="sm" onClick={() => setDeductItems(deductItems.filter((_, i) => i !== idx))} disabled={deductItems.length <= 1}>×</Button>
            </div>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setDeductItems([...deductItems, { product_id: 0, quantity: 1, unit_price: 0, is_promo: false }])}>+ 加行</Button>

          <div className="border-t pt-3 text-sm space-y-1">
            <div>本次扣减合计: <strong>¥{paidTotal.toFixed(2)}</strong></div>
            <div>剩余余额: ¥{order.remaining_amount} → ¥{(order.remaining_amount - paidTotal).toFixed(2)}</div>
            {paidTotal > order.remaining_amount && (
              <div className="text-red-600 font-medium">超出余额，无法提交</div>
            )}
          </div>
          <Button onClick={handleDeduct} disabled={paidTotal > order.remaining_amount}>确认扣减</Button>
        </div>
      </Modal>
    </div>
  );
}
