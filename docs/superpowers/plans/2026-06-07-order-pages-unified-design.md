# 单据页面统一设计 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为退货/损耗建立 Order 单头层，统一 6 个单据页面的列表/详情交互模式，抽取公共组件消除重复代码。

**Architecture:** 分三层推进——先建后端数据模型和 API（退货/损耗各建单头表），再抽前端公共组件（6 个），最后逐页迁移接入。每层产出独立可验证。

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (后端), React/TypeScript/TanStack Query (前端)

---

## 文件结构

```
backend/
├── app/models/
│   ├── return_order.py          ← 新增
│   ├── wastage_order.py         ← 新增
│   ├── stock_movement.py        ← 修改：+return_order_id, +wastage_order_id
│   ├── transaction.py           ← 修改：+return_order_id
│   └── __init__.py              ← 修改：注册新 model
├── app/repositories/
│   ├── return_order_repo.py     ← 新增
│   ├── wastage_order_repo.py    ← 新增
│   └── stock_movement_repo.py   ← 修改：+get_by_return_order, +get_by_wastage_order
├── app/services/
│   ├── return_service.py        ← 重写
│   └── wastage_service.py       ← 重写
├── app/schemas/
│   ├── return_schema.py         ← 修改：+source_type, +source_order_id
│   └── wastage.py               ← 修改：reason 缩为3种
├── app/api/
│   ├── returns.py               ← 重写
│   └── wastage.py               ← 重写
├── alembic/versions/
│   ├── add_return_orders.py     ← 新增 migration
│   └── add_wastage_orders.py    ← 新增 migration
└── tests/
    ├── test_return.py           ← 新增
    └── test_wastage.py          ← 新增

frontend/
├── src/
│   ├── components/ui/
│   │   ├── StatusBadge.tsx       ← 新增
│   │   └── ItemRowEditor.tsx     ← 新增
│   ├── components/business/
│   │   ├── ItemDetailTable.tsx   ← 新增
│   │   ├── OrderListTable.tsx    ← 新增
│   │   ├── OrderDetailModal.tsx  ← 新增
│   │   └── OrderFormModal.tsx    ← 新增
│   ├── hooks/
│   │   ├── useReturns.ts         ← 新增
│   │   └── useWastage.ts         ← 新增
│   ├── services/api.ts           ← 修改：加 returnApi/wastageApi 新方法
│   ├── pages/
│   │   ├── ReturnsPage.tsx       ← 重写
│   │   ├── WastagePage.tsx       ← 重写
│   │   ├── SalesPage.tsx         ← 重写
│   │   ├── PurchasesPage.tsx     ← 重写
│   │   ├── DeliveriesPage.tsx    ← 重写
│   │   └── SubscriptionsPage.tsx ← 轻改
│   └── types/index.ts           ← 修改：加新 interface
```

---

### Task 1: 创建 return_orders 模型 + migration

**Files:**
- Create: `backend/app/models/return_order.py`
- Create: `backend/alembic/versions/add_return_orders.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/stock_movement.py`
- Modify: `backend/app/models/transaction.py`

- [ ] **Step 1: 写 ReturnOrder 模型 + 给已有表加 FK 字段**

```python
# backend/app/models/return_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class ReturnOrder(Base):
    __tablename__ = "return_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    source_type = Column(String(20), nullable=True)
    source_order_id = Column(Integer, nullable=True)
    note = Column(String(500), default="")
    status = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

同时在已有模型里加：

```python
# backend/app/models/stock_movement.py 追加:
return_order_id = Column(Integer, ForeignKey("return_orders.id"), nullable=True)

# backend/app/models/transaction.py 追加:
return_order_id = Column(Integer, ForeignKey("return_orders.id"), nullable=True)
```

- [ ] **Step 2: 生成并运行 migration（此时 autogenerate 能检测到所有改动）**

```bash
cd backend && alembic revision --autogenerate -m "add return_orders"
cd backend && alembic upgrade head
```

Expected: 表创建 + FK 列添加成功，无报错。

- [ ] **Step 4: 运行迁移验证**

```bash
cd backend && alembic upgrade head
```

Expected: 表创建成功，无报错。

- [ ] **Step 5: 注册 model**

```python
# backend/app/models/__init__.py 追加:
from app.models.return_order import ReturnOrder
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/return_order.py backend/app/models/__init__.py \
  backend/app/models/stock_movement.py backend/app/models/transaction.py \
  backend/alembic/versions/add_return_orders.py
git commit -m "feat: add return_orders table + FK columns on stock_movements/transactions"
```

---

### Task 2: 创建 ReturnOrderRepository

**Files:**
- Create: `backend/app/repositories/return_order_repo.py`

- [ ] **Step 1: 写 repo**

```python
# backend/app/repositories/return_order_repo.py
from typing import Optional
from sqlalchemy.orm import Session
from app.models.return_order import ReturnOrder


class ReturnOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> ReturnOrder:
        order = ReturnOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, id: int) -> Optional[ReturnOrder]:
        return self.db.query(ReturnOrder).filter(ReturnOrder.id == id).first()

    def list_all(self):
        return self.db.query(ReturnOrder).order_by(ReturnOrder.created_at.desc()).all()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/repositories/return_order_repo.py
git commit -m "feat: add ReturnOrderRepository"
```

---

### Task 3: 改造 ReturnService + ReturnSchema

**Files:**
- Modify: `backend/app/services/return_service.py`
- Modify: `backend/app/schemas/return_schema.py`

- [ ] **Step 1: 更新 schema**

```python
# backend/app/schemas/return_schema.py
from pydantic import BaseModel
from typing import List, Optional


class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_wasted: bool = False


class ReturnCreate(BaseModel):
    customer_id: int
    source_type: Optional[str] = None   # 'delivery' | 'retail' | 'subscription'
    source_order_id: Optional[int] = None
    items: List[ReturnItem]
    note: str = ""
```

- [ ] **Step 2: 重写 ReturnService**

```python
# backend/app/services/return_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.return_order_repo import ReturnOrderRepository
from app.schemas.return_schema import ReturnCreate
from app.models.return_order import ReturnOrder
from app.models.transaction import Transaction
from app.models.product import Product
from app.models.customer import Customer


