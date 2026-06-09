# 店铺库存与资金流水 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入 Store 维度 + 盘点单，实现店铺级库存和资金流水追踪，同时将 StockMovement 和 Transaction 从多外键改为多态引用。

**Architecture:** Store 独立模型关联 Customer，StockMovement 和 Transaction 改用 source_type/source_id 替代具体单据外键，新增强回调 customer_id 和 store_id 缓存查询维度。盘点单确认时自动计算销量并生成库存变动和资金流水。

**Tech Stack:** Python/FastAPI + SQLAlchemy + SQLite, React/TypeScript + Zustand

---

### Task 1: Store 模型 + InventoryCheck 模型

**Files:**
- Create: `backend/app/models/store.py`
- Create: `backend/app/models/inventory_check.py`
- Create: `backend/app/models/__init__.py` (update imports)

- [ ] **Step 1: 创建 Store 模型**

```python
# backend/app/models/store.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    address = Column(String(200), default="")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 创建 InventoryCheck 模型**

```python
# backend/app/models/inventory_check.py
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), unique=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    check_date = Column(Date, default=date.today)
    status = Column(String(20), default="confirmed")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)


class InventoryCheckItem(Base):
    __tablename__ = "inventory_check_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(Integer, ForeignKey("inventory_checks.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    actual_quantity = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("check_id", "product_id", name="uq_check_product"),
    )
```

- [ ] **Step 3: 更新 models/__init__.py 导入**

```python
# 在 backend/app/models/__init__.py 末尾追加
from app.models.store import Store
from app.models.inventory_check import InventoryCheck, InventoryCheckItem
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/store.py backend/app/models/inventory_check.py backend/app/models/__init__.py
git commit -m "feat: add Store and InventoryCheck models"
```

---

### Task 2: 改造 StockMovement 模型

**Files:**
- Modify: `backend/app/models/stock_movement.py`

- [ ] **Step 1: 重写 StockMovement 模型**

```python
# backend/app/models/stock_movement.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    direction = Column(String(10), nullable=False)
    reason = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    source_type = Column(String(20), nullable=True)
    source_id = Column(Integer, nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/models/stock_movement.py
git commit -m "refactor: StockMovement 改用 source_type/source_id 多态引用"
```

---

### Task 3: 改造 Transaction 模型

**Files:**
- Modify: `backend/app/models/transaction.py`

- [ ] **Step 1: 重写 Transaction 模型**

```python
# backend/app/models/transaction.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    category = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    source_type = Column(String(20), nullable=True)
    source_id = Column(Integer, nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/models/transaction.py
git commit -m "refactor: Transaction 改用 source_type/source_id 多态引用"
```

---

### Task 4: Delivery 模型加 store_id

**Files:**
- Modify: `backend/app/models/delivery.py`

- [ ] **Step 1: 加 store_id 列**

```python
# backend/app/models/delivery.py — 在 customer_id 下方加一行
store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
```

完整文件：
```python
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    delivery_date = Column(Date, default=date.today)
    status = Column(String(20), default="pending")
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/models/delivery.py
git commit -m "feat: Delivery 模型加 store_id"
```

---

### Task 5: 数据库迁移

**Files:**
- Create: `backend/alembic/versions/xxxx_store_and_source_refactor.py`

- [ ] **Step 1: 创建迁移文件**

先看看最新迁移的 revision：

```bash
cd backend && alembic heads
```

然后生成新的迁移文件：

```bash
cd backend && alembic revision --autogenerate -m "store_and_source_refactor"
```

- [ ] **Step 2: 检查自动生成的迁移，补充数据迁移逻辑**

自动生成会创建 stores、inventory_checks、inventory_check_items 表，删旧列加新列。需要手动在 migration 中加数据回填逻辑：

```python
# 在 upgrade() 中，drop_column 之前加：
# 回填 stock_movements 的 source_type/source_id
op.execute("""
    UPDATE stock_movements SET source_type='delivery', source_id=delivery_id
    WHERE delivery_id IS NOT NULL
""")
op.execute("""
    UPDATE stock_movements SET source_type='purchase', source_id=purchase_order_id
    WHERE purchase_order_id IS NOT NULL
""")
op.execute("""
    UPDATE stock_movements SET source_type='retail', source_id=retail_order_id
    WHERE retail_order_id IS NOT NULL
""")
op.execute("""
    UPDATE stock_movements SET source_type='return', source_id=return_order_id
    WHERE return_order_id IS NOT NULL
""")
op.execute("""
    UPDATE stock_movements SET source_type='wastage', source_id=wastage_order_id
    WHERE wastage_order_id IS NOT NULL
""")
op.execute("""
    UPDATE stock_movements SET source_type='subscription', source_id=subscription_order_id
    WHERE subscription_order_id IS NOT NULL
""")

# 同理回填 transactions
op.execute("""
    UPDATE transactions SET source_type='delivery', source_id=delivery_id
    WHERE delivery_id IS NOT NULL
""")
op.execute("""
    UPDATE transactions SET source_type='purchase', source_id=purchase_order_id
    WHERE purchase_order_id IS NOT NULL
""")
op.execute("""
    UPDATE transactions SET source_type='retail', source_id=retail_order_id
    WHERE retail_order_id IS NOT NULL
""")
op.execute("""
    UPDATE transactions SET source_type='return', source_id=return_order_id
    WHERE return_order_id IS NOT NULL
""")
op.execute("""
    UPDATE transactions SET source_type='subscription', source_id=subscription_order_id
    WHERE subscription_order_id IS NOT NULL
""")
```

- [ ] **Step 3: 运行迁移**

```bash
cd backend && alembic upgrade head
```

预期：无报错，表结构更新成功。

- [ ] **Step 4: 提交**

```bash
git add backend/alembic/versions/
git commit -m "feat: migration — Store + InventoryCheck + source 多态改造"
```

---

### Task 6: 改造 StockMovementRepository

**Files:**
- Modify: `backend/app/repositories/stock_movement_repo.py`

- [ ] **Step 1: 更新查询方法，废弃按单据类型查询的方法，改成通用 source 查询**

```python
# backend/app/repositories/stock_movement_repo.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.stock_movement import StockMovement


class StockMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, movements: List[dict]) -> List[StockMovement]:
        objs = [StockMovement(**m) for m in movements]
        self.db.add_all(objs)
        self.db.flush()
        return objs

    def get_by_source(self, source_type: str, source_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
        ).all()

    def get_by_source_reason(self, source_type: str, source_id: int, reason: str) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
            StockMovement.reason == reason,
        ).all()

    def get_by_source_exclude_reason(self, source_type: str, source_id: int, exclude_reason: str) -> List[StockMovement]:
        """查询某单据的流水，排除特定 reason（如排除 cancel）"""
        return self.db.query(StockMovement).filter(
            StockMovement.source_type == source_type,
            StockMovement.source_id == source_id,
            StockMovement.reason != exclude_reason,
        ).all()

    def get_inventory(self) -> list:
        """按 product_id 汇总总仓库存（store_id IS NULL）"""
        return (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id.is_(None))
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ) != 0
            )
            .all()
        )

    def get_inventory_by_store(self, store_id: int) -> list:
        """按 product_id 汇总店铺库存"""
        return (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id == store_id)
            .group_by(StockMovement.product_id)
            .having(
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ) != 0
            )
            .all()
        )

    def get_store_receive_between(self, store_id: int, product_id: int, from_date, to_date) -> int:
        """两次盘点之间的店铺收货总量"""
        result = (
            self.db.query(func.sum(StockMovement.quantity))
            .filter(
                StockMovement.store_id == store_id,
                StockMovement.product_id == product_id,
                StockMovement.reason == "store_receive",
                StockMovement.created_at >= from_date,
                StockMovement.created_at < to_date,
            )
            .scalar()
        )
        return result or 0

    def validate_stock(self, items: list):
        """库存校验：按 product_id 汇总检查总仓库存"""
        inventory = {
            r.product_id: r.stock
            for r in self.get_inventory()
        }
        needed: dict[int, int] = {}
        for item in items:
            pid = item.product_id if hasattr(item, 'product_id') else item["product_id"]
            qty = item.quantity if hasattr(item, 'quantity') else item["quantity"]
            needed[pid] = needed.get(pid, 0) + qty
        for pid, qty in needed.items():
            stock = inventory.get(pid, 0)
            if stock < qty:
                raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {qty}")

    def list_all(self):
        return self.db.query(StockMovement).order_by(StockMovement.created_at.desc()).all()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/repositories/stock_movement_repo.py
