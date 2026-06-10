import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import { wastageApi } from '../services/api';

interface WastageItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

const wastageStatusConfig = {
  confirmed: { label: '已确认', variant: 'success' as const },
  cancelled: { label: '已撤销', variant: 'danger' as const },
};

export default function WastagePage() {
  const [formOpen, setFormOpen] = useState(false);
  const [items, setItems] = useState<WastageItem[]>([
    { product_id: 0, quantity: 1, unit_price: 0 },
  ]);
  const [note, setNote] = useState('');

  const [records, setRecords] = useState<any[]>([]);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);

  const loadRecords = useCallback(() => wastageApi.list().then(setRecords), []);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const updateItem = (idx: number, field: keyof WastageItem, value: number | boolean | string) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await wastageApi.create({ items, note });
      alert('损耗记录成功');
      setFormOpen(false);
      setItems([{ product_id: 0, quantity: 1, unit_price: 0 }]);
      setNote('');
      loadRecords();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const openDetail = async (r: any) => {
    const d = await wastageApi.get(r.id);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async () => {
    if (!detail || !confirm('确定撤销此损耗单？将恢复库存')) return;
    try {
      await wastageApi.cancel(detail.id);
      alert('已撤销');
      setDetailOpen(false);
      loadRecords();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '撤销失败');
    }
  };

  const columns = [
    { key: 'order_number', title: '单号', render: (r: any) => r.order_number || `#${r.id}` },
    { key: 'items_summary', title: '品项' },
    { key: 'reasons', title: '原因', render: () => '损耗' },
    {
      key: 'status', title: '状态',
      render: (r: any) => <StatusBadge status={r.status} config={wastageStatusConfig} />,
    },
    { key: 'created_at', title: '日期', render: (r: any) => r.created_at?.slice(0, 10) },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">损耗管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/wastage/export')}>导出 CSV</Button>
          <Button onClick={() => setFormOpen(true)}>+ 新建损耗</Button>
        </div>
      </div>

      <OrderListTable
        columns={columns}
        data={records}
        rowKey={(r) => r.id}
        onRowClick={openDetail}
      />

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建损耗单"
        onSubmit={handleSubmit}
        submitLabel="提交损耗"
      >
        <div className="space-y-3">
          <ItemRowEditor
            items={items}
            onUpdate={(idx, field, value) => updateItem(idx, field as keyof WastageItem, value)}
            onProductChange={(idx, pid) => updateItem(idx, 'product_id', pid)}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0 }])}
            onlyInStock
          >
            {() => null}
          </ItemRowEditor>
          <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      </OrderFormModal>

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`损耗单 #${detail?.id}`}
        headerInfo={
          <>
            <div>备注: {detail?.note || '-'}</div>
            <div>总成本: ¥{detail?.total_cost?.toFixed(2)}</div>
            <div>日期: {detail?.created_at?.slice(0, 10)}</div>
          </>
        }
        items={detail?.items || []}
        status={detail?.status}
        statusConfig={wastageStatusConfig}
      >
        {detail?.status === 'confirmed' && (
          <Button size="sm" variant="danger" onClick={handleCancel}>撤销</Button>
        )}
      </OrderDetailModal>
    </div>
  );
}
