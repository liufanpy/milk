# 库存流水 + 资金流水 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增库存流水和资金流水两个只读页面，支持筛选 + 连续余额，方便日常对账。

**Architecture:** 纯读查询，不改任何现有代码。后端两个新 API，前端两个新页面 + 路由 + 侧边栏。余额用 Python 循环算，LIMIT 500。

**Tech Stack:** Python/FastAPI/SQLAlchemy (后端), React/TypeScript/TanStack Query (前端)

---

### Task 1: 后端 — 库存流水 API

**Files:**
- Create: `backend/app/api/stock_ledger.py`

- [ ] **Step 1: 写 API**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.return_order import ReturnOrder
from app.models.wastage_order import WastageOrder
from app.models.delivery import Delivery
from app.models.subscription_order import SubscriptionOrder

router = APIRouter(prefix="/api/stock-ledger", tags=["stock-ledger"])


def _order_number_map(db: Session, movements: list) -> dict:
    """批量反查关联单号: movement.id → order_number"""
    ids_by_table: dict[str, set] = {}
    for m in movements:
        for fk, table in [
            ("purchase_order_id", "purchase_orders"),
            ("retail_order_id", "retail_orders"),
            ("return_order_id", "return_orders"),
            ("wastage_order_id", "wastage_orders"),
            ("delivery_id", "deliveries"),
            ("subscription_order_id", "subscription_orders"),
        ]:
            val = getattr(m, fk, None)
            if val:
                ids_by_table.setdefault(table, set()).add(val)

    models = {
        "purchase_orders": PurchaseOrder,
        "retail_orders": RetailOrder,
        "return_orders": ReturnOrder,
        "wastage_orders": WastageOrder,
        "deliveries": Delivery,
        "subscription_orders": SubscriptionOrder,
    }
    result: dict[int, str] = {}
    for table, ids in ids_by_table.items():
        model = models[table]
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for m in movements:
                fk = [k for k, v in [
                    ("purchase_order_id", "purchase_orders"),
                    ("retail_order_id", "retail_orders"),
                    ("return_order_id", "return_orders"),
                    ("wastage_order_id", "wastage_orders"),
                    ("delivery_id", "deliveries"),
                    ("subscription_order_id", "subscription_orders"),
                ] if v == table][0]
                if getattr(m, fk, None) == row.id:
                    result[m.id] = row.order_number or ""
    return result


@router.get("")
def list_stock_ledger(
    product_id: int | None = Query(None),
    direction: str | None = Query(None),
    reason: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StockMovement).order_by(StockMovement.created_at.asc())

    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if direction:
        q = q.filter(StockMovement.direction == direction)
    if reason:
        q = q.filter(StockMovement.reason == reason)

    movements = q.limit(500).all()
    if not movements:
        return []

    products = {p.id: p.name for p in db.query(Product).all()}
    order_numbers = _order_number_map(db, movements)

    # 按 product_id 独立计算连续余额
    balances: dict[int, int] = {}
    rows = []
    for m in movements:
        balances.setdefault(m.product_id, 0)
        if m.direction == "in":
            balances[m.product_id] += m.quantity
        else:
            balances[m.product_id] -= m.quantity

        rows.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "direction": m.direction,
            "quantity": m.quantity,
            "balance": balances[m.product_id],
            "reason": m.reason,
            "unit_price": m.unit_price or 0,
            "order_number": order_numbers.get(m.id, ""),
            "created_at": str(m.created_at),
        })

    return rows
```

- [ ] **Step 2: 注册路由**

```python
# backend/app/main.py 加一行
from app.api import stock_ledger
app.include_router(stock_ledger.router)
```

- [ ] **Step 3: 手动验证**

```bash
curl -s http://localhost:8000/api/stock-ledger | python3 -m json.tool | head -20
```

Expected: 返回 JSON 数组，每条有 `product_name`, `direction`, `quantity`, `balance`, `order_number`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/stock_ledger.py backend/app/main.py
git commit -m "feat: add stock ledger API with running balance"
```

---

### Task 2: 后端 — 资金流水 API

**Files:**
- Create: `backend/app/api/transaction_ledger.py`

- [ ] **Step 1: 写 API**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.purchase_order import PurchaseOrder
from app.models.retail_order import RetailOrder
from app.models.return_order import ReturnOrder
from app.models.delivery import Delivery
from app.models.subscription_order import SubscriptionOrder

router = APIRouter(prefix="/api/transaction-ledger", tags=["transaction-ledger"])

