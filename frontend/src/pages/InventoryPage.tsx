import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, productApi, shelfApi } from '../services/api';
import { Button } from '../components/ui/Button';

export default function InventoryPage() {
  const { data: inventory = [], isLoading } = useQuery({ queryKey: ['inventory'], queryFn: dashboardApi.getInventory });
  const [productNames, setProductNames] = useState<Record<number, string>>({});
  const [shelfNames, setShelfNames] = useState<Record<number, string>>({});

  useEffect(() => {
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
    shelfApi.list().then((data: any) => setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">库存总览</h2><Button variant="secondary" size="sm" onClick={() => window.open('/api/inventory/export')}>导出 CSV</Button></div>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
            <th className="px-4 py-3">产品</th><th className="px-4 py-3">货架</th><th className="px-4 py-3">库存数量</th>
          </tr></thead>
          <tbody>
            {isLoading ? <tr><td colSpan={3} className="text-center py-8 text-gray-400">加载中...</td></tr> :
              inventory.length === 0 ? <tr><td colSpan={3} className="text-center py-8 text-gray-400">暂无库存</td></tr> :
                inventory.map((item: any, i: number) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">{productNames[item.product_id] || `产品#${item.product_id}`}</td>
                    <td className="px-4 py-3">{shelfNames[item.shelf_id] || `货架#${item.shelf_id}`}</td>
                    <td className="px-4 py-3 font-medium">{item.stock}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
