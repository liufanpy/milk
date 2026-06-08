# 统一单号 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为全部 6 种单据统一 14 位单号格式 `XXYYYYMMDDNNNN`，同时删除退货单无用的来源关联字段。

**Architecture:** 每张表新加 `order_number VARCHAR(20) UNIQUE INDEX`，每个 Service 加 `_next_order_number()` 方法。前端列表 `#id` 列统一换 `单号`。

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (后端), React/TypeScript (前端)

---

### Task 1: Migration + 模型层（全部 6 表）

**Files:**
- Modify: `backend/app/models/return_order.py`
- Modify: `backend/app/models/retail_order.py`
- Modify: `backend/app/models/wastage_order.py`
- Modify: `backend/app/models/delivery.py`
- Modify: `backend/app/models/subscription_order.py`
- Create: `backend/alembic/versions/add_order_numbers.py` (autogenerate)

- [ ] **Step 1: 改 ReturnOrder 模型**

删 `source_type` + `source_order_id`，加 `order_number`：

```python
# backend/app/models/return_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class ReturnOrder(Base):
    __tablename__ = "return_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    note = Column(String(500), default="")
    status = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

- [ ] **Step 2: 其余 4 模型各加 order_number**

每个模型在 `id` 之后加一行：

```python
order_number = Column(String(20), nullable=True, unique=True, index=True)
```

涉及文件：
- `backend/app/models/retail_order.py`
- `backend/app/models/wastage_order.py`
- `backend/app/models/delivery.py`
- `backend/app/models/subscription_order.py`

- [ ] **Step 3: 生成并清理 migration**

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "add order_number to all order tables"
```

清理 migration，只保留本任务需要的 DDL（删 return_orders 的 source 列 + 各表加 order_number）。

- [ ] **Step 4: 运行 migration**

```bash
cd backend && .venv/bin/alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/return_order.py backend/app/models/retail_order.py \
  backend/app/models/wastage_order.py backend/app/models/delivery.py \
  backend/app/models/subscription_order.py \
  backend/alembic/versions/add_order_numbers.py
git commit -m "feat: add unified order_number to all order models, remove return source fields"
```

---

### Task 2: PurchaseService — 单号格式升级

**Files:**
- Modify: `backend/app/services/purchase_service.py`

- [ ] **Step 1: 改 `_next_order_number` 格式**

`PO-YYYYMMDD-NNN` → `POYYYYMMDDNNNN`，去掉分隔符、3 位改 4 位：

```python
def _next_order_number(self) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"PO{today}"
    last = (
        self.db.query(PurchaseOrder)
        .filter(PurchaseOrder.order_number.like(f"{prefix}%"))
        .order_by(PurchaseOrder.id.desc())
        .first()
    )
    if last and len(last.order_number) == 14:
        seq = int(last.order_number[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"
```

> `len(last.order_number) == 14` 确保旧格式 `PO-20260608-001`（15位）不会被拿来拼新序号。

- [ ] **Step 2: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_purchase.py -v
```

Expected: 8 passed

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/purchase_service.py
git commit -m "feat: upgrade purchase order_number to 14-digit format"
```

---

### Task 3: RetailOrder — 加单号

**Files:**
- Modify: `backend/app/services/sale_service.py`
- Modify: `backend/app/repositories/retail_order_repo.py`（或直接在 service 里查）

- [ ] **Step 1: SaleService 加 `_next_order_number` + create 调用**

```python
def _next_order_number(self) -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"RO{today}"
    last = (
        self.db.query(RetailOrder)
        .filter(RetailOrder.order_number.like(f"{prefix}%"))
        .order_by(RetailOrder.id.desc())
        .first()
    )
    if last and last.order_number and len(last.order_number) == 14:
        seq = int(last.order_number[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"
```

`create_sale` 中 `retail_order = self.retail_repo.create(...)` 之后加：

```python
retail_order.order_number = self._next_order_number()
```

`list_sales` 每个订单加 `"order_number": o.order_number`。

`get_sale_detail` 返回加 `"order_number": order.order_number`。

- [ ] **Step 2: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_sale.py -v
```

Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/sale_service.py
git commit -m "feat: add order_number to retail orders"
```

---

### Task 4: ReturnOrder — 删 source + 加单号

**Files:**
- Modify: `backend/app/schemas/return_schema.py`
- Modify: `backend/app/services/return_service.py`

- [ ] **Step 1: Schema 删 source**

```python
# backend/app/schemas/return_schema.py
class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_wasted: bool = False


class ReturnCreate(BaseModel):
    customer_id: int
    items: List[ReturnItem]
    note: str = ""
```