# 关联单号查询同 stock_ledger
def _order_number_map(db: Session, txns: list) -> dict:
    from app.models.purchase_order import PurchaseOrder
    from app.models.retail_order import RetailOrder
    from app.models.return_order import ReturnOrder
    from app.models.delivery import Delivery
    from app.models.subscription_order import SubscriptionOrder

    ids_by_table: dict[str, set] = {}
    for t in txns:
        for fk, table in [
            ("purchase_order_id", "purchase_orders"),
            ("retail_order_id", "retail_orders"),
            ("return_order_id", "return_orders"),
            ("delivery_id", "deliveries"),
            ("subscription_order_id", "subscription_orders"),
        ]:
            val = getattr(t, fk, None)
            if val:
                ids_by_table.setdefault(table, set()).add(val)

    models = {
        "purchase_orders": PurchaseOrder,
        "retail_orders": RetailOrder,
        "return_orders": ReturnOrder,
        "deliveries": Delivery,
        "subscription_orders": SubscriptionOrder,
    }
    result: dict[int, str] = {}
    for table, ids in ids_by_table.items():
        model = models[table]
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for t in txns:
                fk = [k for k, v in [
                    ("purchase_order_id", "purchase_orders"),
                    ("retail_order_id", "retail_orders"),
                    ("return_order_id", "return_orders"),
                    ("delivery_id", "deliveries"),
                    ("subscription_order_id", "subscription_orders"),
                ] if v == table][0]
                if getattr(t, fk, None) == row.id:
                    result[t.id] = row.order_number or ""
    return result


@router.get("")
def list_transaction_ledger(
    customer_id: int | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).order_by(Transaction.created_at.asc())

    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if category:
        q = q.filter(Transaction.category == category)

    txns = q.limit(500).all()
    if not txns:
        return []

    customers = {c.id: c.name for c in db.query(Customer).all()}
    suppliers = {s.id: s.name for s in db.query(Supplier).all()}
    order_numbers = _order_number_map(db, txns)

    # 按 customer_id 独立计算连续应收余额，供应商无余额
    balances: dict[int, float] = {}
    rows = []
    for t in txns:
        name = ""
        is_supplier = False
        if t.customer_id:
            name = customers.get(t.customer_id, "")
            balances.setdefault(t.customer_id, 0.0)
            if t.category in ("distribution", "retail", "subscription"):
                balances[t.customer_id] += t.amount
            elif t.category in ("payment", "refund"):
                balances[t.customer_id] -= t.amount
            bal = balances[t.customer_id]
        elif t.supplier_id:
            name = suppliers.get(t.supplier_id, "")
            is_supplier = True
            bal = None
        else:
            bal = None

        rows.append({
            "id": t.id,
            "customer_name": name,
            "category": t.category,
            "amount": t.amount,
            "balance": round(bal, 2) if bal is not None else None,
            "order_number": order_numbers.get(t.id, ""),
            "created_at": str(t.created_at),
        })

    return rows
```

- [ ] **Step 2: 注册路由**

```python
# backend/app/main.py 加一行
from app.api import transaction_ledger
app.include_router(transaction_ledger.router)
```

- [ ] **Step 3: 手动验证**

```bash
curl -s http://localhost:8000/api/transaction-ledger | python3 -m json.tool | head -20
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/transaction_ledger.py backend/app/main.py
git commit -m "feat: add transaction ledger API with running balance"
```

---

### Task 3: 前端 — 库存流水页

**Files:**
- Create: `frontend/src/pages/StockLedgerPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 加 API 方法**

```typescript
// frontend/src/services/api.ts 末尾加
export const ledgerApi = {
  stock: (params?: any) => api.get('/stock-ledger', { params }).then(r => r.data),
  transactions: (params?: any) => api.get('/transaction-ledger', { params }).then(r => r.data),
};
```

- [ ] **Step 2: 写页面**

```tsx
// frontend/src/pages/StockLedgerPage.tsx
import { useState, useEffect } from 'react';
import { OrderListTable } from '../components/business/OrderListTable';
import { ProductSelect } from '../components/business/ProductSelect';
import { ledgerApi } from '../services/api';

const DIR_OPTIONS = ['', 'in', 'out'];
const DIR_LABELS: Record<string, string> = { '': '全部', in: '入库', out: '出库' };
const REASON_OPTIONS = ['', 'purchase', 'retail', 'distribution', 'subscription', 'return', 'wastage', 'expired', 'damaged', 'self_consumed', 'cancel', 'exchange', 'promo', 'cogs'];

export default function StockLedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [productId, setProductId] = useState<number | string>('');
  const [direction, setDirection] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [productId, direction, reason]);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (productId) params.product_id = Number(productId);
      if (direction) params.direction = direction;
      if (reason) params.reason = reason;
      const data = await ledgerApi.stock(params);
      setRows(data);
    } finally { setLoading(false); }
  };

  const columns = [
    { key: 'created_at', title: '时间', render: (r: any) => r.created_at?.slice(0, 19).replace('T', ' ') },
    { key: 'product_name', title: '产品' },
    { key: 'direction', title: '方向', render: (r: any) => (
      <span className={r.direction === 'in' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
        {r.direction === 'in' ? '入库' : '出库'}
      </span>
    )},
    { key: 'quantity', title: '数量', render: (r: any) => <span className="font-medium">{r.quantity}</span> },
    { key: 'balance', title: '库存余额', render: (r: any) => <span className="font-bold">{r.balance}</span> },
    { key: 'reason', title: '原因' },
    { key: 'order_number', title: '关联单号' },
    { key: 'unit_price', title: '单价', render: (r: any) => r.unit_price ? `¥${r.unit_price.toFixed(2)}` : '' },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">库存流水</h2>
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="w-48">
          <ProductSelect value={productId} onChange={(v) => setProductId(v)} />
        </div>
        <select value={direction} onChange={(e) => setDirection(e.target.value)} className="border rounded px-3 py-2 text-sm">
          {DIR_OPTIONS.map(d => <option key={d} value={d}>{DIR_LABELS[d]}</option>)}
        </select>
        <select value={reason} onChange={(e) => setReason(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">全部原因</option>
          {REASON_OPTIONS.filter(r => r).map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <OrderListTable columns={columns} data={rows} rowKey={(r) => r.id} isLoading={loading} />
    </div>
  );
}
```

