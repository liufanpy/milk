# 送货单流程修正 — 实现计划

> **对于自动化执行者：** 使用 superpowers:subagent-driven-development 按任务逐步执行。步骤使用 `- [ ]` 复选框语法追踪进度。

**目标：** 修正送货单流程——分离 delivery/sale 命名、exchange 改用 cancel+new 模式、增加库存校验、支持批量结算。

**架构：** 改动集中在 DeliveryService（创建/换货/详情）、TransactionRepository（AR 计算）、SettlementService（批量结算），以及 dashboard 加 delivery 统计。

**技术栈：** Python/FastAPI/SQLAlchemy/SQLite（后端），React/TypeScript（前端）

**注意：** 项目无测试框架，不包含测试步骤。完成后通过 TestClient 验证所有 API 端点。

---

## 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `backend/app/services/delivery_service.py` | reason/category 改名 + 库存校验 + exchange 重写 + 详情计算修正 |
| 修改 | `backend/app/repositories/transaction_repo.py` | AR 公式更新 |
| 修改 | `backend/app/api/dashboard.py` | today_sales 包含 delivery |
| 修改 | `backend/app/services/settlement_service.py` | 新增 batch_settle 方法 |
| 修改 | `backend/app/schemas/settlement.py` | 新增 BatchSettlement schema |
| 修改 | `backend/app/api/settlements.py` | 新增 POST /batch 端点 |
| 修改 | 数据库已有数据 | 手动改 category + reason |

---

### Task 1: 修正 create_delivery — 命名 + 库存校验

**文件：** `backend/app/services/delivery_service.py`

- [ ] **Step 1: 替换 create_delivery 方法**

将 `create_delivery` 方法替换为：

```python
    def create_delivery(self, data: DeliveryCreate):
        # 库存校验
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        for item in data.items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")

        delivery = self.delivery_repo.create(
            customer_id=data.customer_id,
            delivery_date=data.delivery_date,
            status="pending",
            subscription_order_id=data.subscription_order_id,
            note=data.note,
        )

        total = 0.0
        movements = []
        for item in data.items:
            amount = item.quantity * item.unit_price
            total += amount
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "delivery",
                "quantity": item.quantity,
                "unit_cost": 0.0,
                "delivery_id": delivery.id,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="delivery",
                amount=total,
                delivery_id=delivery.id,
            )

        delivery.status = "delivered"
        self.db.commit()
        return {"id": delivery.id, "total": total}
```

- [ ] **Step 2: 验证**

```bash
cd backend && .venv/bin/python -c "from app.services.delivery_service import DeliveryService; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/delivery_service.py
git commit -m "feat: create_delivery reason/category 改名 delivery，加库存校验"
```

---

### Task 2: 修正 get_delivery_detail — 计算用 delivery 类别

**文件：** `backend/app/services/delivery_service.py`

- [ ] **Step 1: 修改 get_delivery_detail 中的计算**

将方法中的 3 处 `"sale"` 改为 `"delivery"`：

```python
    def get_delivery_detail(self, delivery_id: int):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            return None
        movements = self.stock_repo.get_by_delivery(delivery_id)
        transactions = self.txn_repo.get_by_delivery(delivery_id)

        delivery_total = sum(t.amount for t in transactions if t.category == "delivery")
        delivery_cancel_total = sum(t.amount for t in transactions if t.category == "delivery_cancel")
        paid_total = sum(t.amount for t in transactions if t.category == "payment")

        net = delivery_total + delivery_cancel_total

        return {
            "id": delivery.id,
            "customer_id": delivery.customer_id,
            "delivery_date": str(delivery.delivery_date),
            "status": delivery.status,
            "note": delivery.note,
            "items": [{"product_id": m.product_id, "quantity": m.quantity, "reason": m.reason, "direction": m.direction} for m in movements],
            "total_amount": net,
            "paid_amount": paid_total,
            "unpaid_amount": net - paid_total,
            "transactions": [{"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)} for t in transactions],
        }
```

- [ ] **Step 2: 验证并提交**

```bash
cd backend && .venv/bin/python -c "from app.services.delivery_service import DeliveryService; print('OK')"
git add backend/app/services/delivery_service.py
git commit -m "fix: get_delivery_detail 使用 delivery 类别计算应收"
```

---

### Task 3: 重写 exchange — cancel + new 模式

**文件：** `backend/app/services/delivery_service.py`

- [ ] **Step 1: 替换 exchange 方法**

