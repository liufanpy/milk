import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { OrderListTable } from '../components/business/OrderListTable';
import { StatusBadge } from '../components/ui/StatusBadge';
import { subscriptionApi, customerApi } from '../services/api';

const subStatusConfig = {
  active: { label: '进行中', variant: 'success' as const },
  completed: { label: '已完成', variant: 'default' as const },
  cancelled: { label: '已取消', variant: 'danger' as const },
};

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

  const columns = [
    { key: 'id', title: '#', render: (o: any) => `#${o.id}` },
    { key: 'customer_name', title: '客户', render: (o: any) => customerNames[o.customer_id] || `客户#${o.customer_id}` },
    { key: 'paid_amount', title: '实付金额', render: (o: any) => `¥${o.paid_amount}` },
    { key: 'remaining_amount', title: '剩余金额', render: (o: any) => <span className="font-medium">¥{o.remaining_amount}</span> },
    { key: 'status', title: '状态', render: (o: any) => <StatusBadge status={o.status} config={subStatusConfig} /> },
    {
      key: 'actions', title: '操作',
      render: (o: any) => (
        <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); navigate(`/subscriptions/${o.id}`); }}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">订奶管理</h2>

      {/* 创建表单 — 不动，结构特殊不是品项行模式 */}
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

      <h3 className="text-lg font-semibold mb-2">订奶单列表</h3>
      <OrderListTable
        columns={columns}
        data={orders}
        rowKey={(o) => o.id}
      />
    </div>
  );
}
