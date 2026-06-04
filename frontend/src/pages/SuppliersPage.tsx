import { useState } from 'react';
import { useSuppliers, useCreateSupplier, useUpdateSupplier, useDeleteSupplier } from '../hooks/useSuppliers';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import type { Supplier } from '../types';

const defaultForm = { name: '', contact: '', phone: '' };

export default function SuppliersPage() {
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [form, setForm] = useState(defaultForm);

  const { data: suppliers = [], isLoading } = useSuppliers(keyword);
  const createMutation = useCreateSupplier();
  const updateMutation = useUpdateSupplier();
  const deleteMutation = useDeleteSupplier();

  const openCreate = () => {
    setEditing(null);
    setForm(defaultForm);
    setModalOpen(true);
  };
  const openEdit = (s: Supplier) => {
    setEditing(s);
    setForm({ name: s.name, contact: s.contact, phone: s.phone });
    setModalOpen(true);
  };

  const handleSubmit = () => {
    if (editing) {
      updateMutation.mutate({ id: editing.id, data: form });
    } else {
      createMutation.mutate(form);
    }
    setModalOpen(false);
  };

  const columns = [
    { key: 'name', title: '名称' },
    { key: 'contact', title: '联系人' },
    { key: 'phone', title: '电话' },
    {
      key: 'actions', title: '操作',
      render: (s: Supplier) => (
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(s)}>编辑</Button>
          <Button size="sm" variant="danger" onClick={() => { if (confirm('确定删除?')) deleteMutation.mutate(s.id); }}>删除</Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">供应商管理</h2>
        <Button onClick={openCreate}>+ 新增供应商</Button>
      </div>
      <Input placeholder="搜索供应商..." value={keyword} onChange={(e) => setKeyword(e.target.value)} className="mb-4 max-w-sm" />
      {isLoading ? <p className="text-gray-400">加载中...</p> : <Table columns={columns} data={suppliers} rowKey={(s) => s.id} />}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? '编辑供应商' : '新增供应商'}>
        <div className="space-y-3">
          <Input label="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="联系人" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} />
          <Input label="电话" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={!form.name}>保存</Button>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