```python
    def exchange(self, delivery_id: int, data: ExchangeCreate):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        # 计算旧 delivery 净额（当前应收）
        old_transactions = self.txn_repo.get_by_delivery(delivery_id)
        old_total = sum(t.amount for t in old_transactions if t.category == "delivery") + \
                    sum(t.amount for t in old_transactions if t.category == "delivery_cancel")

        # return_items: 退货回库，stock_movement(reason=return)
        return_total = 0.0
        for item in data.return_items:
            amt = item.quantity * item.unit_price
            return_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "delivery_id": delivery_id,
            }])

        # new_items: 出货，stock_movement(reason=delivery)，带库存校验
        inventory = {
            (r.product_id, r.shelf_id): r.stock
            for r in self.stock_repo.get_inventory()
        }
        new_total = 0.0
        for item in data.new_items:
            stock = inventory.get((item.product_id, item.shelf_id), 0)
            if stock < item.quantity:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")
            amt = item.quantity * item.unit_price
            new_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "delivery",
                "quantity": item.quantity,
                "delivery_id": delivery_id,
            }])

        # transaction: 冲抵旧的 delivery + 新建新的 delivery
        if old_total != 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="delivery_cancel",
                amount=-old_total,
                delivery_id=delivery_id,
            )
        if new_total > 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="delivery",
                amount=new_total,
                delivery_id=delivery_id,
            )

        # 更新 delivery.total_amount
        net = old_total + (-old_total) + new_total  # = new_total
        delivery.total_amount = net

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
```

- [ ] **Step 2: 验证并提交**

```bash
cd backend && .venv/bin/python -c "from app.services.delivery_service import DeliveryService; print('OK')"
git add backend/app/services/delivery_service.py
git commit -m "feat: exchange 改为 delivery_cancel 冲抵 + 新 delivery 模式"
```

---

### Task 4: 更新 AR 公式

**文件：** `backend/app/repositories/transaction_repo.py`

- [ ] **Step 1: 替换 get_ar_by_customer 和 get_receivables**

将两处 CASE 中的 `"sale"` 改为 `"delivery"`，`"refund"` 改为 `"delivery_cancel"`：

`get_ar_by_customer`:
```python
    def get_ar_by_customer(self, customer_id: int) -> float:
        result = self.db.query(
            func.sum(
                case(
                    (Transaction.category.in_(["delivery", "delivery_cancel"]), Transaction.amount),
                    (Transaction.category == "payment", -Transaction.amount),
                    (Transaction.category == "subscription", -Transaction.amount),
                    else_=0,
                )
            )
        ).filter(Transaction.customer_id == customer_id).scalar()
        return result or 0.0
```

`get_receivables`:
```python
    def get_receivables(self) -> list:
        case_expr = case(
            (Transaction.category.in_(["delivery", "delivery_cancel"]), Transaction.amount),
            (Transaction.category == "payment", -Transaction.amount),
            (Transaction.category == "subscription", -Transaction.amount),
            else_=0,
        )
        return (
            self.db.query(
                Transaction.customer_id,
                func.sum(case_expr).label("ar_balance"),
            )
            .filter(Transaction.customer_id.isnot(None))
            .group_by(Transaction.customer_id)
            .having(func.sum(case_expr) != 0)
            .all()
        )
```

- [ ] **Step 2: 验证并提交**

```bash
cd backend && .venv/bin/python -c "from app.repositories.transaction_repo import TransactionRepository; print('OK')"
git add backend/app/repositories/transaction_repo.py
git commit -m "fix: AR 公式改为 delivery + delivery_cancel - payment - subscription"
```

---

### Task 5: 更新 Dashboard today_sales 包含 delivery

**文件：** `backend/app/api/dashboard.py`

- [ ] **Step 1: 修改 today_sales 查询**

将 `Transaction.category == "sale"` 改为包含 `"delivery"` 和 `"delivery_cancel"`：

```python
    today_sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.category.in_(["sale", "delivery", "delivery_cancel"]),
        func.date(Transaction.created_at) == today,
    ).scalar() or 0.0
```

- [ ] **Step 2: 验证并提交**

```bash
cd backend && .venv/bin/python -c "from app.api.dashboard import router; print('OK')"
git add backend/app/api/dashboard.py
git commit -m "fix: dashboard today_sales 包含 delivery + delivery_cancel"
```

---

### Task 6: 批量结算

**文件：**
- 修改: `backend/app/schemas/settlement.py`
- 修改: `backend/app/services/settlement_service.py`
- 修改: `backend/app/api/settlements.py`

- [ ] **Step 1: 新增 BatchSettlement schema**

在 `backend/app/schemas/settlement.py` 末尾新增：

```python
from typing import List


class BatchSettlementItem(BaseModel):
    delivery_id: int
    amount: float


class BatchSettlement(BaseModel):
    customer_id: int
    items: List[BatchSettlementItem]
```

- [ ] **Step 2: SettlementService 新增 batch_settle 方法**

在 `backend/app/services/settlement_service.py` 的 `SettlementService` 类中新增：