git commit -m "refactor: StockMovementRepository 适配 source 多态 + store 查询"
```

---

### Task 7: 改造 TransactionRepository

**Files:**
- Modify: `backend/app/repositories/transaction_repo.py`

- [ ] **Step 1: 更新查询方法**

```python
# backend/app/repositories/transaction_repo.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Transaction:
        txn = Transaction(**kwargs)
        self.db.add(txn)
        self.db.flush()
        return txn

    def get_by_source(self, source_type: str, source_id: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.source_type == source_type,
            Transaction.source_id == source_id,
        ).all()

    def get_ar_by_customer(self, customer_id: int) -> float:
        result = self.db.query(
            func.sum(
                case(
                    (Transaction.category.in_(["distribution", "retail", "subscription"]), Transaction.amount),
                    (Transaction.category == "payment", -Transaction.amount),
                    (Transaction.category == "refund", -Transaction.amount),
                    else_=0,
                )
            )
        ).filter(Transaction.customer_id == customer_id).scalar()
        return result or 0.0

    def get_receivables(self) -> list:
        case_expr = case(
            (Transaction.category.in_(["distribution", "retail", "subscription"]), Transaction.amount),
            (Transaction.category == "payment", -Transaction.amount),
            (Transaction.category == "refund", -Transaction.amount),
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

    def get_amounts_by_deliveries(self, delivery_ids: list[int]) -> dict[int, dict]:
        if not delivery_ids:
            return {}
        rows = (
            self.db.query(
                Transaction.source_id,
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                Transaction.source_type == "delivery",
                Transaction.source_id.in_(delivery_ids),
            )
            .group_by(Transaction.source_id, Transaction.category)
            .all()
        )
        result: dict[int, dict] = {did: {"total_amount": 0.0, "paid_amount": 0.0} for did in delivery_ids}
        for row in rows:
            if row.category in ("distribution", "delivery", "delivery_cancel"):
                result[row.source_id]["total_amount"] += row.total
            elif row.category == "payment":
                result[row.source_id]["paid_amount"] += row.total
        for did, amounts in result.items():
            amounts["unpaid_amount"] = amounts["total_amount"] - amounts["paid_amount"]
        return result

    def list_all(self):
        return self.db.query(Transaction).order_by(Transaction.created_at.desc()).limit(200).all()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/repositories/transaction_repo.py
git commit -m "refactor: TransactionRepository 适配 source 多态"
```

---

### Task 8: 创建 StoreRepository + StoreService + Store API

**Files:**
- Create: `backend/app/repositories/store_repo.py`
- Create: `backend/app/services/store_service.py`
- Create: `backend/app/schemas/store.py`
- Create: `backend/app/api/stores.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: StoreRepository**

```python
# backend/app/repositories/store_repo.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.store import Store


class StoreRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Store:
        store = Store(**kwargs)
        self.db.add(store)
        self.db.flush()
        return store

    def get_by_id(self, store_id: int) -> Optional[Store]:
        return self.db.query(Store).filter(Store.id == store_id).first()

    def get_by_customer(self, customer_id: int) -> Optional[Store]:
        return self.db.query(Store).filter(Store.customer_id == customer_id).first()

    def list_all(self) -> List[Store]:
        return self.db.query(Store).order_by(Store.name).all()

    def update(self, store_id: int, **kwargs) -> Optional[Store]:
        store = self.get_by_id(store_id)
        if not store:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(store, k, v)
        self.db.flush()
        return store
```

- [ ] **Step 2: StoreSchema**

```python
# backend/app/schemas/store.py
from pydantic import BaseModel
from typing import Optional


class StoreCreate(BaseModel):
    name: str
    customer_id: Optional[int] = None
    address: str = ""


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[int] = None
    address: Optional[str] = None
    status: Optional[str] = None


class StoreOut(BaseModel):
    id: int
    name: str
    customer_id: int | None
    customer_name: str
    address: str
    status: str
    created_at: str

    class Config:
        from_attributes = True
```

- [ ] **Step 3: StoreService**

```python
# backend/app/services/store_service.py
from sqlalchemy.orm import Session
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreate, StoreUpdate
from app.models.customer import Customer


class StoreService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StoreRepository(db)

    def create(self, data: StoreCreate) -> dict:
        store = self.repo.create(
            name=data.name,
            customer_id=data.customer_id,
            address=data.address,
        )
        self.db.commit()
        return {"id": store.id, "name": store.name}

    def list_stores(self) -> list:
        stores = self.repo.list_all()
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        return [
            {
                "id": s.id,
                "name": s.name,
                "customer_id": s.customer_id,
                "customer_name": customers.get(s.customer_id, ""),
                "address": s.address,
                "status": s.status,
                "created_at": str(s.created_at),
            }
            for s in stores
        ]

    def get_store(self, store_id: int) -> dict | None:
        store = self.repo.get_by_id(store_id)
        if not store:
            return None
        customers = {c.id: c.name for c in self.db.query(Customer).all()}
        return {
            "id": store.id,
            "name": store.name,
            "customer_id": store.customer_id,
            "customer_name": customers.get(store.customer_id, ""),
            "address": store.address,
            "status": store.status,
            "created_at": str(store.created_at),
        }

    def update(self, store_id: int, data: StoreUpdate) -> dict:
        store = self.repo.update(store_id, **data.model_dump(exclude_none=True))
        if not store:
            raise ValueError("店铺不存在")
        self.db.commit()
        return {"id": store.id}
```

- [ ] **Step 4: Store API**

```python
# backend/app/api/stores.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.store_service import StoreService
from app.schemas.store import StoreCreate, StoreUpdate

router = APIRouter(prefix="/api/stores", tags=["stores"])


def get_store_service(db: Session = Depends(get_db)):
    return StoreService(db)


@router.get("")
def list_stores(svc: StoreService = Depends(get_store_service)):
    return svc.list_stores()


@router.post("", status_code=201)
def create_store(data: StoreCreate, svc: StoreService = Depends(get_store_service)):
    try:
        return svc.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{store_id}")
def get_store(store_id: int, svc: StoreService = Depends(get_store_service)):
    detail = svc.get_store(store_id)
    if not detail:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return detail


@router.put("/{store_id}")
def update_store(store_id: int, data: StoreUpdate, svc: StoreService = Depends(get_store_service)):
    try:
        return svc.update(store_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 5: 注册路由**

在 `backend/app/api/router.py` 中加：
```python
from app.api import stores
api_router.include_router(stores.router)
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/repositories/store_repo.py backend/app/services/store_service.py backend/app/schemas/store.py backend/app/api/stores.py backend/app/api/router.py
git commit -m "feat: Store CRUD — model + repo + service + api"
```

---

### Task 9: 适配 DeliveryService（核心改造）

**Files:**
- Modify: `backend/app/services/delivery_service.py`
- Modify: `backend/app/schemas/delivery.py`

- [ ] **Step 1: 更新 create_delivery — 双记库存 + source_type/source_id**

```python
# backend/app/services/delivery_service.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.store_repo import StoreRepository
from app.models.delivery import Delivery
from app.schemas.delivery import DeliveryCreate, ExchangeCreate


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.store_repo = StoreRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, Delivery, "DO")

    def list_with_amounts(self, customer_id=None, status=None):
        deliveries = self.delivery_repo.list_all(customer_id, status)
        if not deliveries:
            return []
        ids = [d.id for d in deliveries]
        amounts = self.txn_repo.get_amounts_by_deliveries(ids)
        return [
            {
                "id": d.id,
                "order_number": d.order_number,
                "customer_id": d.customer_id,
                "delivery_date": str(d.delivery_date),
                "status": d.status,
                "note": d.note,
                "subscription_order_id": d.subscription_order_id,
                "created_at": str(d.created_at) if d.created_at else None,
                "total_amount": amounts[d.id]["total_amount"],
                "paid_amount": amounts[d.id]["paid_amount"],
                "unpaid_amount": amounts[d.id]["unpaid_amount"],
            }
            for d in deliveries
        ]

    def create_delivery(self, data: DeliveryCreate):
        self.stock_repo.validate_stock(data.items)

        # 查客户关联的店铺
        store = self.store_repo.get_by_customer(data.customer_id)

        delivery = self.delivery_repo.create(
            customer_id=data.customer_id,
            delivery_date=data.delivery_date,
            status="pending",
            subscription_order_id=data.subscription_order_id,
            store_id=store.id if store else None,
            note=data.note,
        )
        delivery.order_number = self._next_order_number()

        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_price
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "distribution",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery.id,
            })

        # 若客户有店铺，多记一条店铺入库
        if store:
            for item in data.items:
                movements.append({
                    "product_id": item.product_id,
                    "direction": "in",
                    "reason": "store_receive",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "source_type": "delivery",
                    "source_id": delivery.id,
                    "store_id": store.id,
                    "customer_id": data.customer_id,
                })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="distribution",
                amount=total,
                source_type="delivery",
                source_id=delivery.id,
            )

        delivery.status = "delivered"
        self.db.commit()
        return {"id": delivery.id, "total": total}

    def get_delivery_detail(self, delivery_id: int):
        from app.models.product import Product

        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            return None
        movements = self.stock_repo.get_by_source("delivery", delivery_id)
        transactions = self.txn_repo.get_by_source("delivery", delivery_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}

        delivery_total = sum(t.amount for t in transactions if t.category in ("distribution", "delivery"))
        delivery_cancel_total = sum(t.amount for t in transactions if t.category == "delivery_cancel")
        paid_total = sum(t.amount for t in transactions if t.category == "payment")

        net = delivery_total + delivery_cancel_total

        exchange_movements = [m for m in movements if m.reason == "exchange"]
        groups: dict = {}
        for m in exchange_movements:
            groups.setdefault(m.created_at, []).append(m)
        exchanges = [
            {
                "created_at": str(ts),
                "return_items": [
                    {"product_id": m.product_id, "quantity": m.quantity, "unit_price": m.unit_price}
                    for m in ms if m.direction == "in"
                ],
                "new_items": [
                    {"product_id": m.product_id, "quantity": m.quantity, "unit_price": m.unit_price}
                    for m in ms if m.direction == "out"
                ],
            }
            for ts, ms in groups.items()
        ]

        return {
            "id": delivery.id,
            "order_number": delivery.order_number,
            "customer_id": delivery.customer_id,
            "delivery_date": str(delivery.delivery_date),
            "status": delivery.status,
            "note": delivery.note,
            "items": [
                {
                    "product_id": m.product_id,
                    "product_name": products.get(m.product_id, ""),
                    "quantity": m.quantity,
                    "unit_price": m.unit_price or 0,
                }
                for m in movements if m.reason != "exchange"
            ],
            "total_amount": net,
            "paid_amount": paid_total,
            "unpaid_amount": net - paid_total,
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in transactions
            ],
            "exchanges": exchanges,
        }

    def exchange(self, delivery_id: int, data: ExchangeCreate):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        return_total = sum(item.quantity * item.unit_price for item in data.return_items)
        new_total = sum(item.quantity * item.unit_price for item in data.new_items)

        if abs(return_total - new_total) > 0.005:
            raise ValueError("换货金额不一致，请走退货结算后重新开单")

        now = datetime.now()

        return_movements = []
        for item in data.return_items:
            return_movements.append({
                "product_id": item.product_id,
                "direction": "in",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery_id,
                "created_at": now,
            })
        self.stock_repo.bulk_create(return_movements)

        self.stock_repo.validate_stock(data.new_items)
        new_movements = []
        for item in data.new_items:
            new_movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "exchange",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "source_type": "delivery",
                "source_id": delivery_id,
                "created_at": now,
            })
        self.stock_repo.bulk_create(new_movements)

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/delivery_service.py
git commit -m "refactor: DeliveryService 适配 source 多态 + 双记店铺库存"
```

---

### Task 10: 适配 PurchaseService

**Files:**
- Modify: `backend/app/services/purchase_service.py`

共 6 处改动：

- [ ] **Step 1: `_confirm_items()` 第 97 行 — 库存变动 dict**

```python
# 旧: "purchase_order_id": order_id,
# 新:
"source_type": "purchase", "source_id": order_id,
```

- [ ] **Step 2: `_confirm_items()` 第 105–110 行 — 资金流水**

```python
# 旧: purchase_order_id=order_id,
# 新:
source_type="purchase", source_id=order_id,
```

- [ ] **Step 3: `_confirm_items()` 第 103 行 — 查 order 对象**

`self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()` 不变（查的是订单头，不是流水）。

- [ ] **Step 4: `cancel_order()` 第 126 行 — 查原始库存记录**

```python
# 旧: original_items = self.stock_repo.get_by_purchase_order(order_id)
# 新:
original_items = self.stock_repo.get_by_source("purchase", order_id)
```

- [ ] **Step 5: `cancel_order()` 第 127–129 行 — 库存校验**

```python
# 旧: inventory = {r.product_id: r.stock for r in self.stock_repo.get_inventory()}
# 新: get_inventory() 内部已过滤 store_id IS NULL，无需改动
```

- [ ] **Step 6: `cancel_order()` 第 136–153 行 — 反向冲抵库存和账务 dict**

```python
# 旧: "purchase_order_id": order_id,
# 新: "source_type": "purchase", "source_id": order_id,

