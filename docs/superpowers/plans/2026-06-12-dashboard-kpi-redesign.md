# Dashboard KPI 计算重设计 + 时间筛选 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard 销售额/出货量口径修正、新增成本和毛利、支持时间筛选（今日/本周/本月/最近30天/自定义），前端展示同步更新。

**Architecture:** 后端 `/api/dashboard` 接受 `date_from`/`date_to` 参数，所有指标按时间范围查询。前端新增时间筛选组件，点击区间后重新请求。

**Tech Stack:** Python/FastAPI/SQLAlchemy + React/TypeScript/TanStack Query

**前置状态：** 以下改动已在工作区但未提交：
- `backend/app/api/dashboard.py`：`today_sales` 已改为 `retail,subscription,store_sales`，`today_out` 已加 `source_type` 过滤
- `backend/app/repositories/transaction_repo.py`：AR 公式已移除 `subscription`
- `backend/app/api/transaction_ledger.py`：余额累加和显示已移除 `subscription`

---

### Task 1: 后端 — Dashboard API 支持时间范围参数

**Files:**
- Modify: `backend/app/api/dashboard.py`（重写 `get_dashboard` 函数）

- [ ] **Step 1: 接受 date_from / date_to 查询参数**

```python
@router.get("/api/dashboard")
def get_dashboard(
    date_from: str = Query(..., description="开始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="结束日期 YYYY-MM-DD，闭区间"),
    db: Session = Depends(get_db),
):
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
```

- [ ] **Step 2: 改造 5 个查询，全部使用 d_from / d_to**

注意：`date_to` 是闭区间，SQL 中 `< d_to + 1` 实现闭区间包含当天。

```python
    sales_conditions = Transaction.category.in_(["retail", "subscription", "store_sales"])
    out_conditions = [
        StockMovement.direction == "out",
        StockMovement.source_type.in_(["retail", "subscription", "store_sales"]),
    ]
    date_range_txn = [func.date(Transaction.created_at) >= d_from, func.date(Transaction.created_at) <= d_to]
    date_range_sm  = [func.date(StockMovement.created_at) >= d_from, func.date(StockMovement.created_at) <= d_to]

    total_sales = db.query(func.sum(Transaction.amount)).filter(sales_conditions, *date_range_txn).scalar() or 0.0

    total_payments = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category == "payment", *date_range_txn
    ).scalar() or 0.0

    total_out = db.query(func.sum(StockMovement.quantity)).filter(*out_conditions, *date_range_sm).scalar() or 0

    total_cost = db.query(func.sum(StockMovement.quantity * Product.default_purchase_price)).filter(
        *out_conditions, *date_range_sm
    ).join(Product, StockMovement.product_id == Product.id).scalar() or 0.0
```

- [ ] **Step 3: 改造低库存和应收（不受时间范围影响，保持全量）**

```python
    stock_repo = StockMovementRepository(db)
    inventory_rows = stock_repo.get_inventory()
    low_stock = [
        {"product_id": r.product_id, "stock": r.stock}
        for r in inventory_rows if 0 < r.stock < 10
    ]

    txn_repo = TransactionRepository(db)
    ar_rows = txn_repo.get_receivables()
    top_ar = sorted(
        [{"customer_id": r.customer_id, "ar_balance": round(r.ar_balance, 2)} for r in ar_rows],
        key=lambda x: abs(x["ar_balance"]), reverse=True,
    )[:5]
```

- [ ] **Step 4: 返回字典**

```python
    cost_val = round(total_cost, 2)
    return {
        "total_sales": round(total_sales, 2),
        "total_payments": round(total_payments, 2),
        "total_cost": cost_val,
        "total_gross_profit": round(total_sales - cost_val, 2),
        "total_out_quantity": total_out,
        "low_stock": low_stock,
        "top_ar": top_ar,
    }
```

- [ ] **Step 5: 验证 API**

```bash
curl "http://localhost:8000/api/dashboard?date_from=2026-06-12&date_to=2026-06-12" | python3 -m json.tool
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/dashboard.py
git commit -m "feat: dashboard API 支持时间范围参数 + 新增成本和毛利"
```

---

### Task 2: 后端 — 添加 Product import

**Files:**
- Modify: `backend/app/api/dashboard.py` 顶部

如果 Task 1 还没 import `Product`，补充：

```python
from app.models.product import Product
```

- [ ] **Step 1: Commit**

```bash
git add backend/app/api/dashboard.py
git commit -m "fix: dashboard 补充 Product import"
```

---

### Task 3: 前端 — 时间筛选组件 + Dashboard 页面重构