```python
    def batch_settle(self, customer_id: int, items: list[dict]):
        results = []
        for item in items:
            delivery = self.delivery_repo.get_by_id(item["delivery_id"])
            if not delivery:
                raise ValueError(f"送货单 #{item['delivery_id']} 不存在")
            if delivery.customer_id != customer_id:
                raise ValueError(f"送货单 #{item['delivery_id']} 不属于该客户")
            self.txn_repo.create(
                customer_id=customer_id,
                category="payment",
                amount=item["amount"],
                delivery_id=item["delivery_id"],
            )
            results.append({"delivery_id": item["delivery_id"], "paid": item["amount"]})
        self.db.commit()
        return {"results": results}
```

- [ ] **Step 3: API 新增 POST /batch 端点**

在 `backend/app/api/settlements.py` 中新增：

```python
@router.post("/batch")
def batch_settle(data: BatchSettlement, svc: SettlementService = Depends(get_settlement_service)):
    try:
        return svc.batch_settle(data.customer_id, [it.model_dump() for it in data.items])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

同时新增 import：
```python
from app.schemas.settlement import SettlementCreate, BatchSettlement
```

注：该路由的 prefix 是 `/api/deliveries`，所以完整路径是 `POST /api/deliveries/batch`。

- [ ] **Step 4: 验证并提交**

```bash
cd backend && .venv/bin/python -c "from app.api.settlements import router; print('OK')"
git add backend/app/schemas/settlement.py backend/app/services/settlement_service.py backend/app/api/settlements.py
git commit -m "feat: 批量结算 POST /api/deliveries/batch"
```

---

### Task 7: 已有数据修正

**文件：** 无（手动 SQL）

- [ ] **Step 1: 更新现有数据**

```bash
cd backend && .venv/bin/python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text(\"UPDATE stock_movements SET reason='delivery' WHERE delivery_id IS NOT NULL AND reason='sale'\"))
    conn.execute(text(\"UPDATE transactions SET category='delivery' WHERE delivery_id IS NOT NULL AND category='sale'\"))
    conn.commit()
    print('OK')
"
```

---

### Task 8: 全流程验证

- [ ] **Step 1: 验证所有端点**

```bash
cd backend && .venv/bin/python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

# 1. 创建送货单（库存充足的产品）
resp = client.post('/api/deliveries', json={
    'customer_id': 1,
    'delivery_date': '2026-06-05',
    'items': [{'product_id': 6, 'quantity': 1, 'unit_price': 10.0, 'shelf_id': 1}],
    'note': 'test'
})
print('1. Create delivery:', resp.status_code, resp.json())
assert resp.status_code == 201
d_id = resp.json()['id']

# 2. 创建送货单（库存不足）— 应该报错
resp2 = client.post('/api/deliveries', json={
    'customer_id': 1,
    'delivery_date': '2026-06-05',
    'items': [{'product_id': 6, 'quantity': 999, 'unit_price': 10.0, 'shelf_id': 1}],
})
print('2. Insufficient stock:', resp2.status_code, resp2.json().get('detail',''))

# 3. 列表
resp3 = client.get('/api/deliveries')
print('3. List:', len(resp3.json()))

# 4. 详情
resp4 = client.get(f'/api/deliveries/{d_id}')
d = resp4.json()
print(f'4. Detail: total={d[\"total_amount\"]} paid={d[\"paid_amount\"]} unpaid={d[\"unpaid_amount\"]}')

# 5. 换货
resp5 = client.post(f'/api/deliveries/{d_id}/exchange', json={
    'return_items': [{'product_id': 6, 'quantity': 1, 'unit_price': 10.0, 'shelf_id': 1}],
    'new_items': [{'product_id': 7, 'quantity': 1, 'unit_price': 8.0, 'shelf_id': 1}]
})
print('5. Exchange:', resp5.status_code, resp5.json())

# 6. 详情（换货后）
resp6 = client.get(f'/api/deliveries/{d_id}')
d2 = resp6.json()
print(f'6. After exchange: total={d2[\"total_amount\"]} unpaid={d2[\"unpaid_amount\"]} txns={len(d2[\"transactions\"])}')

# 7. 批量结算
resp7 = client.post('/api/deliveries/batch', json={
    'customer_id': 1,
    'items': [{'delivery_id': d_id, 'amount': 4.0}]
})
print('7. Batch settle:', resp7.status_code, resp7.json())

# 8. AR
resp8 = client.get('/api/receivables')
print('8. Receivables:', resp8.json())

# 9. Dashboard
resp9 = client.get('/api/dashboard')
print('9. Dashboard today_sales:', resp9.json()['today_sales'])

print()
print('ALL TESTS PASSED')
"
```

---

## 自检清单

**1. Spec 覆盖度：**
- [x] reason/category sale→delivery → Task 1
- [x] exchange cancel+new → Task 3
- [x] 库存校验 → Task 1 + Task 3
- [x] AR 公式 → Task 4
- [x] 批量结算 → Task 6
- [x] 已有数据修正 → Task 7
- [x] dashboard 包含 delivery → Task 5

**2. 占位符检查：** 无 TBD/TODO。

**3. 类型一致性：** BatchSettlement schema 与 service 参数一致。
