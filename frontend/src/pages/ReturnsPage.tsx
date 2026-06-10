import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import CsvImportModal from '../components/business/CsvImportModal';
import { returnApi, customerApi } from '../services/api';

interface ReturnItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

const defaultForm = {
  customer_id: '' as number | string,
  note: '',
};

const returnStatusConfig = {
  confirmed: { label: '已确认', variant: 'success' as const },
  cancelled: { label: '已撤销', variant: 'danger' as const },
};

export default function ReturnsPage() {
  // 新建
  const [formOpen, setFormOpen] = useState(false);
  const [header, setHeader] = useState(defaultForm);
  const [items, setItems] = useState<ReturnItem[]>([
    { product_id: 0, quantity: 1, unit_price: 0 },
  ]);

  // 列表
  const [returns, setReturns] = useState<any[]>([]);

  // 详情
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [importOpen, setImportOpen] = useState(false);

  const loadReturns = useCallback(() => returnApi.list().then(setReturns), []);

  useEffect(() => {
    loadReturns();
  }, [loadReturns]);

  const updateItem = (idx: number, field: keyof ReturnItem, value: number | boolean) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (!header.customer_id || items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await returnApi.create({
        customer_id: Number(header.customer_id),
        items,
        note: header.note,
      });
      alert('退货成功');
      setFormOpen(false);
      setHeader(defaultForm);
      setItems([{ product_id: 0, quantity: 1, unit_price: 0 }]);
      loadReturns();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const openDetail = async (r: any) => {
    const d = await returnApi.get(r.id);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async () => {
    if (!detail || !confirm('确定撤销此退货单？将反向冲抵库存和退款')) return;
    try {
      await returnApi.cancel(detail.id);
      alert('已撤销');
      setDetailOpen(false);
      loadReturns();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '撤销失败');
    }
  };

  const columns = [
    { key: 'order_number', title: '单号', render: (r: any) => r.order_number || `#${r.id}` },
    { key: 'customer_name', title: '客户' },
    { key: 'items_summary', title: '品项' },
    {
      key: 'total_refund', title: '退款金额',
      render: (r: any) => `¥${r.total_refund.toFixed(2)}`,
    },
    {
      key: 'status', title: '状态',
      render: (r: any) => <StatusBadge status={r.status} config={returnStatusConfig} />,
    },
    { key: 'created_at', title: '日期', render: (r: any) => r.created_at?.slice(0, 10) },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">退货管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/returns/export')}>导出 CSV</Button>
          <Button onClick={() => setFormOpen(true)}>+ 新建退货</Button>
        </div>
      </div>

      <OrderListTable
        columns={columns}
        data={returns}
        rowKey={(r) => r.id}
        onRowClick={openDetail}
      />

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建退货单"
        onSubmit={handleSubmit}
        submitLabel="提交退货"
      >
        <div className="space-y-3">
          <CustomerSelect value={header.customer_id} onChange={(v) => setHeader({ ...header, customer_id: v })} />
          <ItemRowEditor
            items={items}
            onUpdate={updateItem}
            onProductChange={(idx, pid) => {
              updateItem(idx, 'product_id', pid);
              if (pid && header.customer_id) {
                customerApi.resolvePrice(Number(header.customer_id), pid)
                  .then(({ price }: any) => updateItem(idx, 'unit_price', price))
                  .catch(() => {});
              }
            }}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0 }])}
          />
          <Input placeholder="备注" value={header.note}
            onChange={(e) => setHeader({ ...header, note: e.target.value })} />
        </div>
      </OrderFormModal>

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`退货单 #${detail?.id}`}
        headerInfo={
          <>
            <div>客户: {detail?.customer_name}</div>
            <div>退款: ¥{detail?.total_refund?.toFixed(2)}</div>
          </>
        }
        items={detail?.items || []}
        status={detail?.status}
        statusConfig={returnStatusConfig}
      >
        {detail?.status === 'confirmed' && (
          <Button size="sm" variant="danger" onClick={handleCancel}>撤销</Button>
        )}
      </OrderDetailModal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入退货"
        onImport={(file) => returnApi.importFile(file)}
        onConfirm={(rows) => returnApi.confirmImport(rows)}
        onDone={() => loadReturns()}
      />
    </div>
  );
}
