import type { ReactNode } from 'react';

interface Column<T> {
  key: string;
  title: string;
  render?: (item: T) => ReactNode;
}

interface OrderListTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
  emptyText?: string;
}

export function OrderListTable<T extends Record<string, any>>({
  columns,
  data,
  rowKey,
  onRowClick,
  isLoading = false,
  emptyText = '暂无数据',
}: OrderListTableProps<T>) {
  if (isLoading) {
    return <p className="text-center py-8 text-gray-400">加载中...</p>;
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 text-left font-medium">
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-gray-400">
                  {emptyText}
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr
                  key={rowKey(item)}
                  className="border-t hover:bg-gray-50 cursor-pointer"
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      {col.render ? col.render(item) : item[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
