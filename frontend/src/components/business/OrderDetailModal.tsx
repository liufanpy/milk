import type { ReactNode } from 'react';
import { Modal } from '../ui/Modal';
import { StatusBadge } from '../ui/StatusBadge';
import { ItemDetailTable } from './ItemDetailTable';

interface StatusConfig {
  [status: string]: {
    label: string;
    variant: 'success' | 'warning' | 'danger' | 'default';
  };
}

interface DetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface OrderDetailModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  headerInfo: ReactNode;
  items: DetailItem[];
  status?: string;
  statusConfig?: StatusConfig;
  children?: ReactNode;   // 底部操作按钮
}

export function OrderDetailModal({
  open,
  onClose,
  title,
  headerInfo,
  items,
  status,
  statusConfig,
  children,
}: OrderDetailModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 text-sm">{headerInfo}</div>
          {status && statusConfig && (
            <StatusBadge status={status} config={statusConfig} />
          )}
        </div>
        <ItemDetailTable items={items} />
        {children && (
          <div className="flex gap-2 pt-2 border-t">{children}</div>
        )}
      </div>
    </Modal>
  );
}