class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.return_repo = ReturnOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_return(self, data: ReturnCreate):
        order = self.return_repo.create(
            customer_id=data.customer_id,
            source_type=data.source_type,
            source_order_id=data.source_order_id,
            note=data.note,
        )

        refund_total = 0.0
        for item in data.items:
            # 退货入库
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "return_order_id": order.id,
            }])
            # 如果产品已报废，额外做一条出库
            if item.is_wasted:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "out",
                    "reason": "wastage",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "return_order_id": order.id,
                }])
            refund_total += item.quantity * item.unit_price

        # 退款
        if refund_total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="refund",
                amount=refund_total,
                return_order_id=order.id,
            )

        self.db.commit()
        return {"id": order.id, "refund_total": refund_total}

    def list_returns(self):
        from app.models.stock_movement import StockMovement

        orders = self.return_repo.list_all()
        if not orders:
            return []

        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        products = {p.id: p.name for p in self.db.query(Product).all()}

        order_ids = [o.id for o in orders]
        movements = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.return_order_id.in_(order_ids),
                StockMovement.reason == "return",
            )
            .all()
        )
        refunds = {
            t.return_order_id: t.amount
            for t in self.db.query(Transaction).filter(
                Transaction.return_order_id.in_(order_ids),
                Transaction.category == "refund",
            ).all()
        }

        order_items: dict[int, list] = {}
        for m in movements:
            order_items.setdefault(m.return_order_id, []).append(m)

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
                "customer_name": customers.get(o.customer_id, ""),
                "source_type": o.source_type,
                "source_order_id": o.source_order_id,
                "item_count": len(items),
                "total_refund": refunds.get(o.id, 0),
                "note": o.note,
                "status": o.status,
                "items_summary": summary,
                "created_at": str(o.created_at),
            })

        return result

    def get_return_detail(self, order_id: int):
        order = self.return_repo.get_by_id(order_id)
        if not order:
            return None

        items = self.stock_repo.get_by_return_order(order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}
        customers = {c.id: c.name for c in self.db.query(Customer).all()}

        refunds = (
            self.db.query(Transaction)
            .filter(
                Transaction.return_order_id == order_id,
                Transaction.category == "refund",
            ).all()
        )
        total_refund = sum(t.amount for t in refunds)

        def item_dict(m):
            return {
                "product_id": m.product_id,
                "product_name": products.get(m.product_id, ""),
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
            }

        return {
            "id": order.id,
            "customer_id": order.customer_id,
            "customer_name": customers.get(order.customer_id, ""),
            "source_type": order.source_type,
            "source_order_id": order.source_order_id,
            "item_count": len(items),
            "total_refund": total_refund,
            "note": order.note,
            "status": order.status,
            "items": [item_dict(m) for m in items if m.direction == "in" and m.reason == "return"],
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in refunds
            ],
            "created_at": str(order.created_at),
        }

    def cancel_return(self, order_id: int):
        order = self.return_repo.get_by_id(order_id)
        if not order:
            raise ValueError("退货单不存在")
        if order.status == "cancelled":
            raise ValueError("该退货单已撤销")

        # 查原始记录
        original_items = self.stock_repo.get_by_return_order(order_id)
        for m in original_items:
            # 反向冲抵库存
            reverse_dir = "out" if m.direction == "in" else "in"
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": reverse_dir,
                "reason": "cancel",
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
                "return_order_id": order_id,
            }])

        # 反向冲抵账务
        original_txns = (
            self.db.query(Transaction)
            .filter(Transaction.return_order_id == order_id)
            .all()
        )
        for t in original_txns:
            self.txn_repo.create(
                customer_id=order.customer_id,
                category=t.category,
                amount=-t.amount,
                return_order_id=order_id,
            )

        self.return_repo.update_status(order_id, "cancelled")
        self.db.commit()
        return {"id": order.id, "status": "cancelled"}
```

- [ ] **Step 3: 给 StockMovementRepository 加查询方法**

```python
# backend/app/repositories/stock_movement_repo.py 追加两个方法:

def get_by_return_order(self, return_order_id: int) -> list:
    return self.db.query(StockMovement).filter(
        StockMovement.return_order_id == return_order_id
    ).all()

def get_by_wastage_order(self, wastage_order_id: int) -> list:
    return self.db.query(StockMovement).filter(
        StockMovement.wastage_order_id == wastage_order_id
    ).all()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/return_service.py backend/app/schemas/return_schema.py \
  backend/app/repositories/stock_movement_repo.py
git commit -m "feat: ReturnService 重构 — 基于 return_orders 单头，支持 list/detail/cancel"
```

---

### Task 4: 改造退货 API

**Files:**
- Modify: `backend/app/api/returns.py`

- [ ] **Step 1: 重写 returns.py**

```python
# backend/app/api/returns.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.return_service import ReturnService
from app.schemas.return_schema import ReturnCreate

router = APIRouter(prefix="/api/returns", tags=["returns"])


def get_return_service(db: Session = Depends(get_db)):
    return ReturnService(db)


@router.post("", status_code=201)
def create_return(data: ReturnCreate, svc: ReturnService = Depends(get_return_service)):
    return svc.create_return(data)


@router.get("")
def list_returns(svc: ReturnService = Depends(get_return_service)):
    return svc.list_returns()


