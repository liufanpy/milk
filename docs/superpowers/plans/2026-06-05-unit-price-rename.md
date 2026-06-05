# unit_price 改名 + 进货自动带价 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `stock_movements.unit_cost` 改名为 `unit_price`，并在前端进货页选产品时自动填入默认进价。

**Architecture:** 纯 rename + 最小功能追加。DB 改列名 → Model/Schema/Service 同步 → 前端类型和页面同步 → 进货页新增价格自动带出。

**Tech Stack:** SQLite, SQLAlchemy, FastAPI, React/TypeScript

---

### Task 1: 数据库列名改名

- [ ] **Step 1: 执行 SQLite ALTER TABLE**

```bash
sqlite3 backend/milk.db "ALTER TABLE stock_movements RENAME COLUMN unit_cost TO unit_price;"
```

- [ ] **Step 2: 验证列名已更改**

```bash
sqlite3 backend/milk.db "PRAGMA table_info(stock_movements);" | grep unit_price
```

Expected: 一行输出，包含 `unit_price` 和类型 `FLOAT`

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "db: rename stock_movements.unit_cost to unit_price"
```

### Task 2: 后端 Model 改名

**Files:**
- Modify: `backend/app/models/stock_movement.py:15`

- [ ] **Step 1: 修改列定义**

```python
# 改前
unit_cost = Column(Float, default=0.0)
# 改后
unit_price = Column(Float, default=0.0)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/stock_movement.py
git commit -m "refactor: rename unit_cost to unit_price in StockMovement model"
```

### Task 3: 后端 Schema 改名

**Files:**
- Modify: `backend/app/schemas/purchase.py:9`

- [ ] **Step 1: 修改 PurchaseItem.unit_cost → unit_price**

```python
# 改前
class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    shelf_id: int

# 改后
class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/purchase.py
git commit -m "refactor: rename unit_cost to unit_price in PurchaseItem schema"
```

### Task 4: 后端 Service 层改名

**Files:**
- Modify: `backend/app/services/purchase_service.py`（12 处）
- Modify: `backend/app/services/sale_service.py`（1 处）
- Modify: `backend/app/services/delivery_service.py`（3 处）
- Modify: `backend/app/services/return_service.py`（2 处）

- [ ] **Step 1: purchase_service.py — 全局替换 unit_cost → unit_price**

12 处替换，使用 Edit 的 `replace_all`:

| 行号 | 改前 | 改后 |
|---|---|---|
| 11 | `"进价", "unit_cost"` | `"进价", "unit_price"` |
| 40 | `item.unit_cost` | `item.unit_price` |
| 70 | `it["unit_cost"]` | `it["unit_price"]` |
| 87 | `item["unit_cost"]` | `item["unit_price"]` |
| 95 | `"unit_cost": cost` | `"unit_price": cost` |
| 135 | `"unit_cost": item.unit_cost` | `"unit_price": item.unit_price` |
| 138 | `item.unit_cost` | `item.unit_price` |
| 195 | `"unit_cost": i.unit_cost` | `"unit_price": i.unit_price` |
| 295 | `"unit_cost"` | `"unit_price"` |
| 306 | `"unit_cost": cost` | `"unit_price": cost` |

- [ ] **Step 2: sale_service.py:26 — 1 处替换**

```python
# 改前
"unit_cost": item.unit_price,
# 改后
"unit_price": item.unit_price,
```

- [ ] **Step 3: delivery_service.py — 3 处替换**

行号 45、110、132：`"unit_cost": item.unit_price` → `"unit_price": item.unit_price`

- [ ] **Step 4: return_service.py — 2 处替换**

行号 22、32：`"unit_cost": item.unit_price` → `"unit_price": item.unit_price`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/purchase_service.py backend/app/services/sale_service.py backend/app/services/delivery_service.py backend/app/services/return_service.py
git commit -m "refactor: rename unit_cost to unit_price in all services"
```

### Task 5: 前端类型改名

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 修改 PurchaseItem 和 PurchaseOrderDetailItem**

