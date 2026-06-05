# 销售页与送货单按客户档位分离 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 销售页只显示零售客户，送货单只显示批发客户，两边客户选择器按 price_tier 过滤。

**Architecture:** CustomerSelect 组件新增 priceTier 参数，透传到后端 API。后端 /api/customers 支持 price_tier 查询参数，customer_repo.search 加过滤条件。

**Tech Stack:** React + TypeScript (前端), FastAPI + SQLAlchemy (后端)

---

### Task 1: 后端支持 price_tier 过滤

**Files:**
- Modify: `backend/app/repositories/customer_repo.py:10-14`
- Modify: `backend/app/services/customer_service.py:21-22`
- Modify: `backend/app/api/customers.py:16-21`

- [ ] **Step 1: customer_repo.search 加 price_tier 参数**

```python
def search(self, keyword: str = "", price_tier: str = "", skip: int = 0, limit: int = 100):
    q = self.db.query(Customer)
    if keyword:
        q = q.filter(Customer.name.ilike(f"%{keyword}%"))
    if price_tier:
        q = q.filter(Customer.price_tier == price_tier)
    return q.offset(skip).limit(limit).all()
```

- [ ] **Step 2: customer_service.list_customers 加 price_tier 参数**

```python
def list_customers(self, keyword: str = "", price_tier: str = ""):
    return self.repo.search(keyword, price_tier=price_tier)
```

- [ ] **Step 3: customers API list_customers 加 price_tier 查询参数**

```python
@router.get("", response_model=list[CustomerOut])
def list_customers(
    keyword: str = Query(""),
    price_tier: str = Query(""),
    svc: CustomerService = Depends(get_customer_service),
):
    return svc.list_customers(keyword, price_tier=price_tier)
```

- [ ] **Step 4: 提交后端改动**

```bash
git add backend/app/repositories/customer_repo.py backend/app/services/customer_service.py backend/app/api/customers.py
git commit -m "feat: customers API 支持 price_tier 过滤参数"
```

---

### Task 2: 前端 api.ts 支持 priceTier 参数

**Files:**
- Modify: `frontend/src/services/api.ts:22`

- [ ] **Step 1: customerApi.list 加 priceTier 参数**

```typescript
list: (keyword = '', priceTier = '') => api.get('/customers', { params: { keyword, price_tier: priceTier } }).then(r => r.data),
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: customerApi.list 支持 priceTier 参数"
```

---

### Task 3: CustomerSelect 组件加 priceTier prop

**Files:**
- Modify: `frontend/src/components/business/CustomerSelect.tsx`

- [ ] **Step 1: 接口加 priceTier，useEffect 依赖它**

```tsx
import { useEffect, useState } from 'react';
import { customerApi } from '../../services/api';

interface CustomerSelectProps {
  value: number | string;
  onChange: (customerId: number) => void;
  allowEmpty?: boolean;
  priceTier?: string;
}
export function CustomerSelect({ value, onChange, allowEmpty = true, priceTier }: CustomerSelectProps) {
  const [customers, setCustomers] = useState<any[]>([]);
  useEffect(() => { customerApi.list('', priceTier).then(setCustomers); }, [priceTier]);
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
    >
      {allowEmpty && <option value="">选客户</option>}
      {customers.map((c: any) => (
        <option key={c.id} value={c.id}>{c.name}</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/business/CustomerSelect.tsx
git commit -m "feat: CustomerSelect 支持 priceTier 过滤"
```

---

### Task 4: SalesPage 传 priceTier="零售"

**Files:**
- Modify: `frontend/src/pages/SalesPage.tsx:73`

- [ ] **Step 1: 修改 CustomerSelect 调用**

将：
```tsx
<CustomerSelect value={customerId} onChange={setCustomerId} />
```
改为：
```tsx
<CustomerSelect value={customerId} onChange={setCustomerId} priceTier="零售" />
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/SalesPage.tsx
git commit -m "feat: 销售页客户选择器只显示零售客户"
```

---

### Task 5: DeliveriesPage 传 priceTier="批发"

**Files:**
- Modify: `frontend/src/pages/DeliveriesPage.tsx:179`
- Modify: `frontend/src/pages/DeliveriesPage.tsx:216`

- [ ] **Step 1: 新建送货单的客户选择器**

将第 179 行：
```tsx
<CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} />
```
改为：
```tsx
<CustomerSelect value={customerId} onChange={(v) => setCustomerId(v)} priceTier="批发" />
```

- [ ] **Step 2: 列表筛选的客户选择器**

将第 216 行：
```tsx
<CustomerSelect value={filterCustomer} onChange={(v) => setFilterCustomer(v)} />
```
改为：
```tsx
<CustomerSelect value={filterCustomer} onChange={(v) => setFilterCustomer(v)} priceTier="批发" />
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/DeliveriesPage.tsx
git commit -m "feat: 送货单客户选择器只显示批发客户"
```

---

### Task 6: 验证

- [ ] **Step 1: 启动后端确认 API 正常**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 2: 前端类型检查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: No new errors

- [ ] **Step 3: 手动验证清单**
  - 销售页：客户下拉只出现 price_tier='零售' 的客户，散客选项正常
  - 送货单新建表单：客户下拉只出现 price_tier='批发' 的客户
  - 送货单列表筛选：客户下拉只出现 price_tier='批发' 的客户
  - 客户管理页：客户列表不受影响，显示全部客户
