import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { subscriptionApi, customerApi } from '../services/api';

export default function SubscriptionsPage() {
  const navigate = useNavigate();
  const [customerId, setCustomerId] = useState<number | string>('');
  const [paidAmount, setPaidAmount] = useState(0);
  const [isPaid, setIsPaid] = useState(true);
  const [note, setNote] = useState('');
  const [orders, setOrders] = useState<any[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  useEffect(() => {
    subscriptionApi.list().then(setOrders);
    customerApi.list().then((data: any) =>
      setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name])))
    );
  }, []);

  const handleCreate = async () => {
    if (!customerId || paidAmount <= 0) { alert('请填写完整'); return; }
    await subscriptionApi.create({
      customer_id: Number(customerId),
      paid_amount: paidAmount,
      is_paid: isPaid,
      note,
    });
    alert('订奶单创建成功');
    setCustomerId(''); setPaidAmount(0); setIsPaid(true); setNote('');
    subscriptionApi.list().then(setOrders);
  };

  const statusLabel = (s: string) =>
    s === 'active' ? '进行中' : s === 'completed' ? '已完成' : s === 'cancelled' ? '已取消' : s;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">订奶管理</h2>

      {/* 创建表单 */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <h3 className="font-semibold">新建订奶单</h3>
        <div>
          <label className="text-sm font-medium text-gray-700">客户</label>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
        </div>
        <Input
          label="实付金额"
          type="number"
          value={String(paidAmount)}
          onChange={(e) => setPaidAmount(Number(e.target.value))}
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isPaid} onChange={(e) => setIsPaid(e.target.checked)} />
          已收款
        </label>
        <Input placeholder="备注（可选）" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleCreate}>创建订奶单</Button>
      </div>

      {/* 列表 */}
      <h3 className="text-lg font-semibold mb-2">订奶单列表</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-gray-600">
              <th className="px-4 py-2">#</th>
              <th className="px-4 py-2">客户</th>
              <th className="px-4 py-2">实付金额</th>
              <th className="px-4 py-2">剩余金额</th>
              <th className="px-4 py-2">状态</th>
              <th className="px-4 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o: any) => (
              <tr key={o.id} className="border-b">
                <td className="px-4 py-2">#{o.id}</td>
                <td className="px-4 py-2">{customerNames[o.customer_id] || `客户#${o.customer_id}`}</td>
                <td className="px-4 py-2">¥{o.paid_amount}</td>
                <td className="px-4 py-2 font-medium">¥{o.remaining_amount}</td>
                <td className="px-4 py-2">{statusLabel(o.status)}</td>
                <td className="px-4 py-2">
                  <Button size="sm" variant="secondary" onClick={() => navigate(`/subscriptions/${o.id}`)}>
                    详情
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