# 旧: purchase_order_id=order_id,
# 新: source_type="purchase", source_id=order_id,
```

- [ ] **Step 7: `import_confirm()` 第 315–326 行 — 库存变动和交易**

```python
# 旧: "purchase_order_id": order.id,
# 新: "source_type": "purchase", "source_id": order.id,

# 旧: self.txn_repo.create(supplier_id=sid, category="purchase", amount=total, purchase_order_id=order.id)
# 新:
self.txn_repo.create(supplier_id=sid, category="purchase", amount=total, source_type="purchase", source_id=order.id)
```

- [ ] **Step 8: `get_purchase_detail()` 第 191 行 — 查明细**

```python
# 旧: items = self.stock_repo.get_by_purchase_order(order_id)
# 新:
items = self.stock_repo.get_by_source_reason("purchase", order_id, "purchase")
```

- [ ] **Step 9: 提交**

```bash
git add backend/app/services/purchase_service.py
git commit -m "refactor: PurchaseService 适配 source 多态"
```

---

### Task 11: 适配 SaleService

**Files:**
- Modify: `backend/app/services/sale_service.py`

共 10 处改动，分布在一个文件 % 2 个方法中：

- [ ] **Step 1: `create_sale()` 第 39 行 — 库存变动 dict**

```python
# 旧: "retail_order_id": retail_order.id,
# 新:
"source_type": "retail", "source_id": retail_order.id,
```

- [ ] **Step 2: `create_sale()` 第 46–51 行 — retail 交易**

```python
# 旧: retail_order_id=retail_order.id,
# 新:
source_type="retail", source_id=retail_order.id,
```

- [ ] **Step 3: `create_sale()` 第 59–63 行 — cogs 交易**

```python
# 旧: retail_order_id=retail_order.id,
# 新:
source_type="retail", source_id=retail_order.id,
```

- [ ] **Step 4: `create_sale()` 第 68–72 行 — payment 交易**

```python
# 旧: retail_order_id=retail_order.id,
# 新:
source_type="retail", source_id=retail_order.id,
```

- [ ] **Step 5: `list_sales()` 第 89–96 行 — 查 StockMovement**

```python
# 旧:
movements = (
    self.db.query(StockMovement)
    .filter(
        StockMovement.retail_order_id.in_(order_ids),
        StockMovement.reason == "retail",
    )
    .all()
)
# 新:
movements = (
    self.db.query(StockMovement)
    .filter(
        StockMovement.source_type == "retail",
        StockMovement.source_id.in_(order_ids),
        StockMovement.reason == "retail",
    )
    .all()
)
```

- [ ] **Step 6: `list_sales()` 第 98–103 行 — 查 paid 状态**

```python
# 旧:
paid_ids = {
    t.retail_order_id
    for t in self.db.query(Transaction).filter(
        Transaction.retail_order_id.in_(order_ids),
        Transaction.category == "payment",
    ).all()
}
# 新:
paid_ids = {
    t.source_id
    for t in self.db.query(Transaction).filter(
        Transaction.source_type == "retail",
        Transaction.source_id.in_(order_ids),
        Transaction.category == "payment",
    ).all()
}
```

- [ ] **Step 7: `list_sales()` 第 109–110 行 — 按 retail_order_id 分组**

```python
# 旧: order_items.setdefault(m.retail_order_id, []).append(m)
#     order_totals[m.retail_order_id] = ...
# 新:
order_items.setdefault(m.source_id, []).append(m)
order_totals[m.source_id] = order_totals.get(m.source_id, 0) + m.quantity * m.unit_price
```

- [ ] **Step 8: `get_sale_detail()` 第 143 行 — 查明细**

```python
# 旧: items = self.stock_repo.get_by_retail_order(order_id)
# 新:
items = self.stock_repo.get_by_source_reason("retail", order_id, "retail")
```

- [ ] **Step 9: `get_sale_detail()` 第 147–152 行 — 查 paid**

```python
# 旧:
paid = (
    self.db.query(Transaction).filter(
        Transaction.retail_order_id == order_id,
        Transaction.category == "payment",
    ).first()
    is not None
)
# 新:
paid = (
    self.db.query(Transaction).filter(
        Transaction.source_type == "retail",
        Transaction.source_id == order_id,
        Transaction.category == "payment",
    ).first()
    is not None
)
```

- [ ] **Step 10: `mark_paid()` 第 186–213 行 — 3 处 Transaction 查询**

```python
# 第 188 行 — 查已有 payment:
# 旧: Transaction.retail_order_id == order_id,
# 新: Transaction.source_type == "retail", Transaction.source_id == order_id,

