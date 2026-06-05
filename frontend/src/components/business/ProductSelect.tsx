import { useEffect, useState } from 'react';
import { productApi, dashboardApi } from '../../services/api';

interface ProductSelectProps {
  value: number | string;
  onChange: (productId: number) => void;
  onlyInStock?: boolean;
}
export function ProductSelect({ value, onChange, onlyInStock }: ProductSelectProps) {
  const [products, setProducts] = useState<any[]>([]);
  useEffect(() => {
    let cancelled = false;
    if (onlyInStock) {
      Promise.all([productApi.list(), dashboardApi.getInventory()])
        .then(([all, inv]) => {
          if (cancelled) return;
          const inStockIds = new Set((inv as any[]).map((r: any) => r.product_id));
          setProducts(all.filter((p: any) => inStockIds.has(p.id)));
        })
        .catch(() => {});
    } else {
      productApi.list().then((data) => { if (!cancelled) setProducts(data); }).catch(() => {});
    }
    return () => { cancelled = true; };
  }, [onlyInStock]);
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
    >
      <option value="">选产品</option>
      {products.map((p: any) => (
        <option key={p.id} value={p.id}>{p.name} ({p.brand})</option>
      ))}
    </select>
  );
}
