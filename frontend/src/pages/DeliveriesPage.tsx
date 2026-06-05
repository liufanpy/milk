import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { useDeliveries, useCreateDelivery, useSettleDelivery, useExchangeDelivery } from '../hooks/useDeliveries';
import { deliveryApi, shelfApi, customerApi, productApi } from '../services/api';

interface DeliveryItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
}

export default function DeliveriesPage() {
  // Create state
  const [customerId, setCustomerId] = useState<number | string>('');
  const [deliveryDate, setDeliveryDate] = useState(new Date().toISOString().split('T')[0]);
  const [items, setItems] = useState<DeliveryItem[]>([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
  const [paid, setPaid] = useState(false);
  const [note, setNote] = useState('');
  const [shelves, setShelves] = useState<any[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  // List state
  const [filterCustomer, setFilterCustomer] = useState<string | number>('');
  const [filterStatus, setFilterStatus] = useState('');
  const { data: deliveries = [], refetch } = useDeliveries();
  const createMutation = useCreateDelivery();
  const settleMutation = useSettleDelivery();
  const exchangeMutation = useExchangeDelivery();

  // Detail state
  const [selectedDelivery, setSelectedDelivery] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [settleAmount, setSettleAmount] = useState(0);
  const [settleOpen, setSettleOpen] = useState(false);
  const [exchangeOpen, setExchangeOpen] = useState(false);
  const [returnItems, setReturnItems] = useState<DeliveryItem[]>([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
  const [newItems, setNewItems] = useState<DeliveryItem[]>([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);

  useEffect(() => {
    shelfApi.list().then(setShelves);
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
  }, []);

  // Create helpers
  const updateItem = (idx: number, field: keyof DeliveryItem, value: number) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);

  const onProductChange = async (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId);
    if (productId) {
      try {
        const { price } = await customerApi.resolvePrice(customerId ? Number(customerId) : 0, productId);
        updateItem(idx, 'unit_price', price);
      } catch {}
    }
  };

  const handleCreate = async () => {
    if (!customerId || items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await createMutation.mutateAsync({
        customer_id: Number(customerId),
        delivery_date: deliveryDate,
        items,
        paid,
        note,
      });
      alert('送货单创建成功');
      setCustomerId(''); setItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]); setNote('');
      refetch();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  // Detail
  const openDetail = async (d: any) => {
    const detail = await deliveryApi.get(d.id);
    setSelectedDelivery(detail);
    setDetailOpen(true);
  };

  const handleSettle = async () => {
    if (!selectedDelivery || settleAmount <= 0) return;
    await settleMutation.mutateAsync({ id: selectedDelivery.id, amount: settleAmount });
    alert('结算成功');
    setSettleOpen(false);
    const detail = await deliveryApi.get(selectedDelivery.id);
    setSelectedDelivery(detail);
    refetch();
  };

  const exchangeCustomerId = selectedDelivery?.customer_id;

  const onReturnProductChange = async (idx: number, productId: number) => {
    setReturnItems(prev => prev.map((it, i) => i === idx ? { ...it, product_id: productId } : it));
    if (exchangeCustomerId && productId) {
      try {
        const { price } = await customerApi.resolvePrice(exchangeCustomerId, productId);
        setReturnItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: price } : it));
      } catch {}
    }
  };

  const onNewProductChange = async (idx: number, productId: number) => {
    setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, product_id: productId } : it));
    if (exchangeCustomerId && productId) {
      try {
        const { price } = await customerApi.resolvePrice(exchangeCustomerId, productId);
        setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: price } : it));
      } catch {}
    }
  };

  const handleExchange = async () => {
    if (!selectedDelivery) return;
    try {
      await exchangeMutation.mutateAsync({
        id: selectedDelivery.id,
        data: { return_items: returnItems, new_items: newItems },
      });
      alert('换货成功');
      setExchangeOpen(false);
      setReturnItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
      setNewItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
      const detail = await deliveryApi.get(selectedDelivery.id);
      setSelectedDelivery(detail);
      refetch();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '换货失败');
    }
  };

  // Filter deliveries
  const filtered = deliveries.filter((d: any) => {
    if (filterCustomer && String(d.customer_id) !== String(filterCustomer)) return false;
    if (filterStatus && d.status !== filterStatus) return false;
    return true;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">送货单管理</h2><Button variant="secondary" size="sm" onClick={() => window.open('/api/deliveries/export')}>导出 CSV</Button></div>

      {/* Create form */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <h3 className="font-semibold">新建送货单</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium text-gray-700">客户</label>
            <CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">日期</label>
            <Input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
          </div>
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1"><label className="text-xs text-gray-500">产品</label><ProductSelect value={item.product_id} onChange={(v) => onProductChange(idx, v)} /></div>
            <div className="w-20"><label className="text-xs text-gray-500">数量</label><Input type="number" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} /></div>
            <div className="w-24"><label className="text-xs text-gray-500">售价</label><Input type="number" value={String(item.unit_price)} onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))} /></div>
            <div className="flex-1">
              <label className="text-xs text-gray-500">货架</label>
              <select value={item.shelf_id} onChange={(e) => updateItem(idx, 'shelf_id', Number(e.target.value))} className="w-full border rounded px-2 py-1 text-sm">
                <option value="">选货架</option>
                {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <Button variant="danger" size="sm" onClick={() => setItems(items.filter((_, i) => i !== idx))} disabled={items.length <= 1}>×</Button>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={addRow}>+ 加行</Button>
          <span className="text-sm text-gray-500 ml-auto">合计: ¥{total.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />已收款</label>
          <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} className="flex-1" />
        </div>
        <Button onClick={handleCreate} disabled={createMutation.isPending}>提交送货单</Button>
      </div>

      {/* List */}
      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold mb-3">送货单列表</h3>
        <div className="flex gap-3 mb-3">
          <CustomerSelect value={filterCustomer} onChange={(v) => setFilterCustomer(v)} />
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded px-3 py-2 text-sm">
            <option value="">全部状态</option>
            <option value="pending">待配送</option>
            <option value="delivered">已送达</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
              <th className="px-4 py-2">#</th><th className="px-4 py-2">客户</th><th className="px-4 py-2">日期</th><th className="px-4 py-2">状态</th><th className="px-4 py-2">总金额</th><th className="px-4 py-2">已付</th><th className="px-4 py-2">未付</th><th className="px-4 py-2">操作</th>
            </tr></thead>
            <tbody>
              {filtered.map((d: any) => (
                <tr key={d.id} className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(d)}>
                  <td className="px-4 py-2">#{d.id}</td>
                  <td className="px-4 py-2">{customerNames[d.customer_id] || `客户#${d.customer_id}`}</td>
                  <td className="px-4 py-2">{d.delivery_date || d.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-2"><Badge variant={d.status === 'delivered' ? 'success' : 'warning'}>{d.status}</Badge></td>
                  <td className="px-4 py-2">¥{d.total_amount || 0}</td>
                  <td className="px-4 py-2 text-green-600">¥{d.paid_amount || 0}</td>
                  <td className="px-4 py-2 text-red-600 font-medium">¥{d.unpaid_amount || 0}</td>
                  <td className="px-4 py-2"><Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); openDetail(d); }}>详情</Button></td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={8} className="text-center py-8 text-gray-400">暂无送货单</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`送货单 #${selectedDelivery?.id}`}>
        {selectedDelivery && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">总金额:</span> <strong>¥{selectedDelivery.total_amount}</strong></div>
              <div><span className="text-gray-500">已付:</span> <span className="text-green-600">¥{selectedDelivery.paid_amount}</span></div>
              <div><span className="text-gray-500">未付:</span> <span className="text-red-600 font-bold">¥{selectedDelivery.unpaid_amount}</span></div>
            </div>
            <div>
              <h4 className="text-sm font-medium mb-1">品项</h4>
              {selectedDelivery.items?.map((item: any, i: number) => (
                <div key={i} className="text-sm text-gray-600 border-b py-1">{productNames[item.product_id] || `产品#${item.product_id}`} — qty: {item.quantity}</div>
              ))}
            </div>
            <div>
              <h4 className="text-sm font-medium mb-1">收款记录</h4>
              {selectedDelivery.transactions?.map((t: any) => (
                <div key={t.id} className="text-sm text-gray-600">#{t.id} [{t.category}] ¥{t.amount} — {new Date(t.created_at).toLocaleDateString()}</div>
              ))}
            </div>
            <div className="flex gap-2 pt-2 border-t">
              <Button size="sm" onClick={() => { setSettleAmount(selectedDelivery.unpaid_amount); setSettleOpen(true); }}>结算</Button>
              <Button size="sm" variant="secondary" onClick={() => setExchangeOpen(true)}>换货</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Settle Modal */}
      <Modal open={settleOpen} onClose={() => setSettleOpen(false)} title="结算">
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">还款金额</label>
            <Input type="number" value={String(settleAmount)} onChange={(e) => setSettleAmount(Number(e.target.value))} />
          </div>
          <Button onClick={handleSettle} disabled={settleMutation.isPending}>确认还款</Button>
        </div>
      </Modal>

      {/* Exchange Modal */}
      <Modal open={exchangeOpen} onClose={() => setExchangeOpen(false)} title="换货">
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-2">退回品项</h4>
            {returnItems.map((item, idx) => (
              <div key={idx} className="flex gap-2 mb-2">
                <ProductSelect value={item.product_id} onChange={(v) => onReturnProductChange(idx, v)} />
                <Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => setReturnItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: Number(e.target.value) } : it))} className="w-20" />
                <Input type="number" placeholder="单价" value={String(item.unit_price)} onChange={(e) => setReturnItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: Number(e.target.value) } : it))} className="w-24" />
                <Button variant="danger" size="sm" onClick={() => setReturnItems(returnItems.filter((_, i) => i !== idx))} disabled={returnItems.length <= 1}>×</Button>
              </div>
            ))}
            <Button variant="secondary" size="sm" onClick={() => setReturnItems([...returnItems, { product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }])}>+</Button>
          </div>
          <div>
            <h4 className="text-sm font-medium mb-2">新品项</h4>
            {newItems.map((item, idx) => (
              <div key={idx} className="flex gap-2 mb-2">
                <ProductSelect value={item.product_id} onChange={(v) => onNewProductChange(idx, v)} />
                <Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: Number(e.target.value) } : it))} className="w-20" />
                <Input type="number" placeholder="单价" value={String(item.unit_price)} onChange={(e) => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: Number(e.target.value) } : it))} className="w-24" />
                <Button variant="danger" size="sm" onClick={() => setNewItems(newItems.filter((_, i) => i !== idx))} disabled={newItems.length <= 1}>×</Button>
              </div>
            ))}
            <Button variant="secondary" size="sm" onClick={() => setNewItems([...newItems, { product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }])}>+</Button>
          </div>
          <Button onClick={handleExchange} disabled={exchangeMutation.isPending}>确认换货</Button>
        </div>
      </Modal>
    </div>
  );
}