# 第 198–200 行 — 查 income:
# 旧: Transaction.retail_order_id == order_id,
# 新: Transaction.source_type == "retail", Transaction.source_id == order_id,

# 第 208–212 行 — 创建 payment:
# 旧: retail_order_id=order_id,
# 新: source_type="retail", source_id=order_id,
```

- [ ] **Step 11: `cancel_sale()` 第 225 行 — 查原始出库**

```python
# 旧: original_items = self.stock_repo.get_by_retail_order(order_id)
# 新:
original_items = self.stock_repo.get_by_source_reason("retail", order_id, "retail")
```

- [ ] **Step 12: `cancel_sale()` 第 229–234 行 — 反向冲抵库存 dict**

```python
# 旧: "retail_order_id": order_id,
# 新: "source_type": "retail", "source_id": order_id,
```

- [ ] **Step 13: `cancel_sale()` 第 241–243 行 — 查原交易**

```python
# 旧:
original_txns = (
    self.db.query(Transaction)
    .filter(Transaction.retail_order_id == order_id)
    .all()
)
# 新:
original_txns = (
    self.db.query(Transaction)
    .filter(Transaction.source_type == "retail", Transaction.source_id == order_id)
    .all()
)
```

- [ ] **Step 14: `cancel_sale()` 第 247–251 行 — 反向冲抵交易**

```python
# 旧: retail_order_id=order_id,
# 新: source_type="retail", source_id=order_id,
```

- [ ] **Step 15: 提交**

```bash
git add backend/app/services/sale_service.py
git commit -m "refactor: SaleService 适配 source 多态"
```

---

### Task 12: 适配 ReturnService

**Files:**
- Modify: `backend/app/services/return_service.py`

共 8 处改动：

- [ ] **Step 1: `create_return()` 第 33–39 行 — 库存变动 dict**

```python
# 旧: "return_order_id": order.id,
# 新: "source_type": "return", "source_id": order.id,
```

- [ ] **Step 2: `create_return()` 第 45–49 行 — 退款交易**

```python
# 旧: return_order_id=order.id,
# 新: source_type="return", source_id=order.id,
```

- [ ] **Step 3: `list_returns()` 第 65–72 行 — 查 StockMovement**

```python
# 旧:
movements = (
    self.db.query(StockMovement)
    .filter(
        StockMovement.return_order_id.in_(order_ids),
        StockMovement.reason == "return",
    )
    .all()
)
# 新:
movements = (
    self.db.query(StockMovement)
    .filter(
        StockMovement.source_type == "return",
        StockMovement.source_id.in_(order_ids),
        StockMovement.reason == "return",
    )
    .all()
)
```

- [ ] **Step 4: `list_returns()` 第 75–78 行 — 查退款金额**

```python
# 旧:
refunds = {
    t.return_order_id: t.amount
    for t in self.db.query(Transaction).filter(
        Transaction.return_order_id.in_(order_ids),
        Transaction.category == "refund",
    ).all()
}
# 新:
refunds = {
    t.source_id: t.amount
    for t in self.db.query(Transaction).filter(
        Transaction.source_type == "return",
        Transaction.source_id.in_(order_ids),
        Transaction.category == "refund",
    ).all()
}
```

- [ ] **Step 5: `list_returns()` 第 84 行 — 按 return_order_id 分组**

```python
# 旧: order_items.setdefault(m.return_order_id, []).append(m)
# 新:
order_items.setdefault(m.source_id, []).append(m)
```

- [ ] **Step 6: `get_return_detail()` 第 117 行 — 查明细**

```python
# 旧: items = self.stock_repo.get_by_return_order(order_id)
# 新:
items = self.stock_repo.get_by_source("return", order_id)
```

- [ ] **Step 7: `get_return_detail()` 第 122–127 行 — 查 refund 交易**

```python
# 旧:
refunds = (
    self.db.query(Transaction)
    .filter(
        Transaction.return_order_id == order_id,
        Transaction.category == "refund",
    ).all()
)
# 新:
refunds = (
    self.db.query(Transaction)
    .filter(
        Transaction.source_type == "return",
        Transaction.source_id == order_id,
        Transaction.category == "refund",
    ).all()
)
```

- [ ] **Step 8: `cancel_return()` 第 163 行 — 查原始记录**

```python
# 旧: original_items = self.stock_repo.get_by_return_order(order_id)
# 新:
original_items = self.stock_repo.get_by_source("return", order_id)
```

- [ ] **Step 9: `cancel_return()` 第 171–180 行 — 反向冲抵库存 dict**

```python
# 旧: "return_order_id": order_id,
# 新: "source_type": "return", "source_id": order_id,
```

- [ ] **Step 10: `cancel_return()` 第 184–188 行 — 查原交易**

```python
# 旧:
original_txns = (
    self.db.query(Transaction)
    .filter(Transaction.return_order_id == order_id)
    .all()
)
# 新:
original_txns = (
    self.db.query(Transaction)
    .filter(Transaction.source_type == "return", Transaction.source_id == order_id)
    .all()
)
```

- [ ] **Step 11: `cancel_return()` 第 190–194 行 — 反向冲抵交易**

```python
# 旧: return_order_id=order_id,
# 新: source_type="return", source_id=order_id,
```

- [ ] **Step 12: 提交**

```bash
git add backend/app/services/return_service.py
git commit -m "refactor: ReturnService 适配 source 多态"
```

---

### Task 13: 适配 WastageService + wastage API export

**Files:**
- Modify: `backend/app/services/wastage_service.py`
- Modify: `backend/app/api/wastage.py`

共 6 处改动：

- [ ] **Step 1: `create_wastage()` 第 43 行 — 库存变动 dict**

```python
# 旧: "wastage_order_id": order.id,
# 新: "source_type": "wastage", "source_id": order.id,
```

- [ ] **Step 2: `list_wastage()` 第 68–72 行 — 查 StockMovement**

```python
# 旧:
movements = (
    self.db.query(StockMovement)
    .filter(StockMovement.wastage_order_id.in_(order_ids))
    .all()
)
# 新:
movements = (
    self.db.query(StockMovement)
    .filter(
        StockMovement.source_type == "wastage",
        StockMovement.source_id.in_(order_ids),
    )
    .all()
)
```

- [ ] **Step 3: `list_wastage()` 第 76 行 — 按 wastage_order_id 分组**

```python
# 旧: order_items.setdefault(m.wastage_order_id, []).append(m)
# 新:
order_items.setdefault(m.source_id, []).append(m)
```

- [ ] **Step 4: `get_wastage_detail()` 第 109 行 — 查明细**

```python
# 旧: items = self.stock_repo.get_by_wastage_order(order_id)
# 新:
items = self.stock_repo.get_by_source("wastage", order_id)
```

- [ ] **Step 5: `cancel_wastage()` 第 141 行 — 查原始记录**

```python
# 旧: original_items = self.stock_repo.get_by_wastage_order(order_id)
# 新:
original_items = self.stock_repo.get_by_source("wastage", order_id)
```

- [ ] **Step 6: `cancel_wastage()` 第 143–149 行 — 反向冲抵库存 dict**

```python
# 旧: "wastage_order_id": order_id,
# 新: "source_type": "wastage", "source_id": order_id,
```

- [ ] **Step 7: `backend/app/api/wastage.py` `export_wastage()` 第 35–36 行**

```python
# 旧:
rows = db.query(StockMovement).join(WastageOrder).filter(
    StockMovement.wastage_order_id.isnot(None)
).order_by(StockMovement.created_at.desc()).all()
# 新:
rows = db.query(StockMovement).filter(
    StockMovement.source_type == "wastage"
).order_by(StockMovement.created_at.desc()).all()
```

- [ ] **Step 8: 提交**

```bash
git add backend/app/services/wastage_service.py backend/app/api/wastage.py
git commit -m "refactor: WastageService + wastage export 适配 source 多态"
```

---

### Task 14: 适配 SubscriptionService

**Files:**
- Modify: `backend/app/services/subscription_service.py`

共 5 处改动：

- [ ] **Step 1: `create_order()` 第 30–34 行 — 充值交易**

```python
# 旧: subscription_order_id=order.id,
# 新: source_type="subscription", source_id=order.id,
```

- [ ] **Step 2: `deduct()` 第 108–114 行 — 库存变动 dict**

```python
# 旧: "subscription_order_id": order_id,
# 新: "source_type": "subscription", "source_id": order_id,
```

- [ ] **Step 3: `deduct()` 第 120–124 行 — promo 交易**

```python
# 旧: subscription_order_id=order_id,
# 新: source_type="subscription", source_id=order_id,
```

- [ ] **Step 4: `deduct()` 第 128–132 行 — 收入交易**

```python
# 旧: subscription_order_id=order_id,
# 新: source_type="subscription", source_id=order_id,
```

- [ ] **Step 5: `deduct()` 第 135–139 行 — cogs 交易**

```python
# 旧: subscription_order_id=order_id,
# 新: source_type="subscription", source_id=order_id,
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/subscription_service.py
git commit -m "refactor: SubscriptionService 适配 source 多态"
```

---

### Task 15: 适配 SettlementService

**Files:**
- Modify: `backend/app/services/settlement_service.py`

共 2 处改动：

- [ ] **Step 1: `settle()` 第 17–21 行 — 创建 payment 交易**

```python
# 旧:
self.txn_repo.create(
    customer_id=delivery.customer_id,
    category="payment",
    amount=amount,
    delivery_id=delivery_id,
)
# 新:
self.txn_repo.create(
    customer_id=delivery.customer_id,
    category="payment",
    amount=amount,
    source_type="delivery", source_id=delivery_id,
)
```

- [ ] **Step 2: `batch_settle()` 第 41–45 行 — 批量创建 payment**

```python
# 旧:
self.txn_repo.create(
    customer_id=customer_id,
    category="payment",
    amount=item["amount"],
    delivery_id=item["delivery_id"],
)
# 新:
self.txn_repo.create(
    customer_id=customer_id,
    category="payment",
    amount=item["amount"],
    source_type="delivery", source_id=item["delivery_id"],
)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/settlement_service.py
git commit -m "refactor: SettlementService 适配 source 多态"
```

---

### Task 16: 适配 stock_ledger 和 transaction_ledger API

**Files:**
- Modify: `backend/app/api/stock_ledger.py`
- Modify: `backend/app/api/transaction_ledger.py`

- [ ] **Step 1: 更新 stock_ledger.py**

将 FK_MAP 改为 source_type 映射：

```python
# backend/app/api/stock_ledger.py
from datetime import date
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
from app.models.inventory_check import InventoryCheck

