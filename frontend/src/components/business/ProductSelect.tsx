import { useEffect, useState } from 'react';
import { productApi } from '../../services/api';

interface ProductSelectProps {
  value: number | string;
  onChange: (productId: number) => void;
}
export function ProductSelect({ value, onChange }: ProductSelectProps) {
  const [products, setProducts] = useState<any[]>([]);
  useEffect(() => { productApi.list().then(setProducts); }, []);
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
