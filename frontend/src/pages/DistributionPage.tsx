import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import CsvImportModal from '../components/business/CsvImportModal';
import { useDistributions, useCreateDistribution, useSettleDistribution, useExchangeDistribution } from '../hooks/useDistribution';
import { distributionApi, customerApi, productApi } from '../services/api';

interface DistributionCreateItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

const deliveryStatusConfig: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'default' }> = {
  pending: { label: '待配送', variant: 'warning' },
  delivered: { label: '已送达', variant: 'success' },
  settled: { label: '已结算', variant: 'success' },
};

export default function DistributionPage() {
  const [formOpen, setFormOpen] = useState(false);
  const [customerId, setCustomerId] = useState<number | string>('');
  const [deliveryDate, setDeliveryDate] = useState(new Date().toISOString().split('T')[0]);
  const [items, setItems] = useState<DistributionCreateItem[]>([{ product_id: 0, quantity: 1, unit_price: 0 }]);
  const [paid, setPaid] = useState(false);
  const [note, setNote] = useState('');
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  const [filterCustomer, setFilterCustomer] = useState<string | number>('');
  const [filterStatus, setFilterStatus] = useState('');
  const { data: distributions = [], refetch } = useDistributions();
  const createMutation = useCreateDistribution();
  const settleMutation = useSettleDistribution();
  const exchangeMutation = useExchangeDistribution();

  const [selectedDelivery, setSelectedDelivery] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [settleAmount, setSettleAmount] = useState(0);
  const [settleOpen, setSettleOpen] = useState(false);
  const [exchangeOpen, setExchangeOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [returnItems, setReturnItems] = useState<DistributionCreateItem[]>([{ product_id: 0, quantity: 1, unit_price: 0 }]);
  const [newItems, setNewItems] = useState<DistributionCreateItem[]>([{ product_id: 0, quantity: 1, unit_price: 0 }]);

  useEffect(() => {
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
  }, []);

  const updateItem = (idx: number, field: keyof DistributionCreateItem, value: number | boolean) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const onProductChange = async (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId as number);
    if (productId) {
      try {
        const { price } = await customerApi.resolvePrice(customerId ? Number(customerId) : 0, productId);
        updateItem(idx, 'unit_price', price);
      } catch {}
    }
  };

  const handleCreate = async () => {
    if (!customerId || items.some(i => !i.product_id || !i.quantity)) {
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
      alert('铺货单创建成功');
      setCustomerId(''); setItems([{ product_id: 0, quantity: 1, unit_price: 0 }]); setNote('');
      setFormOpen(false);
      refetch();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const openDetail = async (d: any) => {
    const detail = await distributionApi.get(d.id);
    setSelectedDelivery(detail);
    setDetailOpen(true);
  };

  const handleSettle = async () => {
    if (!selectedDelivery || settleAmount <= 0) return;
    await settleMutation.mutateAsync({ id: selectedDelivery.id, amount: settleAmount });
    alert('结算成功');
    setSettleOpen(false);
    const detail = await distributionApi.get(selectedDelivery.id);
    setSelectedDelivery(detail);
    refetch();
  };

  const exchangeCustomerId = selectedDelivery?.customer_id;
  const returnTotal = returnItems.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);
  const newTotal = newItems.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);
  const exchangeAmountMatch = Math.abs(returnTotal - newTotal) < 0.001;

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
    if (!exchangeAmountMatch) { alert('换货金额不一致，请走退货结算后重新开单'); return; }
    if (returnItems.some(i => !i.product_id || !i.quantity) || newItems.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await exchangeMutation.mutateAsync({
        id: selectedDelivery.id,
        data: { return_items: returnItems, new_items: newItems },
      });
      alert('换货成功');
      setExchangeOpen(false);
      setReturnItems([{ product_id: 0, quantity: 1, unit_price: 0 }]);
      setNewItems([{ product_id: 0, quantity: 1, unit_price: 0 }]);
      const detail = await distributionApi.get(selectedDelivery.id);
      setSelectedDelivery(detail);
      refetch();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '换货失败');
    }
  };

  const filtered = distributions.filter((d: any) => {
    if (filterCustomer && String(d.customer_id) !== String(filterCustomer)) return false;
    if (filterStatus && d.status !== filterStatus) return false;
    return true;
  });

  const columns = [
    { key: 'order_number', title: '单号', render: (d: any) => d.order_number || `#${d.id}` },
    { key: 'customer_name', title: '客户', render: (d: any) => customerNames[d.customer_id] || `客户#${d.customer_id}` },
    { key: 'delivery_date', title: '日期', render: (d: any) => d.delivery_date || d.created_at?.slice(0, 10) },
    {
      key: 'status', title: '状态',
      render: (d: any) => <StatusBadge status={d.status} config={deliveryStatusConfig} />,
    },
    { key: 'total_amount', title: '总金额', render: (d: any) => `¥${d.total_amount || 0}` },
    { key: 'paid_amount', title: '已付', render: (d: any) => <span className="text-green-600">¥{d.paid_amount || 0}</span> },
    { key: 'unpaid_amount', title: '未付', render: (d: any) => <span className="text-red-600 font-medium">¥{d.unpaid_amount || 0}</span> },
    {
      key: 'actions', title: '操作',
      render: (d: any) => (
        <div onClick={(e) => e.stopPropagation()}>
          <Button size="sm" variant="secondary" onClick={() => openDetail(d)}>详情</Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">铺货单管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/distribution-orders/export')}>导出 CSV</Button>
          <Button onClick={() => setFormOpen(true)}>+ 新建铺货</Button>
        </div>
      </div>

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建铺货单"
        onSubmit={handleCreate}
        isPending={createMutation.isPending}
        submitLabel="提交铺货单"
      >
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-gray-700">客户</label>
              <CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} priceTier="批发" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">日期</label>
              <Input type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
            </div>
          </div>
          <ItemRowEditor
            items={items}
            onUpdate={updateItem}
            onProductChange={onProductChange}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0 }])}
            onlyInStock
          />
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />已收款
            </label>
            <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} className="flex-1" />
          </div>
        </div>
      </OrderFormModal>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold mb-3">铺货单列表</h3>
        <div className="flex gap-3 mb-3">
          <CustomerSelect value={filterCustomer} onChange={(v) => setFilterCustomer(v)} priceTier="批发" />
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded px-3 py-2 text-sm">
            <option value="">全部状态</option>
            <option value="pending">待配送</option>
            <option value="delivered">已送达</option>
            <option value="settled">已结算</option>
          </select>
        </div>
        <OrderListTable
          columns={columns}
          data={filtered}
          rowKey={(d) => d.id}
          onRowClick={(d) => openDetail(d)}
        />
      </div>

      {/* Detail Modal */}
      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`铺货单 #${selectedDelivery?.id}`}
        headerInfo={
          <>
            <div>客户: {customerNames[selectedDelivery?.customer_id] || `客户#${selectedDelivery?.customer_id}`}</div>
            <div>日期: {selectedDelivery?.delivery_date || selectedDelivery?.created_at?.slice(0, 10)}</div>
          </>
        }
        items={selectedDelivery?.items || []}
        status={selectedDelivery?.status}
        statusConfig={deliveryStatusConfig}
      >
        <div className="w-full space-y-3">
          {selectedDelivery?.exchanges?.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">换货记录</h4>
              {selectedDelivery.exchanges.map((ex: any, i: number) => (
                <div key={i} className="text-sm mb-2 pl-3 border-l-2 border-gray-200">
                  <div className="text-xs text-gray-400 mb-1">{ex.created_at}</div>
                  {ex.return_items?.map((item: any, j: number) => (
                    <div key={`ret-${j}`} className="text-gray-400 line-through">
                      退回 {productNames[item.product_id] || `产品#${item.product_id}`} ×{item.quantity} ¥{item.unit_price}
                    </div>
                  ))}
                  {ex.new_items?.map((item: any, j: number) => (
                    <div key={`new-${j}`} className="text-gray-600">
                      换入 {productNames[item.product_id] || `产品#${item.product_id}`} ×{item.quantity} ¥{item.unit_price}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2 border-t pt-2">
            <div className="flex-1 text-sm space-y-1">
              <div>总金额: ¥{selectedDelivery?.total_amount}</div>
              <div>已付: <span className="text-green-600">¥{selectedDelivery?.paid_amount}</span></div>
              <div>未付: <span className="text-red-600 font-bold">¥{selectedDelivery?.unpaid_amount}</span></div>
            </div>
            <div className="flex gap-2 items-start">
              <Button size="sm" onClick={() => { setSettleAmount(selectedDelivery?.unpaid_amount || 0); setSettleOpen(true); }}>结算</Button>
              <Button size="sm" variant="secondary" onClick={() => setExchangeOpen(true)}>换货</Button>
            </div>
          </div>
        </div>
      </OrderDetailModal>

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

      {/* Exchange Modal — keep as-is, this is complex custom logic */}
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
            <Button variant="secondary" size="sm" onClick={() => setReturnItems([...returnItems, { product_id: 0, quantity: 1, unit_price: 0 }])}>+</Button>
          </div>
          <div>
            <h4 className="text-sm font-medium mb-2">新品项</h4>
            {newItems.map((item, idx) => (
              <div key={idx} className="flex gap-2 mb-2">
                <ProductSelect value={item.product_id} onChange={(v) => onNewProductChange(idx, v)} onlyInStock />
                <Input type="number" placeholder="数量" value={String(item.quantity)} onChange={(e) => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, quantity: Number(e.target.value) } : it))} className="w-20" />
                <Input type="number" placeholder="单价" value={String(item.unit_price)} onChange={(e) => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: Number(e.target.value) } : it))} className="w-24" />
                <Button variant="danger" size="sm" onClick={() => setNewItems(newItems.filter((_, i) => i !== idx))} disabled={newItems.length <= 1}>×</Button>
              </div>
            ))}
            <Button variant="secondary" size="sm" onClick={() => setNewItems([...newItems, { product_id: 0, quantity: 1, unit_price: 0 }])}>+</Button>
          </div>
          <div className="text-sm text-gray-500 pt-2 border-t">
            <div>退回合计: ¥{returnTotal.toFixed(2)}</div>
            <div>新发合计: ¥{newTotal.toFixed(2)}</div>
            {!exchangeAmountMatch && <div className="text-red-500 font-medium">金额不一致，无法换货</div>}
          </div>
          <Button onClick={handleExchange} disabled={exchangeMutation.isPending}>确认换货</Button>
        </div>
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入铺货"
        onImport={(file) => distributionApi.importFile(file)}
        onConfirm={(rows) => distributionApi.confirmImport(rows)}
        onDone={() => refetch()}
      />
    </div>
  );
}