```typescript
// 改前 — PurchaseItem (line 111-116)
export interface PurchaseItem {
  product_id: number;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
}

// 改后
export interface PurchaseItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  shelf_id: number;
}

// 改前 — PurchaseOrderDetailItem (line 148-155)
export interface PurchaseOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
  shelf_name: string;
}

// 改后
export interface PurchaseOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
  shelf_id: number;
  shelf_name: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "refactor: rename unit_cost to unit_price in frontend types"
```

### Task 6: 前端进货页改名 + 自动带价

**Files:**
- Modify: `frontend/src/pages/PurchasesPage.tsx`

- [ ] **Step 1: 字段改名 unit_cost → unit_price**

全局替换所有 `unit_cost` → `unit_price`（约 6 处出现在对象字面量中）

- [ ] **Step 2: 标签 "进价" → "单价"**

```tsx
// line 140-141
// 改前
<label className="text-xs text-gray-500">进价</label>
// 改后
<label className="text-xs text-gray-500">单价</label>
```

- [ ] **Step 3: 加载完整产品列表用于查默认进价**

PurchasesPage 当前只加载了 `productNames` map。需要同时加载完整产品数据。

改前 (line 46-48):
```tsx
useEffect(() => {
  supplierApi.list().then(setSuppliers);
  shelfApi.list().then((data: any) => { setShelves(data); setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))); });
  productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
  purchaseApi.list().then(setOrders);
}, []);
```

改后:
```tsx
const [products, setProducts] = useState<any[]>([]);  // 新增 state

useEffect(() => {
  supplierApi.list().then(setSuppliers);
  shelfApi.list().then((data: any) => { setShelves(data); setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))); });
  productApi.list().then((data: any) => {
    setProducts(data);
    setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name])));
  });
  purchaseApi.list().then(setOrders);
}, []);
```

- [ ] **Step 4: 新增 onProductChange 自动填入默认进价**

在 `updateItem` 和 `addRow` 之后添加:

```tsx
const onProductChange = (idx: number, productId: number) => {
  updateItem(idx, 'product_id', productId);
  if (productId) {
    const product = products.find(p => p.id === productId);
    if (product?.default_purchase_price) {
      updateItem(idx, 'unit_price', product.default_purchase_price);
    }
  }
};
```

- [ ] **Step 5: ProductSelect onChange 改为调用 onProductChange**

```tsx
// 改前 (line 133)
<ProductSelect value={item.product_id} onChange={(v) => updateItem(idx, 'product_id', v)} />

// 改后
<ProductSelect value={item.product_id} onChange={(v) => onProductChange(idx, v)} />
```

- [ ] **Step 6: 合并详情弹窗中的 unit_cost → unit_price**

详情弹窗中 (line 235-236):
```tsx
// 改前
<td className="px-2 py-1 text-right">¥{it.unit_cost.toFixed(2)}</td>
<td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_cost).toFixed(2)}</td>

// 改后
<td className="px-2 py-1 text-right">¥{it.unit_price.toFixed(2)}</td>
<td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_price).toFixed(2)}</td>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/PurchasesPage.tsx
git commit -m "feat: auto-fill purchase price from product default + rename unit_cost to unit_price"
```

### Task 7: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend && uvicorn app.main:app --reload --port 8000 &
sleep 2
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend && npm run dev &
```

- [ ] **Step 3: 验证进货自动带价**

打开进货管理页 → 选产品 → 单价应自动填入 `product.default_purchase_price`，可手动修改

- [ ] **Step 4: 验证送货自动带价**

打开送货管理页 → 选客户+产品 → 售价应自动填入（按客户专属价 > 等级价 > 零售价优先级）

- [ ] **Step 5: 验证零售自动带价**

打开零售页 → 选产品 → 售价应自动填入默认零售价

- [ ] **Step 6: 验证数据库列名**

```bash
sqlite3 backend/milk.db "PRAGMA table_info(stock_movements);"
# 应显示 unit_price 而不是 unit_cost
```

- [ ] **Step 7: 验证数据写入正确**

创建一条进货单 → DB Browser 打开 stock_movements → 确认 unit_price 列有正确的进价值