删除 `source_type` + `source_order_id` 字段。

- [ ] **Step 2: ReturnService 加单号 + 删 source**

加 `_next_order_number`（前缀 `RT`，查 `ReturnOrder` 表）。

`create_return`:
- 删 `source_type`、`source_order_id` 参数
- 创建 order 后加 `order.order_number = self._next_order_number()`

`list_returns`:
- 每个订单加 `"order_number": o.order_number`
- 删 `"source_type"`、`"source_order_id"` 返回

`get_return_detail`:
- 加 `"order_number": order.order_number`
- 删 `"source_type"`、`"source_order_id"` 返回

- [ ] **Step 3: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_return.py -v
```

Expected: 7 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/return_schema.py backend/app/services/return_service.py
git commit -m "feat: add order_number to returns, remove source tracking"
```

---

### Task 5: WastageOrder — 加单号

**Files:**
- Modify: `backend/app/services/wastage_service.py`

- [ ] **Step 1: 加单号生成 + create/list/detail**

`_next_order_number` 前缀 `WO`，查 `WastageOrder` 表。`create_wastage` 中写入，`list_wastage` 和 `get_wastage_detail` 中返回。

- [ ] **Step 2: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_wastage.py -v
```

Expected: 6 passed

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/wastage_service.py
git commit -m "feat: add order_number to wastage orders"
```

---

### Task 6: Delivery — 加单号

**Files:**
- Modify: `backend/app/services/delivery_service.py`

- [ ] **Step 1: 加单号生成 + create/list/detail**

`_next_order_number` 前缀 `DO`，查 `Delivery` 表。`create_delivery` 中写入，`list_with_amounts` 和 `get_delivery_detail` 中返回。

- [ ] **Step 2: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/test_delivery.py tests/test_exchange.py -v
```

Expected: 6 passed

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/delivery_service.py
git commit -m "feat: add order_number to deliveries"
```

---

### Task 7: SubscriptionOrder — 加单号

**Files:**
- Modify: `backend/app/services/subscription_service.py`

- [ ] **Step 1: 加单号生成 + create/list/detail**

`_next_order_number` 前缀 `SO`，查 `SubscriptionOrder` 表。创建和列表返回中加入 `order_number`。

- [ ] **Step 2: 运行测试**

```bash
cd backend && .venv/bin/python -m pytest tests/ -k "subscription" -v 2>&1 || echo "no subscription tests, skip"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/subscription_service.py
git commit -m "feat: add order_number to subscription orders"
```

---

### Task 8: 前端 — 6 页面列表列 + 退货删来源

**Files:**
- Modify: `frontend/src/pages/PurchasesPage.tsx`
- Modify: `frontend/src/pages/SalesPage.tsx`
- Modify: `frontend/src/pages/ReturnsPage.tsx`
- Modify: `frontend/src/pages/WastagePage.tsx`
- Modify: `frontend/src/pages/DeliveriesPage.tsx`
- Modify: `frontend/src/pages/SubscriptionsPage.tsx`

- [ ] **Step 1: 各页面列表列改单号**

每个页面的 columns 第一列从 `#id` 改为 `单号`，渲染 `order_number || #id`：

```tsx
{ key: 'order_number', title: '单号', render: (r: any) => r.order_number || `#${r.id}` },
```

6 个页面各改一处。

- [ ] **Step 2: 退货页删来源关联**

`ReturnsPage.tsx` 删除：
- `source_type` + `source_order_id` state
- 来源类型下拉 + 来源单号输入框的整个 `<div className="grid grid-cols-2 gap-3">` block
- `create` 调用中的 `source_type`、`source_order_id` 参数

- [ ] **Step 3: 详情弹窗 headerInfo 删来源显示**

`ReturnsPage.tsx` 的 `OrderDetailModal` headerInfo 中删除来源显示行。

- [ ] **Step 4: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PurchasesPage.tsx frontend/src/pages/SalesPage.tsx \
  frontend/src/pages/ReturnsPage.tsx frontend/src/pages/WastagePage.tsx \
  frontend/src/pages/DeliveriesPage.tsx frontend/src/pages/SubscriptionsPage.tsx
git commit -m "feat: show unified order_number in all list views, remove return source fields"
```

---

### Task 9: 全量回归

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

- [ ] **手动验证**

1. 各页新建一单 → 列表第一列显示新格式单号
2. 旧数据（无单号）→ 回退显示 `#id`
3. 退货新建 → 无来源选择 → 创建成功
4. 进货新建 → 单号格式 `PO202606080001`

- [ ] **Commit**

```bash
git commit -m "chore: 全量回归 — 统一单号"
```
