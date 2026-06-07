interface DetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface ItemDetailTableProps {
  items: DetailItem[];
  productNames?: Record<number, string>;
}

export function ItemDetailTable({ items, productNames }: ItemDetailTableProps) {
  const getName = (item: DetailItem) =>
    item.product_name || productNames?.[item.product_id] || `产品#${item.product_id}`;

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  return (
    <div>
      <table className="w-full text-sm border-t mt-2">
        <thead>
          <tr className="text-gray-500">
            <th className="px-2 py-1 text-left">产品</th>
            <th className="px-2 py-1 text-right">数量</th>
            <th className="px-2 py-1 text-right">单价</th>
            <th className="px-2 py-1 text-right">小计</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} className="border-t">
              <td className="px-2 py-1">{getName(it)}</td>
              <td className="px-2 py-1 text-right">{it.quantity}</td>
              <td className="px-2 py-1 text-right">¥{it.unit_price.toFixed(2)}</td>
              <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_price).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-right font-bold mt-2">合计: ¥{total.toFixed(2)}</div>
    </div>
  );
}
