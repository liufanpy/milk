import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { saleApi, customerApi } from '../services/api';
import { RetailOrder, RetailOrderDetail } from '../types';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

export default function SalesPage() {
  const [customerId, setCustomerId] = useState<number | string>('');
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
  const [paid, setPaid] = useState(true);
  const [note, setNote] = useState('');
  const [sales, setSales] = useState<RetailOrder[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<RetailOrderDetail | null>(null);

  useEffect(() => {
    saleApi.list().then(setSales);
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
  }, []);

  const refreshSales = () => saleApi.list().then(setSales);

  const updateItem = (idx: number, field: keyof ItemRow, value: number | boolean) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };
  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);

  const onProductChange = async (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId);
    if (productId) {
      try {
        const { price } = await customerApi.resolvePrice(customerId ? Number(customerId) : 0, productId);
        updateItem(idx, 'unit_price', price);
      } catch {}
    }
  };
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.quantity)) {
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
    setItems([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
    setPaid(true);
    setNote('');
    refreshSales();
  };

  const handleCancel = async (orderId: number) => {
    if (!confirm('确定撤销此销售记录？（将反向冲抵库存和账务）')) return;
    await saleApi.cancel(orderId);
    refreshSales();
  };

  const openDetail = async (orderId: number) => {
    const d = await saleApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">直接销售（零售/自取）</h2>
        <Button variant="secondary" size="sm" onClick={() => window.open('/api/sales/export')}>导出 CSV</Button>
      </div>

      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div>
          <label className="text-sm font-medium text-gray-700">客户（留空为散客）</label>
          <CustomerSelect value={customerId} onChange={setCustomerId} priceTier="零售" />
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500">产品</label>
              <ProductSelect value={item.product_id} onChange={(v) => onProductChange(idx, v)} onlyInStock />
            </div>
            <div className="w-20">
              <label className="text-xs text-gray-500">数量</label>
              <Input type="number" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} />
            </div>
            <div className="w-24">
              <label className="text-xs text-gray-500">售价</label>
              <Input type="number" value={String(item.unit_price)} onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))} />
            </div>
            <label className="flex items-center gap-1 text-xs pb-2">
              <input type="checkbox" checked={item.is_promo} onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)} />
              赠送
            </label>
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
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="px-4 py-2 text-left">客户</th>
              <th className="px-4 py-2 text-left">品项</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-right">日期</th>
              <th className="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(s.id)}>
                <td className="px-4 py-2 font-medium">{s.customer_name}</td>
                <td className="px-4 py-2 text-gray-500">{s.items_summary}</td>
                <td className="px-4 py-2 text-right">¥{s.total_amount.toFixed(2)}</td>
                <td className="px-4 py-2 text-center">
                  {s.status === 'confirmed' ? (
                    <Badge variant={s.paid ? 'success' : 'warning'}>{s.paid ? '已收款' : '未收款'}</Badge>
                  ) : (
                    <Badge variant="danger">已撤销</Badge>
                  )}
                </td>
                <td className="px-4 py-2 text-right text-gray-400">{new Date(s.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                  {s.status === 'confirmed' && (
                    <Button variant="danger" size="sm" onClick={() => handleCancel(s.id)}>撤销</Button>
                  )}
                </td>
              </tr>
            ))}
            {sales.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">暂无销售记录</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title="销售详情">
        {detail && (
          <div className="space-y-3">
            <div className="flex gap-4 text-sm">
              <span>客户: {detail.customer_name}</span>
              <span>日期: {new Date(detail.created_at).toLocaleDateString()}</span>
              <span>
                状态:{' '}
                {detail.status === 'confirmed' ? (
                  <Badge variant={detail.paid ? 'success' : 'warning'}>{detail.paid ? '已收款' : '未收款'}</Badge>
                ) : (
                  <Badge variant="danger">已撤销</Badge>
                )}
              </span>
            </div>
            <table className="w-full text-sm border-t mt-2">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left">产品</th>
                  <th className="px-2 py-1 text-right">数量</th>
                  <th className="px-2 py-1 text-right">售价</th>
                  <th className="px-2 py-1 text-right">小计</th>
                </tr>
              </thead>
              <tbody>
                {detail.items.map((it, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">
                      {it.product_name}
                      {it.unit_price === 0 && <span className="ml-1 text-yellow-600 text-xs">赠</span>}
                    </td>
                    <td className="px-2 py-1 text-right">{it.quantity}</td>
                    <td className="px-2 py-1 text-right">¥{it.unit_price.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_price).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-right font-bold">合计: ¥{detail.total_amount.toFixed(2)}</div>
            {detail.status === 'confirmed' && (
              <div className="flex justify-end">
                <Button variant="danger" size="sm" onClick={() => { handleCancel(detail.id); setDetailOpen(false); }}>撤销此单</Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
