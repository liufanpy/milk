import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import { saleApi, customerApi } from '../services/api';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

const saleStatusConfig = {
  confirmed: { label: '已收款', variant: 'success' as const },
  unpaid: { label: '未收款', variant: 'warning' as const },
  cancelled: { label: '已撤销', variant: 'danger' as const },
};

export default function SalesPage() {
  const [formOpen, setFormOpen] = useState(false);
  const [customerId, setCustomerId] = useState<number | string>('');
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
  const [paid, setPaid] = useState(true);
  const [note, setNote] = useState('');

  const [sales, setSales] = useState<any[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => {
    saleApi.list().then(setSales);
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
  }, []);

  const refreshSales = () => saleApi.list().then(setSales);

  const updateItem = (idx: number, field: keyof ItemRow, value: number | boolean) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const onProductChange = async (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId);
    if (productId) {
      try {
        const { price } = await customerApi.resolvePrice(customerId ? Number(customerId) : 0, productId);
        updateItem(idx, 'unit_price', price);
      } catch {}
    }
  };

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await saleApi.create({
        customer_id: customerId ? Number(customerId) : null,
        items,
        paid,
        note,
      });
      alert('销售成功');
      setFormOpen(false);
      setCustomerId('');
      setItems([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
      setPaid(true);
      setNote('');
      refreshSales();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const openDetail = async (orderId: number) => {
    const d = await saleApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async (orderId: number) => {
    if (!confirm('确定撤销此销售记录？（将反向冲抵库存和账务）')) return;
    await saleApi.cancel(orderId);
    refreshSales();
  };

  const getSaleStatus = (s: any) => {
    if (s.status === 'cancelled') return 'cancelled';
    return s.paid ? 'confirmed' : 'unpaid';
  };

  const columns = [
    { key: 'customer_name', title: '客户' },
    { key: 'items_summary', title: '品项' },
    {
      key: 'total_amount', title: '金额',
      render: (s: any) => `¥${s.total_amount.toFixed(2)}`,
    },
    {
      key: 'status', title: '状态',
      render: (s: any) => <StatusBadge status={getSaleStatus(s)} config={saleStatusConfig} />,
    },
    { key: 'created_at', title: '日期', render: (s: any) => s.created_at?.slice(0, 10) },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">直接销售（零售/自取）</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/sales/export')}>导出 CSV</Button>
          <Button onClick={() => setFormOpen(true)}>+ 新建销售</Button>
        </div>
      </div>

      <OrderListTable
        columns={columns}
        data={sales}
        rowKey={(s) => s.id}
        onRowClick={(s) => openDetail(s.id)}
      />

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建销售单"
        onSubmit={handleSubmit}
        submitLabel="提交销售"
      >
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700">客户（留空为散客）</label>
            <CustomerSelect value={customerId} onChange={setCustomerId} priceTier="零售" />
          </div>
          <ItemRowEditor
            items={items}
            onUpdate={updateItem}
            onProductChange={onProductChange}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, is_promo: false }])}
            onlyInStock
          >
            {(item, idx) => (
              <label className="flex items-center gap-1 text-xs pb-2">
                <input
                  type="checkbox"
                  checked={item.is_promo}
                  onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)}
                />
                赠送
              </label>
            )}
          </ItemRowEditor>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
            已收款
          </label>
          <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      </OrderFormModal>

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`销售单 #${detail?.id}`}
        headerInfo={
          <>
            <div>客户: {detail?.customer_name || '散客'}</div>
            <div>日期: {detail?.created_at?.slice(0, 10)}</div>
            <div>金额: ¥{detail?.total_amount?.toFixed(2)}</div>
            <div>备注: {detail?.note || '-'}</div>
          </>
        }
        items={detail?.items || []}
        status={detail ? getSaleStatus(detail) : undefined}
        statusConfig={saleStatusConfig}
      >
        {detail?.status === 'confirmed' && (
          <Button size="sm" variant="danger" onClick={() => { handleCancel(detail.id); setDetailOpen(false); }}>撤销此单</Button>
        )}
      </OrderDetailModal>
    </div>
  );
}