router = APIRouter(prefix="/api/stock-ledger", tags=["stock-ledger"])

_SOURCE_MODELS = {
    "purchase": PurchaseOrder,
    "retail": RetailOrder,
    "return": ReturnOrder,
    "wastage": WastageOrder,
    "delivery": Delivery,
    "subscription": SubscriptionOrder,
    "inventory_check": InventoryCheck,
}


def _order_number_map(db: Session, movements: list) -> dict:
    ids_by_type: dict[str, set] = {}
    for m in movements:
        if m.source_type and m.source_id:
            ids_by_type.setdefault(m.source_type, set()).add(m.source_id)

    result: dict[int, str] = {}
    for stype, ids in ids_by_type.items():
        model = _SOURCE_MODELS.get(stype)
        if not model:
            continue
        for row in db.query(model).filter(model.id.in_(ids)).all():
            for m in movements:
                if m.source_type == stype and m.source_id == row.id:
                    if row.order_number:
                        result[m.id] = row.order_number
    return result


@router.get("")
def list_stock_ledger(
    product_id: int | None = Query(None),
    store_id: int | None = Query(None),
    direction: str | None = Query(None),
    reason: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    order_number: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StockMovement).order_by(StockMovement.created_at.asc())

    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if store_id is not None:
        q = q.filter(StockMovement.store_id == store_id)
    if direction:
        q = q.filter(StockMovement.direction == direction)
    if reason:
        q = q.filter(StockMovement.reason == reason)
    if date_from:
        q = q.filter(StockMovement.created_at >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(StockMovement.created_at < date.fromisoformat(date_to))
    if order_number:
        filters = []
        for stype, model in _SOURCE_MODELS.items():
            matched = db.query(model.id).filter(model.order_number == order_number).all()
            if matched:
                ids = [row[0] for row in matched]
                filters.append(
                    (StockMovement.source_type == stype) & (StockMovement.source_id.in_(ids))
                )
        if filters:
            from sqlalchemy import or_
            q = q.filter(or_(*filters))
        else:
            q = q.filter(StockMovement.id == -1)

    movements = q.limit(500).all()
    if not movements:
        return []

    products = {p.id: p.name for p in db.query(Product).all()}
    order_numbers = _order_number_map(db, movements)

    balances: dict[int, dict] = {}  # product_id → {store_key: balance}，store_key=-1 代表总仓(NULL)
    rows = []
    for m in movements:
        key = m.product_id
        balances.setdefault(key, {})
        store_key = m.store_id if m.store_id is not None else -1
        balances[key].setdefault(store_key, 0)
        if m.direction == "in":
            balances[key][store_key] += m.quantity
        else:
            balances[key][store_key] -= m.quantity

        rows.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products.get(m.product_id, ""),
            "direction": m.direction,
            "quantity": m.quantity,
            "balance": balances[key][store_key],
            "reason": m.reason,
            "unit_price": m.unit_price or 0,
            "order_number": order_numbers.get(m.id, ""),
            "store_id": m.store_id,
            "created_at": str(m.created_at),
        })

    return rows
