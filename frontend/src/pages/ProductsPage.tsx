import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useProducts, useCreateProduct, useUpdateProduct, useDeleteProduct } from '../hooks/useProducts';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import CsvImportModal from '../components/business/CsvImportModal';
import { productApi } from '../services/api';
import type { Product, CreateProductData } from '../types';

export default function ProductsPage() {
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<CreateProductData>({
    name: '', brand: '', category: '', unit: '箱', spec: '', default_purchase_price: 0, default_retail_price: 0, default_wholesale_price: 0, shelf_life_days: 0,
  });

  const qc = useQueryClient();
  const [importOpen, setImportOpen] = useState(false);

  const { data: products = [], isLoading } = useProducts(keyword);
  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct();
  const deleteMutation = useDeleteProduct();

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', brand: '', category: '', unit: '箱', spec: '', default_purchase_price: 0, default_retail_price: 0, default_wholesale_price: 0, shelf_life_days: 0 });
    setModalOpen(true);
  };
  const openEdit = (p: Product) => {
    setEditing(p);
    setForm({
      name: p.name, brand: p.brand, category: p.category, unit: p.unit, spec: p.spec,
      default_purchase_price: p.default_purchase_price,
      default_retail_price: p.default_retail_price, default_wholesale_price: p.default_wholesale_price, shelf_life_days: p.shelf_life_days,
    });
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
    { key: 'brand', title: '品牌' },
    { key: 'category', title: '分类' },
    { key: 'spec', title: '规格' },
    { key: 'default_purchase_price', title: '默认进货价', render: (p: Product) => `¥${p.default_purchase_price ?? 0}` },
    { key: 'unit', title: '单位' },
    { key: 'default_retail_price', title: '零售默认价', render: (p: Product) => `¥${p.default_retail_price}` },
    { key: 'default_wholesale_price', title: '批发默认价', render: (p: Product) => `¥${p.default_wholesale_price}` },
    {
      key: 'actions', title: '操作',
      render: (p: Product) => (
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>编辑</Button>
          <Button size="sm" variant="danger" onClick={() => { if (confirm('确定删除?')) deleteMutation.mutate(p.id); }}>删除</Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">产品管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" onClick={() => window.open('/api/products/export')}>导出 CSV</Button>
          <Button onClick={openCreate}>+ 新增产品</Button>
        </div>
      </div>
      <Input placeholder="搜索产品..." value={keyword} onChange={(e) => setKeyword(e.target.value)} className="mb-4 max-w-sm" />
      {isLoading ? <p className="text-gray-400">加载中...</p> : <Table columns={columns} data={products} rowKey={(p) => p.id} />}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? '编辑产品' : '新增产品'}>
        <div className="space-y-3">
          <Input label="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="品牌" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
          <Input label="分类" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          <Input label="规格" value={form.spec || ''} onChange={(e) => setForm({ ...form, spec: e.target.value })} />
          <Input label="单位" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          <Input label="默认进货价" type="number" value={String(form.default_purchase_price ?? 0)} onChange={(e) => setForm({ ...form, default_purchase_price: Number(e.target.value) })} />
          <Input label="零售默认价" type="number" value={String(form.default_retail_price)} onChange={(e) => setForm({ ...form, default_retail_price: Number(e.target.value) })} />
          <Input label="批发默认价" type="number" value={String(form.default_wholesale_price)} onChange={(e) => setForm({ ...form, default_wholesale_price: Number(e.target.value) })} />
          <Input label="保质期(天)" type="number" value={String(form.shelf_life_days)} onChange={(e) => setForm({ ...form, shelf_life_days: Number(e.target.value) })} />
          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={!form.name}>保存</Button>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入产品"
        onImport={(file) => productApi.importFile(file)}
        onConfirm={(rows) => productApi.confirmImport(rows)}
        onDone={() => qc.invalidateQueries({ queryKey: ['products'] })}
      />
    </div>
  );
}
