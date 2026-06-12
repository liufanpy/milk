import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { inventoryCheckApi } from '../services/api';
import { Button } from '../components/ui/Button';
import { OrderListTable } from '../components/business/OrderListTable';
import { InventoryCheck, InventoryCheckItem } from '../types';

const STATUS_LABELS: Record<string, string> = { draft: '草稿', confirmed: '已确认' };

export default function InventoryChecksPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ? Number(id) : null;

  // list state
  const [checks, setChecks] = useState<InventoryCheck[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  // detail state
  const [detail, setDetail] = useState<InventoryCheck | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [items, setItems] = useState<InventoryCheckItem[]>([]);

  useEffect(() => {
    if (documentId) {
      loadDetail();
    } else {
      loadList();
    }
  }, [documentId]);

  const loadList = async () => {
    setListLoading(true);
    try {
      const data = await inventoryCheckApi.list();
      setChecks(data);
    } finally {
      setListLoading(false);
    }
  };

  const loadDetail = async () => {
    if (!documentId) return;
    setDetailLoading(true);
    try {
      const data = await inventoryCheckApi.get(documentId);
      setDetail(data);
      setItems(data.items || []);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const result = await inventoryCheckApi.create();
      navigate(`/inventory-checks/${result.id}`);
    } catch (e: any) {
      alert('创建失败：' + (e.response?.data?.detail || e.message));
    }
  };

  const handleSave = async () => {
    if (!documentId) return;
    setSaving(true);
    const payload = items.map(it => ({
      product_id: it.product_id,
      actual_qty: it.actual_qty,
    }));
    try {
      await inventoryCheckApi.saveItems(documentId, payload);
      loadDetail();
    } catch (e: any) {
      alert('保存失败：' + (e.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  const handleConfirm = async () => {
    if (!documentId) return;
    if (!confirm('确认后盘点单将锁定，不可再修改。确定要确认吗？')) return;
    setConfirming(true);
    try {
      await inventoryCheckApi.confirm(documentId);
      loadDetail();
    } catch (e: any) {
      alert('确认失败：' + (e.response?.data?.detail || e.message));
    } finally {
      setConfirming(false);
    }
  };

  // ——— list view ———
  if (!documentId) {
    const columns = [
      { key: 'order_number', title: '单号' },
      { key: 'check_date', title: '盘点日期' },
      {
        key: 'status',
        title: '状态',
        render: (r: InventoryCheck) => (
          <span className={r.status === 'confirmed' ? 'text-green-600 font-medium' : 'text-orange-500 font-medium'}>
            {STATUS_LABELS[r.status] || r.status}
          </span>
        ),
      },
      { key: 'item_count', title: '产品数' },
      { key: 'note', title: '备注' },
      { key: 'confirmed_at', title: '确认时间', render: (r: InventoryCheck) => r.confirmed_at?.slice(0, 19).replace('T', ' ') || '-' },
    ];

    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">盘点单</h2>
          <Button onClick={handleCreate}>新建盘点</Button>
        </div>
        <OrderListTable
          columns={columns}
          data={checks}
          rowKey={(r) => r.id}
          isLoading={listLoading}
          onRowClick={(r) => navigate(`/inventory-checks/${r.id}`)}
        />
      </div>
    );
  }

  // ——— detail view ———
  if (detailLoading) {
    return <div className="text-center py-8 text-gray-400">加载中...</div>;
  }
  if (!detail) {
    return <div className="text-center py-8 text-gray-400">盘点单不存在</div>;
  }

  const isDraft = detail.status === 'draft';

  const handleActualQtyChange = (idx: number, value: string) => {
    setItems((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], actual_qty: value === '' ? null : Number(value) };
      return next;
    });
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate('/inventory-checks')} className="text-blue-600 hover:underline text-sm">
          &larr; 返回列表
        </button>
        <h2 className="text-xl font-bold">盘点单 {detail.order_number}</h2>
        <span className={`px-2 py-0.5 rounded text-sm font-medium ${isDraft ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
          {STATUS_LABELS[detail.status] || detail.status}
        </span>
      </div>

      <div className="text-sm text-gray-500 mb-4">
        盘点日期：{detail.check_date}
        {detail.confirmed_at && <> | 确认时间：{detail.confirmed_at.slice(0, 19).replace('T', ' ')}</>}
        {detail.note && <> | 备注：{detail.note}</>}
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="px-4 py-3 text-left font-medium">产品</th>
              <th className="px-4 py-3 text-left font-medium">理论库存</th>
              <th className="px-4 py-3 text-left font-medium">实盘数量</th>
              <th className="px-4 py-3 text-left font-medium">差异</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center py-8 text-gray-400">暂无明细</td>
              </tr>
            ) : (
              items.map((it, idx) => (
                <tr key={it.product_id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3">{it.product_name}</td>
                  <td className="px-4 py-3 font-medium">{it.theoretical_qty}</td>
                  <td className="px-4 py-3">
                    {isDraft ? (
                      <input
                        type="number"
                        className="border rounded px-2 py-1 w-24 text-sm"
                        value={it.actual_qty ?? ''}
                        onChange={(e) => handleActualQtyChange(idx, e.target.value)}
                      />
                    ) : (
                      <span className="font-medium">{it.actual_qty ?? '-'}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {it.difference == null ? (
                      <span className="text-gray-400">-</span>
                    ) : it.difference > 0 ? (
                      <span className="text-green-600 font-medium">+{it.difference} 盘盈</span>
                    ) : it.difference < 0 ? (
                      <span className="text-red-600 font-medium">{it.difference} 盘亏</span>
                    ) : (
                      <span className="text-gray-500">0 持平</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {isDraft && (
        <div className="flex gap-3 mt-4">
          <Button variant="secondary" onClick={handleSave} disabled={saving}>保存草稿</Button>
          <Button onClick={handleConfirm} disabled={confirming}>确认盘点</Button>
        </div>
      )}
    </div>
  );
}