- [ ] **Step 3: 加路由**

```tsx
// frontend/src/App.tsx
import StockLedgerPage from './pages/StockLedgerPage';
// ...
<Route path="/stock-ledger" element={<StockLedgerPage />} />
```

- [ ] **Step 4: 加侧边栏**

```tsx
// frontend/src/components/Layout.tsx, 在 '日志' 之前加
{ to: '/stock-ledger', label: '库存流水' },
```

- [ ] **Step 5: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/StockLedgerPage.tsx frontend/src/App.tsx \
  frontend/src/components/Layout.tsx frontend/src/services/api.ts
git commit -m "feat: add stock ledger page"
```

---

### Task 4: 前端 — 资金流水页

**Files:**
- Create: `frontend/src/pages/TransactionLedgerPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: 写页面**

```tsx
// frontend/src/pages/TransactionLedgerPage.tsx
import { useState, useEffect } from 'react';
import { OrderListTable } from '../components/business/OrderListTable';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ledgerApi } from '../services/api';

const CAT_OPTIONS = ['', 'retail', 'distribution', 'subscription', 'payment', 'refund', 'purchase', 'wastage', 'cogs', 'promo'];

export default function TransactionLedgerPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [customerId, setCustomerId] = useState<number | string>('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [customerId, category]);

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (customerId) params.customer_id = Number(customerId);
      if (category) params.category = category;
      const data = await ledgerApi.transactions(params);
      setRows(data);
    } finally { setLoading(false); }
  };

  const isIncome = (r: any) =>
    ['retail', 'distribution', 'subscription'].includes(r.category);
  const isSupplier = (r: any) => !r.customer_name && r.category === 'purchase';

  const columns = [
    { key: 'created_at', title: '时间', render: (r: any) => r.created_at?.slice(0, 19).replace('T', ' ') },
    { key: 'customer_name', title: '客户/供应商', render: (r: any) => r.customer_name || '—' },
    { key: 'category', title: '类型' },
    { key: 'amount', title: '金额', render: (r: any) => (
      <span className={`font-medium ${r.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
        {r.amount > 0 ? '+' : ''}{r.amount.toFixed(2)}
      </span>
    )},
    { key: 'balance', title: '应收余额', render: (r: any) =>
      r.balance !== null ? <span className="font-bold">¥{r.balance.toFixed(2)}</span> : '—'
    },
    { key: 'order_number', title: '关联单号' },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">资金流水</h2>
      <div className="flex gap-3 mb-4">
        <div className="w-48">
          <CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="border rounded px-3 py-2 text-sm">
          <option value="">全部类别</option>
          {CAT_OPTIONS.filter(c => c).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <OrderListTable columns={columns} data={rows} rowKey={(r) => r.id} isLoading={loading} />
    </div>
  );
}
```

- [ ] **Step 2: 加路由 + 侧边栏**

```tsx
// App.tsx
import TransactionLedgerPage from './pages/TransactionLedgerPage';
<Route path="/transaction-ledger" element={<TransactionLedgerPage />} />

// Layout.tsx
{ to: '/transaction-ledger', label: '资金流水' },
```

- [ ] **Step 3: Typecheck + Commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/pages/TransactionLedgerPage.tsx frontend/src/App.tsx \
  frontend/src/components/Layout.tsx
git commit -m "feat: add transaction ledger page"
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

- [ ] **手动验证**

1. 进出几笔货 → 库存流水页能看到记录 + 余额变化
2. 记几笔账 → 资金流水页能看到记录 + 客户应收余额
3. 筛选产品/客户/方向 → 数据正确过滤
4. 侧边栏两个新入口正常
