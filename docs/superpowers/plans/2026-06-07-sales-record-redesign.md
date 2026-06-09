# 销售记录改造 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 `retail_orders` 为主体重构销售记录，对齐进货单的表格+详情弹窗+撤销模式。

**Architecture:** retail_orders 加 status 字段成为完整单头表，list/detail/cancel 三个端点围绕它工作，前端用表格+Modal 替代纯文本列表。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic / React + TypeScript + Tailwind

---

### Task 1: 数据库 Migration

**Files:**
- Create: `backend/alembic/versions/<hash>_add_status_to_retail_orders.py`
- Modify: `backend/app/models/retail_order.py`

- [ ] **Step 1: 在 model 中加字段**

```python
# backend/app/models/retail_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from app.database import Base


class RetailOrder(Base):
    __tablename__ = "retail_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

- [ ] **Step 2: 生成并写 migration**

```bash
cd backend && alembic revision --autogenerate -m "add status to retail_orders"
```

检查生成的 migration 文件，确认 upgrade/downgrade 正确。

- [ ] **Step 3: 运行 migration 验证**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/retail_order.py backend/alembic/versions/
git commit -m "feat: retail_orders 加 status/updated_at 字段"
```

---

### Task 2: SaleService 改造

**Files:**
- Modify: `backend/app/services/sale_service.py`
- Modify: `backend/app/repositories/retail_order_repo.py`
- Modify: `backend/app/schemas/sale.py`

- [ ] **Step 1: retail_order_repo 加 update 方法**

```python
# backend/app/repositories/retail_order_repo.py
from sqlalchemy.orm import Session
from app.models.retail_order import RetailOrder


class RetailOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, customer_id: int | None = None) -> RetailOrder:
        order = RetailOrder(customer_id=customer_id)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, order_id: int) -> RetailOrder | None:
        return self.db.query(RetailOrder).filter(RetailOrder.id == order_id).first()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
```

- [ ] **Step 2: 加出参 schema**

```python
# backend/app/schemas/sale.py — 追加在 SaleCreate 之后

class SaleOrderOut(BaseModel):
    id: int
    customer_id: int | None
    customer_name: str
    item_count: int
    total_amount: float
    paid: bool
    status: str
    items_summary: str
    created_at: str

    class Config:
        from_attributes = True


class SaleOrderDetail(SaleOrderOut):
    items: list[dict]
```

- [ ] **Step 3: 重写 list_sales（查 retail_orders 替代 transactions）**

```python
# 替换 sale_service.py 中的 list_sales 方法

def list_sales(self):
    from app.models.customer import Customer
    from app.models.stock_movement import StockMovement

    orders = self.db.query(RetailOrder).order_by(RetailOrder.created_at.desc()).all()
    if not orders:
        return []

    order_ids = [o.id for o in orders]
    customers = {c.id: c.name for c in self.db.query(Customer).all()}
    products = {p.id: p.name for p in self.db.query(Product).all()}

    movements = (
        self.db.query(StockMovement)
        .filter(
            StockMovement.retail_order_id.in_(order_ids),
            StockMovement.reason == "retail",
        )
        .all()
    )

    paid_ids = {
        t.retail_order_id
        for t in self.db.query(Transaction).filter(
            Transaction.retail_order_id.in_(order_ids),
            Transaction.category == "payment",
        ).all()
    }

    order_items: dict[int, list] = {}
    order_totals: dict[int, float] = {}
    for m in movements:
        order_items.setdefault(m.retail_order_id, []).append(m)
        order_totals[m.retail_order_id] = order_totals.get(m.retail_order_id, 0) + m.quantity * m.unit_price

    result = []
    for o in orders:
        items = order_items.get(o.id, [])
        parts = []
        for m in items[:2]:
            pname = products.get(m.product_id, "")
            parts.append(f"{pname}×{m.quantity}")
        summary = "、".join(parts)
        if len(items) > 2:
            summary += f" 等{len(items)}件"

        result.append({
            "id": o.id,
            "customer_id": o.customer_id,
            "customer_name": customers.get(o.customer_id, "散客") if o.customer_id else "散客",
            "item_count": len(items),
            "total_amount": order_totals.get(o.id, 0),
            "paid": o.id in paid_ids,
            "status": o.status,
            "items_summary": summary,
            "created_at": str(o.created_at),
        })

    return result
```