@router.get("/{order_id}")
def get_return(order_id: int, svc: ReturnService = Depends(get_return_service)):
    detail = svc.get_return_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="退货单不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_return(order_id: int, svc: ReturnService = Depends(get_return_service)):
    try:
        return svc.cancel_return(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/returns.py
git commit -m "feat: 退货 API 加 detail/cancel 端点，改查 return_orders"
```

---

### Task 5: 测试退货功能

**Files:**
- Create: `backend/tests/test_return.py`

- [ ] **Step 1: 写测试**

```python
# backend/tests/test_return.py
"""测试退货单创建/列表/详情/撤销"""


class TestReturnCreate:
    def test_create_return_writes_stock_and_refund(self, client, seed_data):
        """创建退货单：库存入库 + 退款 transaction"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p.id, "quantity": 2, "unit_price": 45},
            ],
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["refund_total"] == 90

        # 验证库存变化（退货入库 2 箱）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 2

    def test_create_return_with_source_tracking(self, client, seed_data):
        """退货关联来源零售单"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "source_type": "retail",
            "source_order_id": 99,
            "items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 45},
            ],
        })

        assert resp.status_code == 201
        # 验证详情中有来源信息
        order_id = resp.json()["id"]
        detail = client.get(f"/api/returns/{order_id}").json()
        assert detail["source_type"] == "retail"
        assert detail["source_order_id"] == 99

    def test_create_return_with_wasted_item(self, client, seed_data):
        """退货且报废：入库 + 同时出库（库存净增为 0）"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 45, "is_wasted": True},
            ],
        })

        assert resp.status_code == 201
        # 报废的退货：入库 3 + 出库 3 = 净增 0
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is None or stock["stock"] == 0


class TestReturnListAndDetail:
    def test_list_returns_order_structure(self, client, seed_data):
        """退货列表返回单头结构"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 2, "unit_price": 45}],
        })

        resp = client.get("/api/returns")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        order = data[0]
        assert "customer_name" in order
        assert "items_summary" in order
        assert "total_refund" in order
        assert "status" in order

    def test_detail_includes_items(self, client, seed_data):
        """退货详情包含品项明细"""
        c = seed_data["customers"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 45},
                {"product_id": p2.id, "quantity": 1, "unit_price": 55},
            ],
        })

        order_id = resp.json()["id"]
        detail = client.get(f"/api/returns/{order_id}").json()
        assert len(detail["items"]) == 2
        assert detail["total_refund"] == 145  # 90 + 55


