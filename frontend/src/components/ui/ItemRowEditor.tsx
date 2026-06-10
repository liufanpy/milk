import type { ReactNode } from 'react';
import { Button } from './Button';
import { ProductSelect } from '../business/ProductSelect';

const inputCls = 'border border-gray-300 rounded-lg px-2 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 [-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none';

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
        <div key={idx} className="flex gap-1.5 items-end">
          <div className="flex-1 min-w-0">
            <ProductSelect
              value={item.product_id}
              onChange={(v) => onProductChange(idx, v)}
              onlyInStock={onlyInStock}
            />
          </div>
          <input
            type="number"
            className={inputCls}
            style={{ width: '5ch' }}
            value={String(item.quantity)}
            onChange={(e) => onUpdate(idx, 'quantity' as keyof T, Number(e.target.value))}
          />
          <input
            type="number"
            className={inputCls}
            style={{ width: '7ch' }}
            value={String(item.unit_price)}
            onChange={(e) => onUpdate(idx, 'unit_price' as keyof T, Number(e.target.value))}
          />
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
