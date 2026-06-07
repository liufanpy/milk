import { ReactNode } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

interface OrderFormModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: () => void;
  isPending?: boolean;
  submitLabel?: string;
  children: ReactNode;
}

export function OrderFormModal({
  open,
  onClose,
  title,
  onSubmit,
  isPending = false,
  submitLabel = '提交',
  children,
}: OrderFormModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-4">
        {children}
        <div className="flex gap-2 pt-2 border-t">
          <Button onClick={onSubmit} disabled={isPending}>{submitLabel}</Button>
          <Button variant="secondary" onClick={onClose}>取消</Button>
        </div>
      </div>
    </Modal>
  );
}