class TestReturnCancel:
    def test_cancel_reverses_stock_and_refund(self, client, seed_data):
        """撤销退货：库存反向 + 退款冲抵"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 2, "unit_price": 45}],
        })
        order_id = resp.json()["id"]

        # 撤销
        resp = client.post(f"/api/returns/{order_id}/cancel")
        assert resp.status_code == 200

        # 库存归零（入库 2 + 冲抵 out 2 = 0）
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is None or stock["stock"] == 0

        # 状态变为 cancelled
        detail = client.get(f"/api/returns/{order_id}").json()
        assert detail["status"] == "cancelled"

    def test_cancel_already_cancelled_fails(self, client, seed_data):
        """已撤销的退货不可再撤销"""
        c = seed_data["customers"][0]
        p = seed_data["products"][0]

        resp = client.post("/api/returns", json={
            "customer_id": c.id,
            "items": [{"product_id": p.id, "quantity": 1, "unit_price": 45}],
        })
        order_id = resp.json()["id"]

        client.post(f"/api/returns/{order_id}/cancel")
        resp = client.post(f"/api/returns/{order_id}/cancel")
        assert resp.status_code == 400
```

- [ ] **Step 2: 运行测试**

```bash
cd backend && python -m pytest tests/test_return.py -v
```

Expected: 全部 PASS（6 条测试）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_return.py
git commit -m "test: 退货单 create/list/detail/cancel 测试"
```

---

### Task 6: 创建 wastage_orders 模型 + migration

**Files:**
- Create: `backend/app/models/wastage_order.py`
- Create: `backend/alembic/versions/add_wastage_orders.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/stock_movement.py`

- [ ] **Step 1: 写 WastageOrder 模型 + StockMovement 加 FK**

```python
# backend/app/models/wastage_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class WastageOrder(Base):
    __tablename__ = "wastage_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note = Column(String(500), default="")
    status = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

```python
# backend/app/models/stock_movement.py 追加:
wastage_order_id = Column(Integer, ForeignKey("wastage_orders.id"), nullable=True)
```

- [ ] **Step 2: 生成并运行 migration**

```bash
cd backend && alembic revision --autogenerate -m "add wastage_orders"
cd backend && alembic upgrade head
```

Expected: 表创建成功。

- [ ] **Step 4: 注册 model**

```python
# backend/app/models/__init__.py 追加:
from app.models.wastage_order import WastageOrder
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/wastage_order.py backend/app/models/__init__.py \
  backend/app/models/stock_movement.py \
  backend/alembic/versions/add_wastage_orders.py
git commit -m "feat: add wastage_orders table + FK on stock_movements"
```

---

### Task 7: 创建 WastageOrderRepository + 改造 WastageService

**Files:**
- Create: `backend/app/repositories/wastage_order_repo.py`
- Modify: `backend/app/schemas/wastage.py`
- Modify: `backend/app/services/wastage_service.py`

- [ ] **Step 1: 写 WastageOrderRepository**

```python
# backend/app/repositories/wastage_order_repo.py
from typing import Optional
from sqlalchemy.orm import Session
from app.models.wastage_order import WastageOrder


class WastageOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> WastageOrder:
        order = WastageOrder(**kwargs)
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, id: int) -> Optional[WastageOrder]:
        return self.db.query(WastageOrder).filter(WastageOrder.id == id).first()

    def list_all(self):
        return self.db.query(WastageOrder).order_by(WastageOrder.created_at.desc()).all()

    def update_status(self, order_id: int, status: str):
        order = self.get_by_id(order_id)
        if order:
            order.status = status
```

- [ ] **Step 2: 更新 WastageSchema — reason 缩为 3 种**

```python
# backend/app/schemas/wastage.py
from pydantic import BaseModel
from typing import List

VALID_REASONS = {"expired", "damaged", "self_consumed"}


class WastageItem(BaseModel):
    product_id: int
    quantity: int
    reason: str          # expired / damaged / self_consumed


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
```

- [ ] **Step 3: 重写 WastageService**

```python
# backend/app/services/wastage_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.wastage_order_repo import WastageOrderRepository
from app.schemas.wastage import WastageCreate, VALID_REASONS
from app.models.wastage_order import WastageOrder
from app.models.product import Product


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.wastage_repo = WastageOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_wastage(self, data: WastageCreate):
        for item in data.items:
            if item.reason not in VALID_REASONS:
                raise ValueError(f"无效的损耗原因: {item.reason}")

        self.stock_repo.validate_stock(data.items)

        order = self.wastage_repo.create(note=data.note)

        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}

        movements = []
        total_cost = 0.0
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": item.reason,
                "quantity": item.quantity,
                "unit_price": costs.get(item.product_id, 0),
                "wastage_order_id": order.id,
            })
            total_cost += item.quantity * costs.get(item.product_id, 0)

        self.stock_repo.bulk_create(movements)

        if total_cost > 0:
            self.txn_repo.create(
                category="wastage",
                amount=-total_cost,
            )

        self.db.commit()
        return {"id": order.id, "item_count": len(data.items), "total_cost": total_cost}

    def list_wastage(self):
        from app.models.stock_movement import StockMovement

        orders = self.wastage_repo.list_all()
        if not orders:
            return []

        products = {p.id: p.name for p in self.db.query(Product).all()}

        order_ids = [o.id for o in orders]
        movements = (
            self.db.query(StockMovement)
            .filter(StockMovement.wastage_order_id.in_(order_ids))
            .all()
        )

        order_items: dict[int, list] = {}
        for m in movements:
            order_items.setdefault(m.wastage_order_id, []).append(m)

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

            reasons = list({m.reason for m in items})

            result.append({
                "id": o.id,
                "item_count": len(items),
                "reasons": reasons,
                "items_summary": summary,
                "note": o.note,
                "status": o.status,
                "created_at": str(o.created_at),
            })

        return result

    def get_wastage_detail(self, order_id: int):
        order = self.wastage_repo.get_by_id(order_id)
        if not order:
            return None

        items = self.stock_repo.get_by_wastage_order(order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}

        def item_dict(m):
            return {
                "product_id": m.product_id,
                "product_name": products.get(m.product_id, ""),
                "quantity": m.quantity,
                "reason": m.reason,
                "unit_price": m.unit_price or 0,
            }

        total_cost = sum(m.quantity * (m.unit_price or 0) for m in items)

        return {
            "id": order.id,
            "note": order.note,
            "status": order.status,
            "item_count": len(items),
            "total_cost": total_cost,
            "items": [item_dict(m) for m in items],
            "created_at": str(order.created_at),
        }

    def cancel_wastage(self, order_id: int):
        order = self.wastage_repo.get_by_id(order_id)
        if not order:
            raise ValueError("损耗单不存在")
        if order.status == "cancelled":
            raise ValueError("该损耗单已撤销")

        original_items = self.stock_repo.get_by_wastage_order(order_id)
        for m in original_items:
            self.stock_repo.bulk_create([{
                "product_id": m.product_id,
                "direction": "in",
                "reason": "cancel",
                "quantity": m.quantity,
                "unit_price": m.unit_price or 0,
                "wastage_order_id": order_id,
            }])

        self.wastage_repo.update_status(order_id, "cancelled")
        self.db.commit()
        return {"id": order.id, "status": "cancelled"}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/wastage_order_repo.py \
  backend/app/schemas/wastage.py backend/app/services/wastage_service.py
git commit -m "feat: WastageService 重构 — 基于 wastage_orders 单头，reason 缩为3种"
```

---

### Task 8: 改造损耗 API + 测试

**Files:**
- Modify: `backend/app/api/wastage.py`
- Create: `backend/tests/test_wastage.py`

- [ ] **Step 1: 重写 wastage.py**

```python
# backend/app/api/wastage.py
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.wastage_service import WastageService
from app.schemas.wastage import WastageCreate
from app.models.wastage_order import WastageOrder
from app.models.stock_movement import StockMovement
from app.models.product import Product

router = APIRouter(prefix="/api/wastage", tags=["wastage"])


def get_wastage_service(db: Session = Depends(get_db)):
    return WastageService(db)


@router.post("", status_code=201)
def create_wastage(data: WastageCreate, svc: WastageService = Depends(get_wastage_service)):
    try:
        return svc.create_wastage(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_wastage(svc: WastageService = Depends(get_wastage_service)):
    return svc.list_wastage()


# ⚠️ /export 必须在 /{order_id} 之前注册，否则 "export" 会被当成 order_id
@router.get("/export")
def export_wastage(db: Session = Depends(get_db)):
    rows = db.query(StockMovement).join(WastageOrder).filter(
        StockMovement.wastage_order_id.isnot(None)
    ).order_by(StockMovement.created_at.desc()).all()
    products = {p.id: p.name for p in db.query(Product).all()}
    csv_lines = ["产品名称,数量,原因,时间"]
    for r in rows:
        pname = products.get(r.product_id, str(r.product_id))
        csv_lines.append(f"{pname},{r.quantity},{r.reason},{r.created_at}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wastage.csv"},
    )


@router.get("/{order_id}")
def get_wastage(order_id: int, svc: WastageService = Depends(get_wastage_service)):
    detail = svc.get_wastage_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="损耗单不存在")
    return detail


@router.post("/{order_id}/cancel")
def cancel_wastage(order_id: int, svc: WastageService = Depends(get_wastage_service)):
    try:
        return svc.cancel_wastage(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: 写测试**

```python
# backend/tests/test_wastage.py
"""测试损耗单创建/列表/详情/撤销"""


class TestWastageCreate:
    def test_create_wastage_writes_stock_out(self, client, seed_data):
        """创建损耗单：库存减少"""
        # 先进货入库 10 箱
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 10, "unit_price": 35}],
            "status": "confirmed",
        })

        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 3, "reason": "expired"}],
        })

        assert resp.status_code == 201
        assert resp.json()["item_count"] == 1

        # 库存剩 7
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock is not None
        assert stock["stock"] == 7

    def test_create_wastage_invalid_reason_fails(self, client, seed_data):
        """无效的 reason 被拒绝"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })

        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 1, "reason": "giveaway"}],
        })
        assert resp.status_code == 400

    def test_create_wastage_insufficient_stock_fails(self, client, seed_data):
        """库存不足时拒绝"""
        p = seed_data["products"][0]
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 100, "reason": "damaged"}],
        })
        assert resp.status_code == 400