- [ ] **Step 4: 新增 get_sale_detail**

```python
# 追加在 list_sales 之后

def get_sale_detail(self, order_id: int):
    order = self.retail_repo.get_by_id(order_id)
    if not order:
        return None

    items = self.stock_repo.get_by_retail_order(order_id)
    products = {p.id: p.name for p in self.db.query(Product).all()}
    customers = {c.id: c.name for c in self.db.query(Customer).all()}

    paid = (
        self.db.query(Transaction).filter(
            Transaction.retail_order_id == order_id,
            Transaction.category == "payment",
        ).first()
        is not None
    )

    def item_dict(m):
        return {
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "quantity": m.quantity,
            "unit_price": m.unit_price,
        }

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer_name": customers.get(order.customer_id, "散客") if order.customer_id else "散客",
        "item_count": len(items),
        "total_amount": sum(m.quantity * m.unit_price for m in items),
        "paid": paid,
        "status": order.status,
        "items_summary": "",
        "items": [item_dict(m) for m in items],
        "created_at": str(order.created_at),
    }
```

- [ ] **Step 5: stock_movement_repo 加 get_by_retail_order**

```python
# backend/app/repositories/stock_movement_repo.py — StockMovementRepository 类中追加

def get_by_retail_order(self, retail_order_id: int) -> list:
    return self.db.query(StockMovement).filter(
        StockMovement.retail_order_id == retail_order_id,
        StockMovement.reason == "retail",
    ).all()
```

- [ ] **Step 6: 新增 cancel_sale**

```python
# 追加在 get_sale_detail 之后

def cancel_sale(self, order_id: int):
    order = self.retail_repo.get_by_id(order_id)
    if not order:
        raise ValueError("销售记录不存在")
    if order.status == "cancelled":
        raise ValueError("该销售已撤销")

    # 查原始出库记录
    original_items = self.stock_repo.get_by_retail_order(order_id)
    reverses = []
    reverse_total = 0.0
    for m in original_items:
        reverses.append({
            "product_id": m.product_id,
            "direction": "in",
            "reason": "cancel",
            "quantity": m.quantity,
            "unit_price": m.unit_price,
            "retail_order_id": order_id,
        })
        reverse_total += m.quantity * m.unit_price

    if reverses:
        self.stock_repo.bulk_create(reverses)

    # 反向冲抵账务
    original_txns = (
        self.db.query(Transaction)
        .filter(Transaction.retail_order_id == order_id)
        .all()
    )
    for t in original_txns:
        self.txn_repo.create(
            customer_id=order.customer_id,
            category=t.category,
            amount=-t.amount,
            retail_order_id=order_id,
        )

    self.retail_repo.update_status(order_id, "cancelled")
    self.db.commit()
    return {"id": order.id, "status": "cancelled"}
```

- [ ] **Step 7: 更新 create_sale 中的 import（移除顶部未使用的 Transaction import）**

检查 `sale_service.py` 顶部 import 已包含所需模型（RetailOrder 通过 retail_repo 引用，Transaction 和 Product 已 import）。

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/sale_service.py backend/app/repositories/retail_order_repo.py backend/app/repositories/stock_movement_repo.py backend/app/schemas/sale.py
git commit -m "feat: SaleService 以 retail_orders 为主体重构 list/detail/cancel"
```

---

### Task 3: API 路由更新

**Files:**
- Modify: `backend/app/api/sales.py`

- [ ] **Step 1: 改 list_sales、加 detail 和 cancel 端点**

将 `sales.py` 完全替换为：

```python
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas.sale import SaleCreate
from app.models.retail_order import RetailOrder
from app.models.customer import Customer

router = APIRouter(prefix="/api/sales", tags=["sales"])


def get_sale_service(db: Session = Depends(get_db)):
    return SaleService(db)


