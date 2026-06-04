import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useShelves, useCreateShelf, useUpdateShelf, useDeleteShelf } from '../hooks/useShelves';
import { useCustomers } from '../hooks/useCustomers';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import CsvImportModal from '../components/business/CsvImportModal';
import { shelfApi } from '../services/api';
import type { Shelf } from '../types';

export default function ShelvesPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Shelf | null>(null);
  const [form, setForm] = useState<{ name: string; customer_id: number | '' }>({ name: '', customer_id: '' });

  const qc = useQueryClient();
  const [importOpen, setImportOpen] = useState(false);

  const { data: shelves = [], isLoading } = useShelves();
  const { data: customers = [] } = useCustomers();
  const createMutation = useCreateShelf();
  const updateMutation = useUpdateShelf();
  const deleteMutation = useDeleteShelf();

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', customer_id: '' });
    setModalOpen(true);
  };
  const openEdit = (s: Shelf) => {
    setEditing(s);
    setForm({ name: s.name, customer_id: s.customer_id ?? '' });
    setModalOpen(true);
  };

  const handleSubmit = () => {
    const payload = { name: form.name, customer_id: form.customer_id === '' ? null : Number(form.customer_id) };
    if (editing) {
      updateMutation.mutate({ id: editing.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
    setModalOpen(false);
  };

  const columns = [
    { key: 'name', title: '名称' },
    {
      key: 'customer_id', title: '所属客户',
      render: (s: Shelf) => {
        if (!s.customer_id) return <span className="text-gray-400">无</span>;
        const c = customers.find((c: any) => c.id === s.customer_id);
        return c?.name ?? `ID:${s.customer_id}`;
      },
    },
    {
      key: 'actions', title: '操作',
      render: (s: Shelf) => (
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(s)}>编辑</Button>
          <Button size="sm" variant="danger" onClick={() => { if (confirm('确定删除?')) deleteMutation.mutate(s.id); }}>删除</Button>
        </div>
      ),
    },
  ];

  const customerOptions = customers.map((c: any) => ({ value: c.id, label: c.name }));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">货架管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" onClick={() => window.open('/api/shelves/export')}>导出 CSV</Button>
          <Button onClick={openCreate}>+ 新增货架</Button>
        </div>
      </div>
      {isLoading ? <p className="text-gray-400">加载中...</p> : <Table columns={columns} data={shelves} rowKey={(s) => s.id} />}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? '编辑货架' : '新增货架'}>
        <div className="space-y-3">
          <Input label="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Select
            label="所属客户"
            options={[{ value: '', label: '通用(无客户)' }, ...customerOptions]}
            value={form.customer_id}
            onChange={(e) => setForm({ ...form, customer_id: e.target.value === '' ? '' : Number(e.target.value) })}
          />
          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={!form.name}>保存</Button>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入货架"
        onImport={(file) => shelfApi.importFile(file)}
        onConfirm={(rows) => shelfApi.confirmImport(rows)}
        onDone={() => qc.invalidateQueries({ queryKey: ['shelves'] })}
      />
    </div>
  );
}