class TestWastageListAndDetail:
    def test_list_returns_order_structure(self, client, seed_data):
        """损耗列表返回单头结构"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "expired"}],
        })

        resp = client.get("/api/wastage")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "items_summary" in data[0]
        assert "reasons" in data[0]
        assert "status" in data[0]

    def test_detail_includes_reason(self, client, seed_data):
        """损耗详情包含品项 reason"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "self_consumed"}],
        })
        order_id = resp.json()["id"]

        detail = client.get(f"/api/wastage/{order_id}").json()
        assert detail["items"][0]["reason"] == "self_consumed"


class TestWastageCancel:
    def test_cancel_reverses_stock(self, client, seed_data):
        """撤销损耗：库存恢复"""
        s = seed_data["suppliers"][0]
        p = seed_data["products"][0]
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [{"product_id": p.id, "quantity": 5, "unit_price": 35}],
            "status": "confirmed",
        })
        resp = client.post("/api/wastage", json={
            "items": [{"product_id": p.id, "quantity": 2, "reason": "expired"}],
        })
        order_id = resp.json()["id"]

        client.post(f"/api/wastage/{order_id}/cancel")

        # 库存恢复 5
        inventory = client.get("/api/inventory").json()
        stock = next((r for r in inventory if r["product_id"] == p.id), None)
        assert stock["stock"] == 5
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && python -m pytest tests/test_wastage.py -v
```

Expected: 全部 PASS（6 条测试）

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/wastage.py backend/tests/test_wastage.py
git commit -m "feat: 损耗 API 加 detail/cancel 端点 + 测试"
```

---

### Task 9: 创建前端共享组件 — StatusBadge + ItemRowEditor

**Files:**
- Create: `frontend/src/components/ui/StatusBadge.tsx`
- Create: `frontend/src/components/ui/ItemRowEditor.tsx`

- [ ] **Step 1: 写 StatusBadge**

```tsx
// frontend/src/components/ui/StatusBadge.tsx
import { Badge } from './Badge';

interface StatusConfig {
  [status: string]: {
    label: string;
    variant: 'success' | 'warning' | 'danger' | 'default';
  };
}

interface StatusBadgeProps {
  status: string;
  config: StatusConfig;
}

export function StatusBadge({ status, config }: StatusBadgeProps) {
  const item = config[status] ?? { label: status, variant: 'default' as const };
  return <Badge variant={item.variant}>{item.label}</Badge>;
}
```

- [ ] **Step 2: 写 ItemRowEditor**

```tsx
// frontend/src/components/ui/ItemRowEditor.tsx
import { ReactNode } from 'react';
import { Button } from './Button';
import { Input } from './Input';
import { ProductSelect } from '../business/ProductSelect';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
}

interface ItemRowEditorProps<T extends ItemRow> {
  items: T[];
  onUpdate: (idx: number, field: keyof T, value: number | boolean) => void;
  onProductChange: (idx: number, productId: number) => void;
  onRemove: (idx: number) => void;
  onAdd: () => void;
  minRows?: number;
  onlyInStock?: boolean;
  children?: (item: T, idx: number) => ReactNode;
}

export function ItemRowEditor<T extends ItemRow>({
  items,
  onUpdate,
  onProductChange,
  onRemove,
  onAdd,
  minRows = 1,
  onlyInStock = false,
  children,
}: ItemRowEditorProps<T>) {
  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx} className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500">产品</label>
            <ProductSelect
              value={item.product_id}
              onChange={(v) => onProductChange(idx, v)}
              onlyInStock={onlyInStock}
            />
          </div>
          <div className="w-20">
            <label className="text-xs text-gray-500">数量</label>
            <Input
              type="number"
              value={String(item.quantity)}
              onChange={(e) => onUpdate(idx, 'quantity' as keyof T, Number(e.target.value))}
            />
          </div>
          <div className="w-24">
            <label className="text-xs text-gray-500">单价</label>
            <Input
              type="number"
              value={String(item.unit_price)}
              onChange={(e) => onUpdate(idx, 'unit_price' as keyof T, Number(e.target.value))}
            />
          </div>
          {children?.(item, idx)}
          <Button
            variant="danger"
            size="sm"
            onClick={() => onRemove(idx)}
            disabled={items.length <= minRows}
          >×</Button>
        </div>
      ))}
      <Button variant="secondary" size="sm" onClick={onAdd}>+ 加行</Button>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/StatusBadge.tsx frontend/src/components/ui/ItemRowEditor.tsx
git commit -m "feat: add StatusBadge + ItemRowEditor shared components"
```

---

### Task 10: 创建前端共享组件 — ItemDetailTable + OrderListTable

**Files:**
- Create: `frontend/src/components/business/ItemDetailTable.tsx`
- Create: `frontend/src/components/business/OrderListTable.tsx`

- [ ] **Step 1: 写 ItemDetailTable**

```tsx
// frontend/src/components/business/ItemDetailTable.tsx

interface DetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface ItemDetailTableProps {
  items: DetailItem[];
  productNames?: Record<number, string>;
}

export function ItemDetailTable({ items, productNames }: ItemDetailTableProps) {
  const getName = (item: DetailItem) =>
    item.product_name || productNames?.[item.product_id] || `产品#${item.product_id}`;

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  return (
    <div>
      <table className="w-full text-sm border-t mt-2">
        <thead>
          <tr className="text-gray-500">
            <th className="px-2 py-1 text-left">产品</th>
            <th className="px-2 py-1 text-right">数量</th>
            <th className="px-2 py-1 text-right">单价</th>
            <th className="px-2 py-1 text-right">小计</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} className="border-t">
              <td className="px-2 py-1">{getName(it)}</td>
              <td className="px-2 py-1 text-right">{it.quantity}</td>
              <td className="px-2 py-1 text-right">¥{it.unit_price.toFixed(2)}</td>
              <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_price).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-right font-bold mt-2">合计: ¥{total.toFixed(2)}</div>
    </div>
  );
}
```

- [ ] **Step 2: 写 OrderListTable**

```tsx
// frontend/src/components/business/OrderListTable.tsx
import { ReactNode } from 'react';

