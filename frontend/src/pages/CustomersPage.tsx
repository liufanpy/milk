import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  useCustomers, useCreateCustomer, useUpdateCustomer, useDeleteCustomer,
  useCustomerPrices, useAddCustomerPrice, useDeleteCustomerPrice,
} from '../hooks/useCustomers';
import { useProducts } from '../hooks/useProducts';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Modal } from '../components/ui/Modal';
import CsvImportModal from '../components/business/CsvImportModal';
import { customerApi } from '../services/api';
import { Table } from '../components/ui/Table';
import type { Customer, CreateCustomerData, ProductCustomerPrice } from '../types';

const priceTierOptions = [
  { value: '零售', label: '零售' },
  { value: '批发', label: '批发' },
];
const paymentOptions = [
  { value: '现金', label: '现金' },
  { value: '月结', label: '月结' },
  { value: '周结', label: '周结' },
  { value: '预存款', label: '预存款' },
];
const defaultForm: CreateCustomerData = { name: '', phone: '', address: '', price_tier: '批发', default_payment: '月结' };

export default function CustomersPage() {
  const qc = useQueryClient();
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState<CreateCustomerData>(defaultForm);

  const [priceCustomerId, setPriceCustomerId] = useState<number | null>(null);
  const [priceModalOpen, setPriceModalOpen] = useState(false);
  const [priceForm, setPriceForm] = useState({ product_id: '', price: '0' });

  const { data: customers = [], isLoading } = useCustomers(keyword);
  const { data: products = [] } = useProducts();
  const { data: customerPrices = [] } = useCustomerPrices(priceCustomerId);
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  const deleteMutation = useDeleteCustomer();
  const addPriceMutation = useAddCustomerPrice();
  const deletePriceMutation = useDeleteCustomerPrice();

  const openCreate = () => {
    setEditing(null);
    setForm(defaultForm);
    setModalOpen(true);
  };
  const openEdit = (c: Customer) => {
    setEditing(c);
    setForm({ name: c.name, phone: c.phone, address: c.address, price_tier: c.price_tier, default_payment: c.default_payment });
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

  const openPriceModal = (c: Customer) => {
    setPriceCustomerId(c.id);
    setPriceForm({ product_id: '', price: '0' });
    setPriceModalOpen(true);
  };

  const handleAddPrice = () => {
    if (!priceCustomerId || !priceForm.product_id) return;
    addPriceMutation.mutate({
      customerId: priceCustomerId,
      productId: Number(priceForm.product_id),
      price: Number(priceForm.price),
    });
    setPriceForm({ product_id: '', price: '0' });
  };

  const columns = [
    { key: 'name', title: '名称' },
    { key: 'phone', title: '电话' },
    { key: 'address', title: '地址' },
    { key: 'price_tier', title: '价格等级' },
    { key: 'default_payment', title: '默认结算' },
    {
      key: 'actions', title: '操作',
      render: (c: Customer) => (
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(c)}>编辑</Button>
          <Button size="sm" variant="secondary" onClick={() => openPriceModal(c)}>定价</Button>
          <Button size="sm" variant="danger" onClick={() => { if (confirm('确定删除?')) deleteMutation.mutate(c.id); }}>删除</Button>
        </div>
      ),
    },
  ];

  const productOptions = products.map((p: any) => ({ value: p.id, label: `${p.name} (${p.brand})` }));

  const productMap = Object.fromEntries(products.map((p: any) => [p.id, p]));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">客户管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" onClick={() => window.open('/api/customers/export')}>导出 CSV</Button>
          <Button onClick={openCreate}>+ 新增客户</Button>
        </div>
      </div>
      <Input placeholder="搜索客户..." value={keyword} onChange={(e) => setKeyword(e.target.value)} className="mb-4 max-w-sm" />
      {isLoading ? <p className="text-gray-400">加载中...</p> : <Table columns={columns} data={customers} rowKey={(c) => c.id} />}

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? '编辑客户' : '新增客户'}>
        <div className="space-y-3">
          <Input label="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="电话" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <Input label="地址" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <Select label="价格等级" options={priceTierOptions} value={form.price_tier} onChange={(e) => setForm({ ...form, price_tier: e.target.value })} />
          <Select label="默认结算" options={paymentOptions} value={form.default_payment} onChange={(e) => setForm({ ...form, default_payment: e.target.value })} />
          <div className="flex gap-2 pt-2">
            <Button onClick={handleSubmit} disabled={!form.name}>保存</Button>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>

      {/* Customer-specific pricing modal */}
      <Modal open={priceModalOpen} onClose={() => setPriceModalOpen(false)} title="客户定价管理">
        <div className="space-y-4">
          {customerPrices.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-600">已设置的价格</p>
              {customerPrices.map((cp: ProductCustomerPrice) => (
                <div key={cp.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-sm">{productMap[cp.product_id]?.name ?? `产品#${cp.product_id}`}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">¥{cp.price}</span>
                    <Button size="sm" variant="danger" onClick={() => deletePriceMutation.mutate({ customerId: priceCustomerId!, priceId: cp.id })}>删除</Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂未设置客户特定价格</p>
          )}
          <div className="border-t pt-3 space-y-3">
            <p className="text-sm font-medium text-gray-600">新增价格</p>
            <Select
              label="产品"
              options={productOptions}
              value={priceForm.product_id}
              onChange={(e) => setPriceForm({ ...priceForm, product_id: e.target.value })}
            />
            <Input label="价格" type="number" value={priceForm.price} onChange={(e) => setPriceForm({ ...priceForm, price: e.target.value })} />
            <Button onClick={handleAddPrice} disabled={!priceForm.product_id || !priceForm.price}>添加</Button>
          </div>
        </div>
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入客户"
        onImport={(file) => customerApi.importFile(file)}
        onConfirm={(rows) => customerApi.confirmImport(rows)}
        onDone={() => qc.invalidateQueries({ queryKey: ['customers'] })}
      />
    </div>
  );
}
