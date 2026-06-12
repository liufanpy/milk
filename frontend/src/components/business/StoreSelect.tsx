import { useEffect, useState } from 'react';
import { storeApi } from '../../services/api';
import { ComboBox } from '../ui/ComboBox';

interface StoreSelectProps {
  value: number | string;
  onChange: (storeId: number) => void;
}
export function StoreSelect({ value, onChange }: StoreSelectProps) {
  const [stores, setStores] = useState<any[]>([]);
  useEffect(() => { storeApi.list().then(setStores); }, []);
  return (
    <ComboBox
      value={value}
      onChange={(v) => onChange(Number(v) || 0)}
      options={stores.map((s: any) => ({ value: s.id, label: s.name }))}
      placeholder="选店铺"
    />
  );
}