interface Column<T> {
  key: string;
  title: string;
  render?: (item: T) => ReactNode;
}

interface OrderListTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (item: T) => string | number;
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
  emptyText?: string;
}

export function OrderListTable<T extends Record<string, any>>({
  columns,
  data,
  rowKey,
  onRowClick,
  isLoading = false,
  emptyText = '暂无数据',
}: OrderListTableProps<T>) {
  if (isLoading) {
    return <p className="text-center py-8 text-gray-400">加载中...</p>;
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 text-left font-medium">
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-8 text-gray-400">
                  {emptyText}
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr
                  key={rowKey(item)}
                  className="border-t hover:bg-gray-50 cursor-pointer"
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      {col.render ? col.render(item) : item[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/business/ItemDetailTable.tsx \
  frontend/src/components/business/OrderListTable.tsx
git commit -m "feat: add ItemDetailTable + OrderListTable shared components"
```

---

### Task 11: 创建 OrderDetailModal + OrderFormModal

**Files:**
- Create: `frontend/src/components/business/OrderDetailModal.tsx`
- Create: `frontend/src/components/business/OrderFormModal.tsx`

- [ ] **Step 1: 写 OrderDetailModal**

```tsx
// frontend/src/components/business/OrderDetailModal.tsx
import { ReactNode } from 'react';
import { Modal } from '../ui/Modal';
import { StatusBadge } from '../ui/StatusBadge';
import { ItemDetailTable } from './ItemDetailTable';
import type { StatusConfig } from '../ui/StatusBadge';

interface DetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}

interface OrderDetailModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  headerInfo: ReactNode;
  items: DetailItem[];
  status?: string;
  statusConfig?: StatusConfig;
  children?: ReactNode;   // 底部操作按钮
}

export function OrderDetailModal({
  open,
  onClose,
  title,
  headerInfo,
  items,
  status,
  statusConfig,
  children,
}: OrderDetailModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 text-sm">{headerInfo}</div>
          {status && statusConfig && (
            <StatusBadge status={status} config={statusConfig} />
          )}
        </div>
        <ItemDetailTable items={items} />
        {children && (
          <div className="flex gap-2 pt-2 border-t">{children}</div>
        )}
      </div>
    </Modal>
  );
}
```

- [ ] **Step 2: 写 OrderFormModal**

```tsx
// frontend/src/components/business/OrderFormModal.tsx
import { ReactNode } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

interface OrderFormModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: () => void;
  isPending?: boolean;
  submitLabel?: string;
  children: ReactNode;
}

export function OrderFormModal({
  open,
  onClose,
  title,
  onSubmit,
  isPending = false,
  submitLabel = '提交',
  children,
}: OrderFormModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="space-y-4">
        {children}
        <div className="flex gap-2 pt-2 border-t">
          <Button onClick={onSubmit} disabled={isPending}>{submitLabel}</Button>
          <Button variant="secondary" onClick={onClose}>取消</Button>
        </div>
      </div>
    </Modal>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/business/OrderDetailModal.tsx \
  frontend/src/components/business/OrderFormModal.tsx
git commit -m "feat: add OrderDetailModal + OrderFormModal shared components"
```

---

### Task 12: 改造前端 — ReturnsPage

**Files:**
- Create: `frontend/src/hooks/useReturns.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/ReturnsPage.tsx`

- [ ] **Step 1: 更新 api.ts 中的 returnApi**

```typescript
// 替换现有 returnApi:
export const returnApi = {
  create: (data: any) => api.post('/returns', data).then(r => r.data),
  list: () => api.get('/returns').then(r => r.data),
  get: (id: number) => api.get(`/returns/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/returns/${id}/cancel`).then(r => r.data),
};
```

- [ ] **Step 2: 写 useReturns hook**

```typescript
// frontend/src/hooks/useReturns.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { returnApi } from '../services/api';

export function useReturns() {
  return useQuery({ queryKey: ['returns'], queryFn: returnApi.list });
}

export function useReturnDetail(id: number | null) {
  return useQuery({
    queryKey: ['returns', id],
    queryFn: () => returnApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateReturn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: returnApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['returns'] }),
  });
}

export function useCancelReturn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: returnApi.cancel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['returns'] }),
  });
}
```

- [ ] **Step 3: 重写 ReturnsPage**

```tsx
// frontend/src/pages/ReturnsPage.tsx
import { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { ItemRowEditor } from '../components/ui/ItemRowEditor';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderFormModal } from '../components/business/OrderFormModal';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import { returnApi, customerApi } from '../services/api';

interface ReturnItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_wasted: boolean;
}

const defaultForm = {
  customer_id: '' as number | string,
  source_type: '' as string,
  source_order_id: '' as string,
  note: '',
};

const returnStatusConfig = {
  confirmed: { label: '已确认', variant: 'success' as const },
  cancelled: { label: '已撤销', variant: 'danger' as const },
};

