import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../services/api';

export default function InventoryPage() {
  const { data: inventory = [], isLoading } = useQuery({ queryKey: ['inventory'], queryFn: dashboardApi.getInventory });

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">库存总览</h2>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
            <th className="px-4 py-3">产品ID</th><th className="px-4 py-3">货架ID</th><th className="px-4 py-3">库存数量</th>
          </tr></thead>
          <tbody>
            {isLoading ? <tr><td colSpan={3} className="text-center py-8 text-gray-400">加载中...</td></tr> :
              inventory.length === 0 ? <tr><td colSpan={3} className="text-center py-8 text-gray-400">暂无库存</td></tr> :
                inventory.map((item: any, i: number) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">#{item.product_id}</td>
                    <td className="px-4 py-3">#{item.shelf_id}</td>
                    <td className="px-4 py-3 font-medium">{item.stock}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