@router.post("", status_code=201)
def create_sale(data: SaleCreate, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.create_sale(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.list_sales()


@router.get("/{order_id}")
def get_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    detail = svc.get_sale_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_sale(order_id: int, svc: SaleService = Depends(get_sale_service)):
    try:
        return svc.cancel_sale(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
def export_sales(db: Session = Depends(get_db)):
    orders = db.query(RetailOrder).order_by(RetailOrder.created_at.desc()).all()
    customers = {c.id: c.name for c in db.query(Customer).all()}
    csv_lines = ["客户名称,金额,状态,时间"]
    for o in orders:
        cname = (customers.get(o.customer_id, "散客") if o.customer_id else "散客")
        csv_lines.append(f"{cname},,{o.status},{o.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales.csv"},
    )
```

> CSV 导出改为查 retail_orders，金额列留空（需 JOIN stock_movements 才能算，简单导出先不聚合）。

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/sales.py
git commit -m "feat: sales API 加 detail/cancel 端点，export 改为 retail_orders"
```

---

### Task 4: 前端类型 + API

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: types/index.ts 追加类型**

```typescript
// 追加在文件末尾
export interface RetailOrder {
  id: number;
  customer_id: number | null;
  customer_name: string;
  item_count: number;
  total_amount: number;
  paid: boolean;
  status: string;
  items_summary: string;
  created_at: string;
}

export interface RetailOrderDetail extends RetailOrder {
  items: RetailOrderDetailItem[];
}

export interface RetailOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}
```

- [ ] **Step 2: api.ts 扩展 saleApi**

```typescript
// 替换 saleApi 对象
export const saleApi = {
  create: (data: any) => api.post('/sales', data).then(r => r.data),
  list: () => api.get('/sales').then(r => r.data),
  get: (id: number) => api.get(`/sales/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/sales/${id}/cancel`).then(r => r.data),
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: 前端 RetailOrder 类型 + saleApi get/cancel"
```

---

### Task 5: SalesPage 前端改造

**Files:**
- Modify: `frontend/src/pages/SalesPage.tsx`

- [ ] **Step 1: 替换整个 SalesPage.tsx**

```tsx
import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { saleApi, customerApi } from '../services/api';
import { RetailOrder, RetailOrderDetail } from '../types';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

const STATUS_LABEL: Record<string, string> = { confirmed: '已收款', cancelled: '已撤销' };
const STATUS_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'default'> = { confirmed: 'success', cancelled: 'danger' };

export default function SalesPage() {
  const [customerId, setCustomerId] = useState<number | string>('');
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
  const [paid, setPaid] = useState(true);
  const [note, setNote] = useState('');
  const [sales, setSales] = useState<RetailOrder[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<RetailOrderDetail | null>(null);

  useEffect(() => {
    saleApi.list().then(setSales);
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
  }, []);

  const refreshSales = () => saleApi.list().then(setSales);

  const updateItem = (idx: number, field: keyof ItemRow, value: number | boolean) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };
  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);

  const onProductChange = async (idx: number, productId: number) => {
    updateItem(idx, 'product_id', productId);
    if (productId) {
      try {
        const { price } = await customerApi.resolvePrice(customerId ? Number(customerId) : 0, productId);
        updateItem(idx, 'unit_price', price);
      } catch {}
    }
  };
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息');
      return;
    }
    await saleApi.create({
      customer_id: customerId ? Number(customerId) : null,
      items,
      paid,
      note,
    });
    alert('销售成功');
    setCustomerId('');
    setItems([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
    setPaid(true);
    setNote('');
    refreshSales();
  };

  const handleCancel = async (orderId: number) => {
    if (!confirm('确定撤销此销售记录？（将反向冲抵库存和账务）')) return;
    await saleApi.cancel(orderId);
    refreshSales();
  };

  const openDetail = async (orderId: number) => {
    const d = await saleApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">直接销售（零售/自取）</h2>
        <Button variant="secondary" size="sm" onClick={() => window.open('/api/sales/export')}>导出 CSV</Button>
      </div>

      {/* 新建销售 */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div>
          <label className="text-sm font-medium text-gray-700">客户（留空为散客）</label>
          <CustomerSelect value={customerId} onChange={setCustomerId} priceTier="零售" />
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500">产品</label>
              <ProductSelect value={item.product_id} onChange={(v) => onProductChange(idx, v)} onlyInStock />
            </div>
            <div className="w-20">
              <label className="text-xs text-gray-500">数量</label>
              <Input type="number" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} />
            </div>
            <div className="w-24">
              <label className="text-xs text-gray-500">售价</label>
              <Input type="number" value={String(item.unit_price)} onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))} />
            </div>
            <label className="flex items-center gap-1 text-xs pb-2">
              <input type="checkbox" checked={item.is_promo} onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)} />
              赠送
            </label>
            <Button variant="danger" size="sm" onClick={() => removeRow(idx)} disabled={items.length <= 1}>×</Button>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={addRow}>+ 加行</Button>
          <span className="text-sm text-gray-500 ml-auto">合计: ¥{total.toFixed(2)}</span>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
          已收款
        </label>
        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleSubmit}>提交销售</Button>
      </div>

      {/* 销售记录 */}
      <h3 className="text-lg font-semibold mb-2">销售记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="px-4 py-2 text-left">客户</th>
              <th className="px-4 py-2 text-left">品项</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-right">日期</th>
              <th className="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(s.id)}>
                <td className="px-4 py-2 font-medium">{s.customer_name}</td>
                <td className="px-4 py-2 text-gray-500">{s.items_summary}</td>
                <td className="px-4 py-2 text-right">¥{s.total_amount.toFixed(2)}</td>
                <td className="px-4 py-2 text-center">
                  {s.status === 'confirmed' ? (
                    <Badge variant={s.paid ? 'success' : 'warning'}>{s.paid ? '已收款' : '未收款'}</Badge>
                  ) : (
                    <Badge variant="danger">已撤销</Badge>
                  )}
                </td>
                <td className="px-4 py-2 text-right text-gray-400">{new Date(s.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                  {s.status === 'confirmed' && (
                    <Button variant="danger" size="sm" onClick={() => handleCancel(s.id)}>撤销</Button>
                  )}
                </td>
              </tr>
            ))}
            {sales.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">暂无销售记录</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 详情弹窗 */}
      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title="销售详情">
        {detail && (
          <div className="space-y-3">
            <div className="flex gap-4 text-sm">
              <span>客户: {detail.customer_name}</span>
              <span>日期: {new Date(detail.created_at).toLocaleDateString()}</span>
              <span>
                状态:{' '}
                {detail.status === 'confirmed' ? (
                  <Badge variant={detail.paid ? 'success' : 'warning'}>{detail.paid ? '已收款' : '未收款'}</Badge>
                ) : (
                  <Badge variant="danger">已撤销</Badge>
                )}
              </span>
            </div>
            <table className="w-full text-sm border-t mt-2">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left">产品</th>
                  <th className="px-2 py-1 text-right">数量</th>
                  <th className="px-2 py-1 text-right">售价</th>
                  <th className="px-2 py-1 text-right">小计</th>
                </tr>
              </thead>
              <tbody>
                {detail.items.map((it, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">
                      {it.product_name}
                      {it.unit_price === 0 && <span className="ml-1 text-yellow-600 text-xs">赠</span>}
                    </td>
                    <td className="px-2 py-1 text-right">{it.quantity}</td>
                    <td className="px-2 py-1 text-right">¥{it.unit_price.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_price).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-right font-bold">合计: ¥{detail.total_amount.toFixed(2)}</div>
            {detail.status === 'confirmed' && (
              <div className="flex justify-end">
                <Button variant="danger" size="sm" onClick={() => { handleCancel(detail.id); setDetailOpen(false); }}>撤销此单</Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript 编译检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SalesPage.tsx
git commit -m "feat: SalesPage 表格+详情弹窗+撤销"
```

---

### Task 6: 验证

- [ ] **Step 1: 启动后端确认 API 正常**

```bash
cd backend && python -m app.main &
# 测试:
curl http://localhost:8000/api/sales  # 应返回零售单列表
```

- [ ] **Step 2: 启动前端确认页面正常**

```bash
cd frontend && npm run dev
```

浏览器确认：
- 销售记录以表格展示
- 点击行打开详情弹窗，显示品项明细
- 点击撤销后状态变为已撤销
- 新建销售后记录出现在列表中

- [ ] **Step 3: 确认撤销逻辑正确**

创建一笔销售 → 撤销 → 检查 stock_movements 有 cancel 记录 → 检查库存数量回补

- [ ] **Step 4: Commit（如有修正）**
