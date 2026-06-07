import { ReactNode } from 'react';
import { Button } from './Button';
import { Input } from './Input';
import { ProductSelect } from '../business/ProductSelect';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
}

interface ItemRowEditorProps<T extends ItemRow> {
  items: T[];
  onUpdate: (idx: number, field: keyof T, value: number | boolean) => void;
  onProductChange: (idx: number, productId: number) => void;
  onRemove: (idx: number) => void;
  onAdd: () => void;
  minRows?: number;
  onlyInStock?: boolean;
  children?: (item: T, idx: number) => ReactNode;
}

export function ItemRowEditor<T extends ItemRow>({
  items,
  onUpdate,
  onProductChange,
  onRemove,
  onAdd,
  minRows = 1,
  onlyInStock = false,
  children,
}: ItemRowEditorProps<T>) {
  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx} className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500">产品</label>
            <ProductSelect
              value={item.product_id}
              onChange={(v) => onProductChange(idx, v)}
              onlyInStock={onlyInStock}
            />
          </div>
          <div className="w-20">
            <label className="text-xs text-gray-500">数量</label>
            <Input
              type="number"
              value={String(item.quantity)}
              onChange={(e) => onUpdate(idx, 'quantity' as keyof T, Number(e.target.value))}
            />
          </div>
          <div className="w-24">
            <label className="text-xs text-gray-500">单价</label>
            <Input
              type="number"
              value={String(item.unit_price)}
              onChange={(e) => onUpdate(idx, 'unit_price' as keyof T, Number(e.target.value))}
            />
          </div>
          {children?.(item, idx)}
          <Button
            variant="danger"
            size="sm"
            onClick={() => onRemove(idx)}
            disabled={items.length <= minRows}
          >×</Button>
        </div>
      ))}
      <Button variant="secondary" size="sm" onClick={onAdd}>+ 加行</Button>
    </div>
  );
}