```

- [ ] **Step 2: 更新 transaction_ledger.py**

同样将 FK_MAP 改为 `_SOURCE_MODELS`，查询改用 `source_type + source_id`，加 `store_id` 筛选参数。

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/stock_ledger.py backend/app/api/transaction_ledger.py
git commit -m "refactor: stock/transaction ledger 适配 source 多态 + store_id 筛选"
```

---

### Task 17: 创建 InventoryCheck API

**Files:**
- Create: `backend/app/schemas/inventory_check.py`
- Create: `backend/app/services/inventory_check_service.py`
- Create: `backend/app/api/inventory_checks.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: InventoryCheck Schema**

```python
# backend/app/schemas/inventory_check.py
from pydantic import BaseModel
from typing import List
from datetime import date


class CheckItem(BaseModel):
    product_id: int
    actual_quantity: int


class InventoryCheckCreate(BaseModel):
    store_id: int
    check_date: date
    items: List[CheckItem]
    note: str = ""


class InventoryCheckOut(BaseModel):
    id: int
    order_number: str
    store_id: int
    store_name: str
    check_date: str
    status: str
    item_count: int
    note: str
    created_at: str
```

- [ ] **Step 2: InventoryCheckService**

```python
# backend/app/services/inventory_check_service.py
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.models.inventory_check import InventoryCheck, InventoryCheckItem
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.store import Store
from app.models.product_customer_price import ProductCustomerPrice
from app.models.customer import Customer
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.inventory_check import InventoryCheckCreate


class InventoryCheckService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def _next_order_number(self) -> str:
        from app.services.order_number import next_order_number
        return next_order_number(self.db, InventoryCheck, "IC")

    def _resolve_sale_price(self, customer_id: int, product: Product) -> float:
        """客户协议价 > 产品批发价"""
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product.id,
        ).first()
        if custom:
            return custom.price
        return product.default_wholesale_price

    def _get_last_check_quantity(self, store_id: int, product_id: int, before_date: date) -> int:
        """最近一次盘点该产品的实盘数"""
        last = (
            self.db.query(InventoryCheckItem.actual_quantity)
            .join(InventoryCheck)
            .filter(
                InventoryCheck.store_id == store_id,
                InventoryCheck.check_date < before_date,
                InventoryCheck.status == "confirmed",
                InventoryCheckItem.product_id == product_id,
            )
            .order_by(InventoryCheck.check_date.desc())
            .first()
        )
        return last[0] if last else 0

    def _get_last_check_date(self, store_id: int, before_date: date) -> date | None:
        """最近一次盘点日期"""
        last = (
            self.db.query(InventoryCheck.check_date)
            .filter(
                InventoryCheck.store_id == store_id,
                InventoryCheck.check_date < before_date,
                InventoryCheck.status == "confirmed",
            )
            .order_by(InventoryCheck.check_date.desc())
            .first()
        )
        return last[0] if last else None

    def create(self, data: InventoryCheckCreate):
        store = self.db.query(Store).filter(Store.id == data.store_id).first()
        if not store:
            raise ValueError("店铺不存在")

        check = InventoryCheck(
            order_number=self._next_order_number(),
            store_id=data.store_id,
            check_date=data.check_date,
            note=data.note,
        )
        self.db.add(check)
        self.db.flush()

        products = {p.id: p for p in self.db.query(Product).all()}

        # 上次盘点日期（用于计算期间收货的起点）
        last_check_date = self._get_last_check_date(data.store_id, data.check_date)
        from_dt = datetime.combine(last_check_date, datetime.min.time()) if last_check_date else datetime.min
        to_dt = datetime.combine(data.check_date, datetime.min.time())

        for item in data.items:
            # 保存盘点明细
            detail = InventoryCheckItem(
                check_id=check.id,
                product_id=item.product_id,
                actual_quantity=item.actual_quantity,
            )
            self.db.add(detail)

            # 计算销量
            beginning = self._get_last_check_quantity(data.store_id, item.product_id, data.check_date)
            received = self.stock_repo.get_store_receive_between(
                data.store_id, item.product_id, from_dt, to_dt
            )
            ending = item.actual_quantity
            sales_qty = beginning + received - ending

            product = products.get(item.product_id)
            if not product:
                continue

            if sales_qty > 0:
                # 库存变动
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "out",
                    "reason": "store_sales",
                    "quantity": sales_qty,
                    "source_type": "inventory_check",
                    "source_id": check.id,
                    "store_id": data.store_id,
                }])

                # 成本
                cost = sales_qty * product.default_purchase_price
                self.txn_repo.create(
                    category="store_cogs",
                    amount=-cost,
                    source_type="inventory_check",
                    source_id=check.id,
                    store_id=data.store_id,
                )

                # 收入（需客户信息）
                sale_price = self._resolve_sale_price(store.customer_id or 0, product)
                revenue = sales_qty * sale_price
                self.txn_repo.create(
                    customer_id=store.customer_id,
                    category="store_sales",
                    amount=revenue,
                    source_type="inventory_check",
                    source_id=check.id,
                    store_id=data.store_id,
                )

            elif sales_qty < 0:
                # 盘盈
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "direction": "in",
                    "reason": "store_gain",
                    "quantity": -sales_qty,
                    "source_type": "inventory_check",
                    "source_id": check.id,
                    "store_id": data.store_id,
                }])

        self.db.commit()
        return {"id": check.id, "order_number": check.order_number}

    def list_checks(self, store_id: int | None = None, date_from: str | None = None, date_to: str | None = None):
        from app.models.store import Store as StoreModel
        q = self.db.query(InventoryCheck).order_by(InventoryCheck.check_date.desc())
        if store_id:
            q = q.filter(InventoryCheck.store_id == store_id)
        if date_from:
            q = q.filter(InventoryCheck.check_date >= date.fromisoformat(date_from))
        if date_to:
            q = q.filter(InventoryCheck.check_date < date.fromisoformat(date_to))
        checks = q.all()
        stores = {s.id: s.name for s in self.db.query(StoreModel).all()}
        return [
            {
                "id": c.id,
                "order_number": c.order_number,
                "store_id": c.store_id,
                "store_name": stores.get(c.store_id, ""),
                "check_date": str(c.check_date),
                "status": c.status,
                "item_count": self.db.query(InventoryCheckItem).filter(
                    InventoryCheckItem.check_id == c.id
                ).count(),
                "note": c.note,
                "created_at": str(c.created_at),
            }
            for c in checks
        ]

    def get_detail(self, check_id: int):
        check = self.db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
        if not check:
            return None
        stores = {s.id: s.name for s in self.db.query(Store).all()}
        products = {p.id: p for p in self.db.query(Product).all()}
        items = self.db.query(InventoryCheckItem).filter(InventoryCheckItem.check_id == check_id).all()
        stock_moves = self.stock_repo.get_by_source("inventory_check", check_id)
        txns = self.txn_repo.get_by_source("inventory_check", check_id)

        item_details = []
        for item in items:
            p = products.get(item.product_id)
            sales_move = next((m for m in stock_moves if m.product_id == item.product_id and m.reason == "store_sales"), None)
            gain_move = next((m for m in stock_moves if m.product_id == item.product_id and m.reason == "store_gain"), None)
            sales_qty = sales_move.quantity if sales_move else (gain_move.quantity if gain_move else 0)
            item_details.append({
                "product_id": item.product_id,
                "product_name": p.name if p else "",
                "actual_quantity": item.actual_quantity,
                "sales_quantity": sales_qty if sales_move else (-gain_move.quantity if gain_move else 0),
                "unit_price": p.default_wholesale_price if p else 0,
            })

        return {
            "id": check.id,
            "order_number": check.order_number,
            "store_id": check.store_id,
            "store_name": stores.get(check.store_id, ""),
            "check_date": str(check.check_date),
            "status": check.status,
            "note": check.note,
            "created_at": str(check.created_at),
            "items": item_details,
            "transactions": [
                {"id": t.id, "category": t.category, "amount": t.amount, "created_at": str(t.created_at)}
                for t in txns
            ],
        }

    def cancel(self, check_id: int):
        check = self.db.query(InventoryCheck).filter(InventoryCheck.id == check_id).first()
        if not check:
            raise ValueError("盘点单不存在")
        if check.status == "cancelled":
            raise ValueError("该盘点单已撤销")

        # 级联检查：是否已被后续盘点引用
        later = (
            self.db.query(InventoryCheck)
            .filter(
                InventoryCheck.store_id == check.store_id,
                InventoryCheck.check_date > check.check_date,
                InventoryCheck.status == "confirmed",
            )
            .order_by(InventoryCheck.check_date.asc())
            .first()
        )
        if later:
            raise ValueError(f"该盘点已被 {later.order_number} 引用，请先撤销后续盘点")

        # 删库存流水
        moves = self.stock_repo.get_by_source("inventory_check", check_id)
        for m in moves:
            self.db.delete(m)

        # 删资金流水
        txns = self.txn_repo.get_by_source("inventory_check", check_id)
        for t in txns:
            self.db.delete(t)

        check.status = "cancelled"
        self.db.commit()
        return {"id": check.id, "status": "cancelled"}
