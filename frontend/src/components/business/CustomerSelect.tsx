import { useEffect, useState } from 'react';
import { customerApi } from '../../services/api';

interface CustomerSelectProps {
  value: number | string;
  onChange: (customerId: number) => void;
  allowEmpty?: boolean;
  priceTier?: string;
}
export function CustomerSelect({ value, onChange, allowEmpty = true, priceTier }: CustomerSelectProps) {
  const [customers, setCustomers] = useState<any[]>([]);
  useEffect(() => { customerApi.list('', priceTier).then(setCustomers); }, [priceTier]);
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
    >
      {allowEmpty && <option value="">选客户</option>}
      {customers.map((c: any) => (
        <option key={c.id} value={c.id}>{c.name}</option>
      ))}
    </select>
  );
}
