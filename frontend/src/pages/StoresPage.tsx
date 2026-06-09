import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { OrderListTable } from '../components/business/OrderListTable';
import { storeApi, customerApi } from '../services/api';
import type { Store } from '../types';

export default function StoresPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState('');
  const [customerId, setCustomerId] = useState<number | string>('');
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStores();
    customerApi.list().then(setCustomers);
  }, []);

  const loadStores = () => storeApi.list().then(setStores);

  const handleCreate = async () => {
    if (!name) { alert('请输入店名'); return; }
    setLoading(true);
    try {
      await storeApi.create({ name, customer_id: Number(customerId) || null, address });
      setFormOpen(false);
      setName('');
      setCustomerId('');
      setAddress('');
      loadStores();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    } finally { setLoading(false); }
  };

  const columns = [
    { key: 'name', title: '店名', render: (s: Store) => <span className="font-medium">{s.name}</span> },
    { key: 'customer_name', title: '关联客户' },
    { key: 'address', title: '地址' },
    { key: 'status', title: '状态' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">店铺管理</h2>
        <Button onClick={() => setFormOpen(true)}>+ 新建店铺</Button>
      </div>

      <OrderListTable columns={columns} data={stores} rowKey={(s) => s.id} />

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title="新建店铺">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">店名</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="店名" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">关联客户</label>
            <select
              value={customerId}
              onChange={(e) => setCustomerId(Number(e.target.value))}
              className="w-full border rounded px-3 py-2 text-sm mt-1"
            >
              <option value="">不关联</option>
              {customers.map((c: any) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">地址</label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="地址" />
          </div>
          <div className="flex gap-2 pt-2 border-t">
            <Button onClick={handleCreate} disabled={loading}>创建</Button>
            <Button variant="secondary" onClick={() => setFormOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
