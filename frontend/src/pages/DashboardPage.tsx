import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, productApi, shelfApi, customerApi } from '../services/api';
import { Badge } from '../components/ui/Badge';

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: dashboardApi.get });
  const { data: receivables = [] } = useQuery({ queryKey: ['receivables'], queryFn: dashboardApi.getReceivables });
  const [productNames, setProductNames] = useState<Record<number, string>>({});
  const [shelfNames, setShelfNames] = useState<Record<number, string>>({});
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  useEffect(() => {
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
    shelfApi.list().then((data: any) => setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))));
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
  }, []);

  if (isLoading) return <p className="text-gray-400">加载中...</p>;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">经营看板</h2>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日销售</div>
          <div className="text-2xl font-bold text-green-600">¥{data?.today_sales || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日收款</div>
          <div className="text-2xl font-bold text-blue-600">¥{data?.today_payments || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日出库</div>
          <div className="text-2xl font-bold">{data?.today_out_quantity || 0} 件</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-3">低库存预警（&lt; 10）</h3>
          {data?.low_stock?.length === 0 ? <p className="text-gray-400 text-sm">无预警</p> : (
            data?.low_stock?.map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm py-1 border-b">
                <span>{productNames[item.product_id] || `产品#${item.product_id}`} {shelfNames[item.shelf_id] || `货架#${item.shelf_id}`}</span>
                <Badge variant="warning">{item.stock}</Badge>
              </div>
            ))
          )}
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-3">应收排行 Top 5</h3>
          {receivables.length === 0 ? <p className="text-gray-400 text-sm">无应收</p> : (
            receivables.slice(0, 5).map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm py-1 border-b">
                <span>{customerNames[item.customer_id] || `客户#${item.customer_id}`}</span>
                <span className="font-medium text-red-600">¥{item.ar_balance}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
