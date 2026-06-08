# 移除零售/送货赠送功能 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零售和送货流程中移除 `is_promo` 赠送功能，赠品后续改走损耗单。

**Architecture:** 纯删代码——去掉 schema 字段、service 分支逻辑、前端复选框。不改 DB schema，不影响订阅扣瓶的独立 `is_promo`。

**Tech Stack:** Python/FastAPI/SQLAlchemy (后端), React/TypeScript (前端)

---

### Task 1: 后端 — 删 SaleItem.is_promo + SaleService promo 逻辑

**Files:**
- Modify: `backend/app/schemas/sale.py`
- Modify: `backend/app/services/sale_service.py`

- [ ] **Step 1: 删除 SaleItem.is_promo 字段**

```python
# backend/app/schemas/sale.py
from pydantic import BaseModel
from typing import List, Optional

class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    #   is_promo: bool = False  ← 删除这一行

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItem]
    paid: bool = True
    note: str = ""
```

- [ ] **Step 2: 删除 SaleService.create_sale 中 promo 分支**

`backend/app/services/sale_service.py` 中 `create_sale` 方法，把：

```python
for item in data.items:
    unit_price = 0.0 if item.is_promo else item.unit_price
    ...
    if not item.is_promo:
        movements.append({...})
```

改为：

```python
for item in data.items:
    movements.append({
        "product_id": item.product_id,
        "direction": "out",
        "reason": "retail",
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "retail_order_id": order.id,
    })
    total_amount += item.quantity * item.unit_price
```

同时删 `_confirm_items` 里的 promo cost 分支（`category="promo"` transaction），cogs 全部走 `category="cogs"`。

- [ ] **Step 3: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_sale.py -v
```

Expected: 2/2 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/sale.py backend/app/services/sale_service.py
git commit -m "refactor: remove is_promo from sale schema and service"
```

---

### Task 2: 后端 — 删 DeliveryItem.is_promo + DeliveryService promo 逻辑

**Files:**
- Modify: `backend/app/schemas/delivery.py`
- Modify: `backend/app/services/delivery_service.py`

- [ ] **Step 1: 删除 DeliveryItem.is_promo 字段**

```python
# backend/app/schemas/delivery.py
class DeliveryItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    #   is_promo: bool = False  ← 删除这一行
```

- [ ] **Step 2: 删除 DeliveryService 中 promo 逻辑**

删除 `create_delivery` 中：
- `unit_price = 0.0 if item.is_promo else item.unit_price`
- `if not item.is_promo:` 分支判断
- `category="promo"` transaction 创建逻辑

赠品行和正价行统一处理，cogs 走 `category="distribution"` 对应成本。

- [ ] **Step 3: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_delivery.py tests/test_exchange.py -v
```

Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/delivery.py backend/app/services/delivery_service.py
git commit -m "refactor: remove is_promo from delivery schema and service"
```

---

### Task 3: 前端 — 删 SalesPage 赠送勾选框

**Files:**
- Modify: `frontend/src/pages/SalesPage.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 删 SalesPage 中 is_promo**

`ItemRow` interface 删除 `is_promo: boolean` 字段。

所有 state 初始化 `{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }` → `{ product_id: 0, quantity: 1, unit_price: 0 }`。

`ItemRowEditor` children slot 删掉整段赠送复选框：

```tsx
// 删除以下代码：
{(item, idx) => (
  <label className="flex items-center gap-1 text-xs pb-2">
    <input
      type="checkbox"
      checked={item.is_promo}
      onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)}
    />
    赠送
  </label>
)}
```

ItemRowEditor 改为无 children：

```tsx
<ItemRowEditor
  items={items}
  onUpdate={updateItem}
  onProductChange={onProductChange}
  onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
  onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0 }])}
  onlyInStock
/>
```

- [ ] **Step 2: 删 types/index.ts 中的 is_promo**

```typescript
// SaleItem interface: 删除 is_promo?: boolean
// DeliveryItem interface: 删除 is_promo?: boolean
```

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SalesPage.tsx frontend/src/types/index.ts
git commit -m "refactor: remove is_promo from SalesPage"
```

---

### Task 4: 前端 — 删 DeliveriesPage 赠送勾选框

**Files:**
- Modify: `frontend/src/pages/DeliveriesPage.tsx`

- [ ] **Step 1: 删 DeliveriesPage 中所有 is_promo**

`DeliveryItem` interface 删除 `is_promo: boolean` 字段。

所有涉及 `is_promo: false` 的 state 初始化（items/returnItems/newItems）全部去掉该字段。

`ItemRowEditor` children slot 删掉赠送复选框（同 Task 3）。

换货弹窗中 `returnItems` / `newItems` 的初始化也去掉 `is_promo`。

- [ ] **Step 2: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DeliveriesPage.tsx
git commit -m "refactor: remove is_promo from DeliveriesPage"
```

---

### Task 5: 全量回归

- [ ] **后端测试**

```bash
cd backend && .venv/bin/python -m pytest tests/ -v
```

Expected: 35 passed

- [ ] **前端 typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Commit**

```bash
git commit -m "chore: 全量回归验证 — 移除 is_promo"
```

---

### 不动

- `SubscriptionDetailPage.tsx` — 订奶扣瓶的 `is_promo` 是独立功能，不动
- DB schema — `is_promo` 不是 DB 列，无需 migration
- StockMovement 表 — promo 只是 transaction category，不影响库存