```

- [ ] **Step 3: InventoryCheck API**

```python
# backend/app/api/inventory_checks.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.inventory_check_service import InventoryCheckService
from app.schemas.inventory_check import InventoryCheckCreate

router = APIRouter(prefix="/api/inventory-checks", tags=["inventory-checks"])


def get_service(db: Session = Depends(get_db)):
    return InventoryCheckService(db)


@router.post("", status_code=201)
def create_check(data: InventoryCheckCreate, svc: InventoryCheckService = Depends(get_service)):
    try:
        return svc.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_checks(
    store_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    svc: InventoryCheckService = Depends(get_service),
):
    return svc.list_checks(store_id, date_from, date_to)


@router.get("/{check_id}")
def get_check(check_id: int, svc: InventoryCheckService = Depends(get_service)):
    detail = svc.get_detail(check_id)
    if not detail:
        raise HTTPException(status_code=404, detail="盘点单不存在")
    return detail


@router.post("/{check_id}/cancel")
def cancel_check(check_id: int, svc: InventoryCheckService = Depends(get_service)):
    try:
        return svc.cancel(check_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: 注册路由**

在 `backend/app/api/router.py` 中加：
```python
from app.api import inventory_checks
api_router.include_router(inventory_checks.router)
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/schemas/inventory_check.py backend/app/services/inventory_check_service.py backend/app/api/inventory_checks.py backend/app/api/router.py
git commit -m "feat: InventoryCheck — schema + service + api"
```

---

### Task 18: 前端类型 + API 适配

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 加 Store 和 InventoryCheck 类型**

在 `frontend/src/types/index.ts` 中追加：

```typescript
export interface Store {
  id: number;
  name: string;
  customer_id: number | null;
  customer_name: string;
  address: string;
  status: string;
  created_at: string;
}

export interface InventoryCheck {
  id: number;
  order_number: string;
  store_id: number;
  store_name: string;
  check_date: string;
  status: string;
  item_count: number;
  note: string;
  created_at: string;
}

export interface InventoryCheckItem {
  product_id: number;
  product_name?: string;
  actual_quantity: number;
}

export interface InventoryCheckDetail extends InventoryCheck {
  items: any[];
  transactions: any[];
}
```

- [ ] **Step 2: 加 Store 和 InventoryCheck API**

在 `frontend/src/services/api.ts` 中追加：

```typescript
// Stores
export const storeApi = {
  list: () => api.get('/stores').then(r => r.data),
  get: (id: number) => api.get(`/stores/${id}`).then(r => r.data),
  create: (data: any) => api.post('/stores', data).then(r => r.data),
  update: (id: number, data: any) => api.put(`/stores/${id}`, data).then(r => r.data),
};

// Inventory Checks
export const inventoryCheckApi = {
  create: (data: any) => api.post('/inventory-checks', data).then(r => r.data),
  list: (params?: any) => api.get('/inventory-checks', { params }).then(r => r.data),
  get: (id: number) => api.get(`/inventory-checks/${id}`).then(r => r.data),
  cancel: (id: number) => api.post(`/inventory-checks/${id}/cancel`).then(r => r.data),
};
```

- [ ] **Step 3: 更新 ledgerApi 加 store_id 参数**

```typescript
export const ledgerApi = {
  stock: (params?: any) => api.get('/stock-ledger', { params }).then(r => r.data),
  transactions: (params?: any) => api.get('/transaction-ledger', { params }).then(r => r.data),
};
```

（已经接受 params，前端传 `store_id` 即可，不需要改 API 定义）

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: 前端 Store + InventoryCheck 类型和 API"
```

---

### Task 19: 前端店铺管理页

**Files:**
- Create: `frontend/src/pages/StoresPage.tsx`

- [ ] **Step 1: 创建店铺管理页**

```tsx
// frontend/src/pages/StoresPage.tsx
import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { OrderListTable } from '../components/business/OrderListTable';
import { storeApi, customerApi } from '../services/api';
import type { Store } from '../types';

export default function StoresPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState('');
  const [customerId, setCustomerId] = useState<number | string>('');
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStores();
    customerApi.list().then(setCustomers);
  }, []);

  const loadStores = () => storeApi.list().then(setStores);

  const handleCreate = async () => {
    if (!name) { alert('请输入店名'); return; }
    setLoading(true);
    try {
      await storeApi.create({ name, customer_id: Number(customerId) || null, address });
      setFormOpen(false);
      setName('');
      setCustomerId('');
      setAddress('');
      loadStores();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    } finally { setLoading(false); }
  };

  const columns = [
    { key: 'name', title: '店名', render: (s: Store) => <span className="font-medium">{s.name}</span> },
    { key: 'customer_name', title: '关联客户' },
    { key: 'address', title: '地址' },
    { key: 'status', title: '状态' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">店铺管理</h2>
        <Button onClick={() => setFormOpen(true)}>+ 新建店铺</Button>
      </div>

      <OrderListTable columns={columns} data={stores} rowKey={(s) => s.id} />

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title="新建店铺">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">店名</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="店名" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">关联客户</label>
            <select
              value={customerId}
              onChange={(e) => setCustomerId(Number(e.target.value))}
              className="w-full border rounded px-3 py-2 text-sm mt-1"
            >
              <option value="">不关联</option>
              {customers.map((c: any) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">地址</label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="地址" />
          </div>
          <div className="flex gap-2 pt-2 border-t">
            <Button onClick={handleCreate} disabled={loading}>创建</Button>
            <Button variant="secondary" onClick={() => setFormOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/StoresPage.tsx
git commit -m "feat: 店铺管理页"
```

---

### Task 20: 前端盘点页

**Files:**
- Create: `frontend/src/pages/InventoryCheckPage.tsx`

- [ ] **Step 1: 创建盘点页**

```tsx
// frontend/src/pages/InventoryCheckPage.tsx
import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { OrderListTable } from '../components/business/OrderListTable';
import { OrderDetailModal } from '../components/business/OrderDetailModal';
import { storeApi, productApi, inventoryCheckApi, ledgerApi, inventoryApi } from '../services/api';
import type { InventoryCheck, InventoryCheckDetail } from '../types';

export default function InventoryCheckPage() {
  const [stores, setStores] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [storeId, setStoreId] = useState<number | string>('');
  const [checkDate, setCheckDate] = useState(new Date().toISOString().slice(0, 10));
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [checks, setChecks] = useState<InventoryCheck[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<InventoryCheckDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  useEffect(() => {
    storeApi.list().then((data: any) => {
      setStores(data);
      if (data.length === 1) setStoreId(data[0].id);
    });
    productApi.list().then(setProducts);
    loadChecks();
  }, []);

  const loadChecks = () => inventoryCheckApi.list().then(setChecks);

  const handleConfirm = async () => {
    if (!storeId) { alert('请选店铺'); return; }
    const items = Object.entries(quantities)
      .filter(([_, qty]) => qty > 0)
      .map(([pid, qty]) => ({ product_id: Number(pid), actual_quantity: qty }));
    if (items.length === 0) { alert('请至少填写一个产品的实盘数'); return; }

    setLoading(true);
    try {
      await inventoryCheckApi.create({ store_id: Number(storeId), check_date: checkDate, items });
      setQuantities({});
      loadChecks();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '创建失败');
    } finally { setLoading(false); }
  };

  const openDetail = async (id: number) => {
    const d = await inventoryCheckApi.get(id);
    setDetail(d);
    setDetailOpen(true);
  };

  const handleCancel = async (id: number) => {
    if (!confirm('确定撤销？')) return;
    await inventoryCheckApi.cancel(id);
    loadChecks();
  };

  const columns = [
    { key: 'order_number', title: '单号', render: (c: any) => <span className="font-medium">{c.order_number}</span> },
    { key: 'store_name', title: '店铺' },
    { key: 'check_date', title: '日期' },
    { key: 'item_count', title: '品项数' },
    { key: 'status', title: '状态' },
    {
      key: 'actions', title: '操作',
      render: (c: any) => (
        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
          {c.status === 'confirmed' && (
            <Button variant="danger" size="sm" onClick={() => handleCancel(c.id)}>撤销</Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">盘点管理</h2>

      <div className="bg-white rounded-lg border p-4 mb-6">
        <h3 className="font-semibold mb-3">新建盘点</h3>
        <div className="flex gap-4 mb-4">
          <select
            value={storeId}
            onChange={(e) => setStoreId(Number(e.target.value))}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="">选店铺</option>
            {stores.map((s: any) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <Input type="date" value={checkDate} onChange={(e) => setCheckDate(e.target.value)} />
        </div>
        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {products.map((p) => (
            <div key={p.id} className="border rounded p-2">
              <div className="text-xs text-gray-500 truncate">{p.name}</div>
              <input
                type="number"
                min="0"
                value={quantities[p.id] || ''}
                onChange={(e) => setQuantities(prev => ({
                  ...prev, [p.id]: e.target.value ? parseInt(e.target.value) : 0
                }))}
                className="w-full border rounded px-2 py-1 text-sm mt-1"
                placeholder="实盘"
              />
            </div>
          ))}
        </div>
        <div className="mt-4">
          <Button onClick={handleConfirm} disabled={loading}>确认盘点</Button>
        </div>
      </div>

      <h3 className="text-lg font-semibold mb-2">盘点记录</h3>
      <OrderListTable
        columns={columns}
        data={checks}
        rowKey={(c) => c.id}
        onRowClick={(c) => openDetail(c.id)}
      />

      <OrderDetailModal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title={`盘点详情 — ${detail?.order_number || ''}`}
        headerInfo={
          <>
            <div>店铺: {detail?.store_name}</div>
            <div>日期: {detail?.check_date}</div>
          </>
        }
        items={detail?.items || []}
      />
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/InventoryCheckPage.tsx
git commit -m "feat: 盘点页面"
```

---

### Task 21: 前端路由注册 + 侧边栏入口

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: App.tsx 加路由**

```tsx
// 在 imports 中加:
import StoresPage from './pages/StoresPage';
import InventoryCheckPage from './pages/InventoryCheckPage';

// 在 <Routes> 中加:
<Route path="/stores" element={<StoresPage />} />
<Route path="/inventory-checks" element={<InventoryCheckPage />} />
```

- [ ] **Step 2: Layout.tsx 侧边栏加入口**

```tsx
// 在 navItems 数组中加:
{ path: '/stores', label: '店铺管理' },
{ path: '/inventory-checks', label: '盘点管理' },
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: 注册店铺管理和盘点路由 + 侧边栏入口"
```

---

### Task 22: 更新库存流水和资金流水页加店铺筛选

**Files:**
- Modify: `frontend/src/pages/StockLedgerPage.tsx`
- Modify: `frontend/src/pages/TransactionLedgerPage.tsx`

- [ ] **Step 1: StockLedgerPage 加 store_id 筛选**

在 `StockLedgerPage.tsx` 筛选栏中加店铺下拉，查询参数加 `store_id`。

- [ ] **Step 2: TransactionLedgerPage 加 store_id 筛选**

在 `TransactionLedgerPage.tsx` 筛选栏中加店铺下拉，查询参数加 `store_id`。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/StockLedgerPage.tsx frontend/src/pages/TransactionLedgerPage.tsx
git commit -m "feat: 流水页加店铺筛选"
```

---

### Task 23: 运行测试验证

**Files:**
- 运行: 全部测试

- [ ] **Step 1: 运行后端测试**

```bash
cd backend && python -m pytest tests/ -v
```

预期：现有测试可能需要更新（字段名变化），修复失败的测试。

- [ ] **Step 2: 启动前端检查编译**

```bash
cd frontend && npm run build 2>&1 | head -20
```

预期：无 TS 编译错误。

- [ ] **Step 3: 提交修复**

```bash
git add -A
git commit -m "test: 适配 source 多态改造后的测试修复"
```