**Files:**
- Create: `frontend/src/components/business/TimeRangeFilter.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 创建 TimeRangeFilter 组件**

```tsx
import { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

type RangeKey = 'today' | 'week' | 'month' | '30d' | 'custom';

interface DateRange {
  date_from: string;
  date_to: string;
}

interface Props {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function weekStart(): string {
  const d = new Date();
  d.setDate(d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1));
  return d.toISOString().slice(0, 10);
}

function monthStart(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export function TimeRangeFilter({ value, onChange }: Props) {
  const [active, setActive] = useState<RangeKey>('today');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const RANGES: { key: RangeKey; label: string }[] = [
    { key: 'today', label: '今日' },
    { key: 'week', label: '本周' },
    { key: 'month', label: '本月' },
    { key: '30d', label: '最近30天' },
    { key: 'custom', label: '自定义' },
  ];

  const handleClick = (key: RangeKey) => {
    setActive(key);
    const t = todayStr();
    if (key === 'today') onChange({ date_from: t, date_to: t });
    else if (key === 'week') onChange({ date_from: weekStart(), date_to: t });
    else if (key === 'month') onChange({ date_from: monthStart(), date_to: t });
    else if (key === '30d') onChange({ date_from: daysAgo(29), date_to: t });
  };

  return (
    <div className="flex items-center gap-2 mb-4">
      {RANGES.map((r) => (
        <Button
          key={r.key}
          size="sm"
          variant={active === r.key ? 'primary' : 'secondary'}
          onClick={() => handleClick(r.key)}
        >
          {r.label}
        </Button>
      ))}
      {active === 'custom' && (
        <div className="flex items-center gap-1">
          <Input
            type="date"
            value={customFrom}
            onChange={(e) => {
              setCustomFrom(e.target.value);
              if (e.target.value && customTo) onChange({ date_from: e.target.value, date_to: customTo });
            }}
          />
          <span className="text-gray-400">至</span>
          <Input
            type="date"
            value={customTo}
            onChange={(e) => {
              setCustomTo(e.target.value);
              if (customFrom && e.target.value) onChange({ date_from: customFrom, date_to: e.target.value });
            }}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 修改 api.ts 中 dashboardApi.get 接受参数**

```typescript
export const dashboardApi = {
  get: (date_from: string, date_to: string) =>
    api.get('/dashboard', { params: { date_from, date_to } }).then(r => r.data),
  getReceivables: () => api.get('/receivables').then(r => r.data),
};
```

- [ ] **Step 3: 重构 DashboardPage.tsx**

```tsx
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, productApi, customerApi } from '../services/api';
import { Badge } from '../components/ui/Badge';
import { TimeRangeFilter } from '../components/business/TimeRangeFilter';

function todayStr() { return new Date().toISOString().slice(0, 10); }

export default function DashboardPage() {
  const [range, setRange] = useState({ date_from: todayStr(), date_to: todayStr() });

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', range],
    queryFn: () => dashboardApi.get(range.date_from, range.date_to),
  });

  const { data: receivables = [] } = useQuery({ queryKey: ['receivables'], queryFn: dashboardApi.getReceivables });
  const [productNames, setProductNames] = useState<Record<number, string>>({});
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  useEffect(() => {
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
    customerApi.list().then((data: any) => setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name]))));
  }, []);

  if (isLoading) return <p className="text-gray-400">加载中...</p>;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">经营看板</h2>

      <TimeRangeFilter value={range} onChange={setRange} />

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">销售额</div>
          <div className="text-2xl font-bold text-green-600">¥{data?.total_sales || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">收款</div>
          <div className="text-2xl font-bold text-blue-600">¥{data?.total_payments || 0}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">成本</div>
          <div className="text-2xl font-bold text-gray-600">¥{data?.total_cost || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">出库量</div>
          <div className="text-2xl font-bold">{data?.total_out_quantity || 0} 件</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">毛利</div>
          <div className={`text-2xl font-bold ${(data?.total_gross_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ¥{data?.total_gross_profit || 0}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-3">低库存预警（&lt; 10）</h3>
          {data?.low_stock?.length === 0 ? <p className="text-gray-400 text-sm">无预警</p> : (
            data?.low_stock?.map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm py-1 border-b">
                <span>{productNames[item.product_id] || `产品#${item.product_id}`}</span>
                <Badge variant="warning">{item.stock}</Badge>
              </div>
            ))
          )}
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-3">应收排行 Top 5</h3>
          {receivables.length === 0 ? <p className="text-gray-400 text-sm">无应收</p> : (
            receivables.slice(0, 5).map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm py-1 border-b">
                <span>{customerNames[item.customer_id] || `客户#${item.customer_id}`}</span>
                <span className="font-medium text-red-600">¥{item.ar_balance}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 确认编译通过**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/business/TimeRangeFilter.tsx \
        frontend/src/pages/DashboardPage.tsx \
        frontend/src/services/api.ts
git commit -m "feat: dashboard 时间筛选 + 成本/毛利展示"
```

---

### Task 4: 端到端验证

- [ ] **Step 1: 启动前后端，打开 dashboard 页面**

- [ ] **Step 2: 验证时间筛选**

点击"今日"/"本周"/"本月"/"最近30天"/"自定义"，检查：
- 请求 URL 带正确的 `date_from` 和 `date_to`
- 所有指标切换后数字合理

- [ ] **Step 3: 验证指标口径**

- `total_sales` = 选中时段内 `retail + subscription + store_sales` 的金额总和
- `total_cost` = 同口径出库量 × 进价总和
- `total_gross_profit` = sales − cost
- `total_out_quantity` = 同口径出库数量

- [ ] **Step 4: Commit（如有修正）**

```bash
git add .
git commit -m "chore: dashboard 端到端验证通过，收尾修正"
```