export default function ReturnsPage() {
  // 新建
  const [formOpen, setFormOpen] = useState(false);
  const [header, setHeader] = useState(defaultForm);
  const [items, setItems] = useState<ReturnItem[]>([
    { product_id: 0, quantity: 1, unit_price: 0, is_wasted: false },
  ]);

  // 列表
  const [returns, setReturns] = useState<any[]>([]);

  // 详情
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  const loadReturns = useCallback(() => returnApi.list().then(setReturns), []);

  useEffect(() => {
    loadReturns();
    customerApi.list().then((data: any) =>
      setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name])))
    );
  }, [loadReturns]);

  const updateItem = (idx: number, field: keyof ReturnItem, value: number | boolean) =>
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (!header.customer_id || items.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await returnApi.create({
        customer_id: Number(header.customer_id),
        source_type: header.source_type || null,
        source_order_id: header.source_order_id ? Number(header.source_order_id) : null,
        items,
        note: header.note,
      });
      alert('退货成功');
      setFormOpen(false);
      setHeader(defaultForm);
      setItems([{ product_id: 0, quantity: 1, unit_price: 0, is_wasted: false }]);
      loadReturns();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    }
  };

  const openDetail = async (r: any) => {
    const d = await returnApi.get(r.id);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async () => {
    if (!detail || !confirm('确定撤销此退货单？将反向冲抵库存和退款')) return;
    await returnApi.cancel(detail.id);
    alert('已撤销');
    setDetailOpen(false);
    loadReturns();
  };

  const columns = [
    { key: 'id', title: '#', render: (r: any) => `#${r.id}` },
    { key: 'customer_name', title: '客户' },
    { key: 'items_summary', title: '品项' },
    {
      key: 'total_refund', title: '退款金额',
      render: (r: any) => `¥${r.total_refund.toFixed(2)}`,
    },
    {
      key: 'status', title: '状态',
      render: (r: any) => <StatusBadge status={r.status} config={returnStatusConfig} />,
    },
    { key: 'created_at', title: '日期', render: (r: any) => r.created_at?.slice(0, 10) },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">退货管理</h2>
        <Button onClick={() => setFormOpen(true)}>+ 新建退货</Button>
      </div>

      <OrderListTable
        columns={columns}
        data={returns}
        rowKey={(r) => r.id}
        onRowClick={openDetail}
      />

      <OrderFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="新建退货单"
        onSubmit={handleSubmit}
        submitLabel="提交退货"
      >
        <div className="space-y-3">
          <CustomerSelect value={header.customer_id} onChange={(v) => setHeader({ ...header, customer_id: v })} />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={header.source_type}
              onChange={(e) => setHeader({ ...header, source_type: e.target.value })}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">不关联来源</option>
              <option value="delivery">送货单</option>
              <option value="retail">零售单</option>
              <option value="subscription">订奶单</option>
            </select>
            <Input
              placeholder="来源单号"
              value={header.source_order_id}
              onChange={(e) => setHeader({ ...header, source_order_id: e.target.value })}
            />
          </div>
          <ItemRowEditor
            items={items}
            onUpdate={updateItem}
            onProductChange={(idx, pid) => {
              updateItem(idx, 'product_id', pid);
              if (pid && header.customer_id) {
                customerApi.resolvePrice(Number(header.customer_id), pid)
                  .then(({ price }) => updateItem(idx, 'unit_price', price))
                  .catch(() => {});
              }
            }}
            onRemove={(idx) => setItems(items.filter((_, i) => i !== idx))}
            onAdd={() => setItems([...items, { product_id: 0, quantity: 1, unit_price: 0, is_wasted: false }])}
          >
            {(item, idx) => (
              <label className="flex items-center gap-1 text-xs pb-2">
                <input
                  type="checkbox"
                  checked={item.is_wasted}
                  onChange={(e) => updateItem(idx, 'is_wasted', e.target.checked)}
                />
                报废
              </label>
            )}
          </ItemRowEditor>
          <Input placeholder="备注" value={header.note}
            onChange={(e) => setHeader({ ...header, note: e.target.value })} />
        </div>
      </OrderFormModal>

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`退货单 #${detail?.id}`}
        headerInfo={
          <>
            <div>客户: {detail?.customer_name}</div>
            {detail?.source_type && (
              <div>来源: {detail.source_type} #{detail.source_order_id}</div>
            )}
            <div>退款: ¥{detail?.total_refund?.toFixed(2)}</div>
          </>
        }
        items={detail?.items || []}
        status={detail?.status}
        statusConfig={returnStatusConfig}
      >
        {detail?.status === 'confirmed' && (
          <Button size="sm" variant="danger" onClick={handleCancel}>撤销</Button>
        )}
      </OrderDetailModal>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/hooks/useReturns.ts frontend/src/pages/ReturnsPage.tsx
git commit -m "feat: ReturnsPage 表格+弹窗+撤销，接入共享组件"
```

---

### Task 13: 改造 WastagePage

**Files:**
- Modify: `frontend/src/pages/WastagePage.tsx`

- [ ] **Step 1: 重写 WastagePage**

关键差异点（其余骨架跟 ReturnsPage 一致）：

**新建表单：无客户选择器，损耗原因下拉作为 ItemRowEditor slot**

```tsx
// 表单头字段只有 note，没有客户
const [note, setNote] = useState('');
const [items, setItems] = useState<WastageItem[]>([
  { product_id: 0, quantity: 1, reason: 'expired' },
]);

// ItemRowEditor 的 slot 是原因下拉
<ItemRowEditor ...>
  {(item, idx) => (
    <select
      value={item.reason}
      onChange={(e) => updateItem(idx, 'reason', e.target.value)}
      className="border rounded px-2 py-1 text-sm"
    >
      <option value="expired">过期</option>
      <option value="damaged">破损</option>
      <option value="self_consumed">自喝</option>
    </select>
  )}
</ItemRowEditor>
```

**列表 columns：**

```tsx
const columns = [
  { key: 'id', title: '#', render: (r: any) => `#${r.id}` },
  { key: 'items_summary', title: '品项' },
  { key: 'reasons', title: '原因', render: (r: any) => r.reasons?.join('、') },
  { key: 'status', title: '状态', render: (r: any) => <StatusBadge status={r.status} config={statusConfig} /> },
  { key: 'created_at', title: '日期', render: (r: any) => r.created_at?.slice(0, 10) },
];
```

**详情 headerInfo：**只显示备注和日期，无客户信息。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/WastagePage.tsx
git commit -m "feat: WastagePage 表格+弹窗+撤销，接入共享组件"
```

---

### Task 14: 改造 SalesPage

**Files:**
- Modify: `frontend/src/pages/SalesPage.tsx`

销售已有 retail_orders + detail/cancel API（上期做完）。改动：
- 列表从 div 列表变成 `OrderListTable` 表格
- 新建改成 `OrderFormModal`
- 加详情弹窗

- [ ] **Step 1: 改造 SalesPage**

**列表 columns（关键差异：已收款/未收款/已撤销 三种状态）：**

```tsx
const saleStatusConfig = {
  confirmed: { label: '已收款', variant: 'success' as const },   // paid=true 用此
  unpaid: { label: '未收款', variant: 'warning' as const },      // paid=false 用此
  cancelled: { label: '已撤销', variant: 'danger' as const },
};

const columns = [
  { key: 'customer_name', title: '客户' },
  { key: 'items_summary', title: '品项' },
  { key: 'total_amount', title: '金额', render: (s: any) => `¥${s.total_amount.toFixed(2)}` },
  {
    key: 'status', title: '状态',
    render: (s: any) => {
      if (s.status === 'cancelled') return <StatusBadge status="cancelled" config={saleStatusConfig} />;
      return <StatusBadge status={s.paid ? 'confirmed' : 'unpaid'} config={saleStatusConfig} />;
    },
  },
  { key: 'created_at', title: '日期', render: (s: any) => s.created_at?.slice(0, 10) },
];
```

**新建表单：**客户(可选) + ItemRowEditor(slot: 赠送勾选) + 已收款勾选 + 备注。

**详情弹窗：**headerInfo 显示客户/日期/状态/是否已收款。底部撤销按钮（仅 confirmed 状态）。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SalesPage.tsx
git commit -m "feat: SalesPage 表格+弹窗+撤销，接入共享组件"
```

---

### Task 15: 改造 PurchasesPage + DeliveriesPage

**Files:**
- Modify: `frontend/src/pages/PurchasesPage.tsx`
- Modify: `frontend/src/pages/DeliveriesPage.tsx`

两页已有列表表格和详情弹窗，改动较轻。

- [ ] **Step 1: PurchasesPage 改造**

**新建表单改 Modal：**把现有内联的 `<div className="bg-white rounded-lg border p-4 mb-6">` 整个迁入 `<OrderFormModal>`。接入 `ItemRowEditor`。进货无 slot。

**保留原有双按钮逻辑：**`OrderFormModal` 的 `submitLabel` 不够用，需要在 children 内自己写按钮：

```tsx
<OrderFormModal open={formOpen} onClose={...} title="新建进货单" onSubmit={() => {}} submitLabel="">
  {/* 供应商+日期 */}
  {/* ItemRowEditor 无 slot */}
  {/* 备注 */}
  <div className="flex gap-2 pt-2 border-t">
    <Button variant="secondary" onClick={() => handleSubmit('draft')}>保存草稿</Button>
    <Button onClick={() => handleSubmit('confirmed')}>确认入库</Button>
    <Button variant="secondary" onClick={() => setFormOpen(false)}>取消</Button>
  </div>
</OrderFormModal>
```

**接入 StatusBadge：**`StatusBadge status={o.status} config={purchaseStatusConfig}`。列表接入 `OrderListTable`，rowKey 用 `o.id`。

- [ ] **Step 2: DeliveriesPage 改造**

**新建表单改 Modal + ItemRowEditor(slot: 赠送勾选)：**

```tsx
<ItemRowEditor ... onlyInStock>
  {(item, idx) => (
    <label className="flex items-center gap-1 text-xs pb-2">
      <input type="checkbox" checked={item.is_promo} onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)} />
      赠送
    </label>
  )}
