# Dashboard KPI 计算重设计 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard 销售额/出货量/应收账款口径修正，新增成本、退款、毛利指标，前端展示同步更新。

**Architecture:** 后端在 dashboard API 中新增 3 个聚合查询，前端 DashboardPage 新增 3 个卡片。

**Tech Stack:** Python/FastAPI/SQLAlchemy + React/TypeScript/TanStack Query

**前置状态：** 以下改动已在工作区但未提交：
- `backend/app/api/dashboard.py`：`today_sales` 已改为 `retail,subscription,store_sales`，`today_out` 已加 `source_type` 过滤
- `backend/app/repositories/transaction_repo.py`：AR 公式已移除 `subscription`
- `backend/app/api/transaction_ledger.py`：余额累加和显示已移除 `subscription`

---

### Task 1: 后端 — 新增今日退款额查询

**Files:**
- Modify: `backend/app/api/dashboard.py:33`（新增查询，在 today_payments 后插入）

- [ ] **Step 1: 在 dashboard.py 中添加 today_refund 查询**

```python
    today_refund = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category == "refund",
        func.date(Transaction.created_at) == today,
    ).scalar() or 0.0
```

插入位置：`today_payments` 查询后面（第 36 行之后）。
注意：refund 的 amount 是正值（退货 service 里退款是正数），取绝对值显示即可。实际上 SELECT SUM 会直接累加，无需取反。

- [ ] **Step 2: 在 return 字典中添加 today_refund 字段**

```python
    return {
        "today_sales": round(today_sales, 2),
        "today_payments": round(today_payments, 2),
        "today_refund": round(today_refund, 2),
        "today_out_quantity": today_out,
        "low_stock": low_stock,
        "top_ar": top_ar,
    }
```

- [ ] **Step 3: 验证 API 返回**

```bash
curl http://localhost:8000/api/dashboard | python3 -m json.tool | grep -E "sales|payments|refund|out"
```

预期输出包含 `today_refund` 字段。

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/dashboard.py
git commit -m "feat: dashboard 新增今日退款额指标"
```

---

### Task 2: 后端 — 新增今日成本查询

**Files:**
- Modify: `backend/app/api/dashboard.py`（新增 JOIN 查询）

- [ ] **Step 1: 在 dashboard.py 中 import Product 模型**

```python
from app.models.product import Product
```

插入位置：其他 import 行之后（第 9 行附近）。

- [ ] **Step 2: 添加 today_cost 查询**

在 `today_out` 查询之后插入：

```python
    today_cost = db.query(func.sum(StockMovement.quantity * Product.default_purchase_price)).filter(
        StockMovement.direction == "out",
        StockMovement.source_type.in_(["retail", "subscription", "store_sales"]),
        func.date(StockMovement.created_at) == today,
    ).join(Product, StockMovement.product_id == Product.id).scalar() or 0.0
```

原理：`stock_movements.quantity * products.default_purchase_price`，SQLAlchemy 会生成 JOIN 并在 SQL 层完成乘法+求和。

- [ ] **Step 3: 在 return 字典中添加 today_cost 和 today_gross_profit**

```python
    today_cost_val = round(today_cost, 2)
    today_gross_profit = round(today_sales - today_cost_val, 2)

    return {
        "today_sales": round(today_sales, 2),
        "today_payments": round(today_payments, 2),
        "today_refund": round(today_refund, 2),
        "today_cost": today_cost_val,
        "today_gross_profit": today_gross_profit,
        "today_out_quantity": today_out,
        "low_stock": low_stock,
        "top_ar": top_ar,
    }
```

- [ ] **Step 4: 验证 API 返回**

```bash
curl http://localhost:8000/api/dashboard | python3 -m json.tool | grep -E "cost|profit"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/dashboard.py
git commit -m "feat: dashboard 新增今日成本和毛利指标"
```

---

### Task 3: 前端 — Dashboard 页面新增退款、成本、毛利卡片

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx:22-35`

- [ ] **Step 1: 第一行新增退款和成本卡片**

将原来 3 列改为 4 列布局，在"今日收款"卡片后面插入退款和成本：

```tsx
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日销售额</div>
          <div className="text-2xl font-bold text-green-600">¥{data?.today_sales || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日收款</div>
          <div className="text-2xl font-bold text-blue-600">¥{data?.today_payments || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日退款</div>
          <div className="text-2xl font-bold text-orange-600">¥{data?.today_refund || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日成本</div>
          <div className="text-2xl font-bold text-gray-600">¥{data?.today_cost || 0}</div>
        </div>
      </div>
```

改动点：
- `grid-cols-3` → `grid-cols-4`
- "今日零售" → "今日销售额"
- 新增退款（橙色）、成本（灰色）卡片
- "今出库"卡片保留，挪到第二行

- [ ] **Step 2: 第二行新增毛利卡片**

在出库卡旁边增加毛利：

```tsx
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日出库</div>
          <div className="text-2xl font-bold">{data?.today_out_quantity || 0} 件</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">今日毛利</div>
          <div className={`text-2xl font-bold ${(data?.today_gross_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ¥{data?.today_gross_profit || 0}
          </div>
        </div>
      </div>
```

- [ ] **Step 3: 确认前端编译通过**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: dashboard 前端展示新增退款/成本/毛利指标"
```

---

### Task 4: 验证应收账款公式

**Files:**
- Verify: `backend/app/repositories/transaction_repo.py:27-33`
- Verify: `backend/app/repositories/transaction_repo.py:41-46`
- Verify: `backend/app/api/transaction_ledger.py:94,98`

- [ ] **Step 1: 确认 subscription 已从所有 AR 公式中移除**

```bash
grep "subscription" backend/app/repositories/transaction_repo.py | grep -v "import"
grep "subscription" backend/app/api/transaction_ledger.py | grep -v "import\|SubscriptionOrder"
```

预期无输出（或仅有 import 行）。

- [ ] **Step 2: 确认 get_ar_by_customer 公式正确**

```python
# 应包含: distribution(+), retail(+) 
# 应排除: subscription
# 应包含: payment(-), refund(-)
```

- [ ] **Step 3: Commit（如有残留改动）**

```bash
# 如果之前未提交
git add backend/app/repositories/transaction_repo.py backend/app/api/transaction_ledger.py
git commit -m "fix: AR 公式移除 subscription 预付款"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 创建测试数据验证 dashboard**

```bash
# 创建一笔零售
curl -X POST http://localhost:8000/api/sales -H 'Content-Type: application/json' \
  -d '{"customer_id":1,"items":[{"product_id":1,"quantity":3,"unit_price":6}],"paid":true}'

# 创建一笔退货
curl -X POST http://localhost:8000/api/returns -H 'Content-Type: application/json' \
  -d '{"customer_id":1,"items":[{"product_id":1,"quantity":1,"unit_price":6}],"note":"测试"}'

# 查看 dashboard
curl http://localhost:8000/api/dashboard | python3 -m json.tool
```

- [ ] **Step 2: 验证各字段有意义**

检查：
- `today_sales` >= 0
- `today_cost` > 0（因为卖了多少有进价）
- `today_gross_profit` = sales - cost
- `today_refund` >= 0
- `today_out_quantity` > 0 且不含非销售出库

- [ ] **Step 3: 打开前端页面**

http://localhost:5173 → 确认 6 个卡片都正常显示，数字合理。

- [ ] **Step 4: Commit（如有修正）**

```bash
git add .
git commit -m "test: dashboard KPI 端到端验证通过"
```
