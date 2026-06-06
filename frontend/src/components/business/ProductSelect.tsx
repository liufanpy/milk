import { useEffect, useState } from 'react';
import { productApi, dashboardApi } from '../../services/api';
import { ComboBox } from '../ui/ComboBox';

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
    <ComboBox
      value={value}
      onChange={(v) => onChange(Number(v))}
      options={products.map((p: any) => ({ value: p.id, label: `${p.name} (${p.brand})` }))}
      placeholder="选产品"
    />
  );
}