</ItemRowEditor>
```

**详情弹窗接入 OrderDetailModal：**保留现有结算/换货 Modal 和逻辑，headerInfo 显示客户/总金额/已付/未付。底部按钮：结算 + 换货。换货 Modal 完全不动。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PurchasesPage.tsx frontend/src/pages/DeliveriesPage.tsx
git commit -m "feat: PurchasesPage/DeliveriesPage 新建改Modal，接入共享组件"
```

---

### Task 16: 轻改 SubscriptionsPage

**Files:**
- Modify: `frontend/src/pages/SubscriptionsPage.tsx`

改动最小。
- [ ] **Step 1: 仅换列表渲染**

把现有的手写 `<table>` 换成 `OrderListTable`：

```tsx
const subStatusConfig = {
  active: { label: '进行中', variant: 'success' as const },
  completed: { label: '已完成', variant: 'default' as const },
  cancelled: { label: '已取消', variant: 'danger' as const },
};

const columns = [
  { key: 'id', title: '#', render: (o: any) => `#${o.id}` },
  { key: 'customer_name', title: '客户', render: (o: any) => customerNames[o.customer_id] || '' },
  { key: 'paid_amount', title: '实付金额', render: (o: any) => `¥${o.paid_amount}` },
  { key: 'remaining_amount', title: '剩余金额', render: (o: any) => `¥${o.remaining_amount}` },
  { key: 'status', title: '状态', render: (o: any) => <StatusBadge status={o.status} config={subStatusConfig} /> },
  { key: 'actions', title: '操作', render: (o: any) => (
    <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); navigate(`/subscriptions/${o.id}`); }}>详情</Button>
  )},
];
```

**新建表单不动**（订奶的创建是单个金额+客户，不是品项行模式，不适合 ItemRowEditor）。

**详情页保持独立路由** `/subscriptions/:id`。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SubscriptionsPage.tsx
git commit -m "feat: SubscriptionsPage 列表接入 OrderListTable + StatusBadge"
```

---

### Task 17: 全量回归测试

- [ ] **后端测试**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: 全部 PASS（含已有的 purchase/delivery/sale/exchange 测试 + 新增的 return/wastage 测试）

- [ ] **前端 typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **手动验证清单**

1. 退货页：新建 → 列表出现 → 点行看详情 → 撤销
2. 损耗页：新建 → 列表出现 → 点行看详情 → 撤销
3. 销售页：新建 → 列表表格展示 → 点行看详情 → 撤销
4. 进货页：新建弹窗 → 列表 → 详情弹窗 → 确认/撤销
5. 送货页：新建弹窗 → 列表 → 详情弹窗 → 结算/换货
6. 订奶页：列表正常 → 详情页独立路由正常

- [ ] **Commit**

```bash
git commit -m "chore: 全量回归验证通过"
```
