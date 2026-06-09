# 库存资金流水统一设计 & 订奶金额模式重构 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一库存资金流水体系：StockMovement 管货、Transaction 管钱，订奶从"瓶数扣减"改为"金额扣减"模式。

**Architecture:** 9 个 Task 组，按依赖顺序执行。Phase 1-2 是基础设施（模型+Schema），Phase 3-5 是核心业务改造（Service+API+前端），Phase 6-7 是清除旧逻辑和验证。每个 Task 独立可验证。

**Tech Stack:** Python/FastAPI/SQLAlchemy/SQLite, React/TypeScript/Vite

---

### Task 1: 模型层变更

**Files:**
- Create: `backend/app/models/retail_order.py`
- Modify: `backend/app/models/stock_movement.py`
- Modify: `backend/app/models/transaction.py`
- Modify: `backend/app/models/subscription_order.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/__init__.py` (if exists)

- [ ] **Step 1: 创建 RetailOrder 模型**

```python
# backend/app/models/retail_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from app.database import Base


class RetailOrder(Base):
    __tablename__ = "retail_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 修改 StockMovement 模型**

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
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True)
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    retail_order_id = Column(Integer, ForeignKey("retail_orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 3: 修改 Transaction 模型**

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
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    retail_order_id = Column(Integer, ForeignKey("retail_orders.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 4: 修改 SubscriptionOrder 模型**

```python
# backend/app/models/subscription_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class SubscriptionOrder(Base):
    __tablename__ = "subscription_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    paid_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    note = Column(String(500), default="")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 5: 更新 main.py lifespan 自动补齐新列**

```python
# backend/app/main.py — 在 lifespan 中扩展列补齐逻辑
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text, inspect
    insp = inspect(engine)

    # 新增列列表
    new_cols = [
        ("stock_movements", "purchase_order_id", "INTEGER REFERENCES purchase_orders(id)"),
        ("transactions", "purchase_order_id", "INTEGER REFERENCES purchase_orders(id)"),
        ("stock_movements", "retail_order_id", "INTEGER REFERENCES retail_orders(id)"),
        ("transactions", "subscription_order_id", "INTEGER REFERENCES subscription_orders(id)"),
        ("transactions", "retail_order_id", "INTEGER REFERENCES retail_orders(id)"),
    ]
    for table, col, col_type in new_cols:
        cols = [c["name"] for c in insp.get_columns(table)]
        if col not in cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()

    # subscription_orders 重命名列 + 新增 note
    sub_cols = [c["name"] for c in insp.get_columns("subscription_orders")]
    rename_map = [
        ("total_amount", "paid_amount"),
        ("remaining_bottles", "remaining_amount"),
    ]
    for old_name, new_name in rename_map:
        if old_name in sub_cols and new_name not in sub_cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE subscription_orders RENAME COLUMN {old_name} TO {new_name}"))
                conn.commit()

    if "note" not in sub_cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE subscription_orders ADD COLUMN note VARCHAR(500) DEFAULT ''"))
            conn.commit()

    yield
```

- [ ] **Step 6: 启动后端验证表创建成功**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```
Expected: OK 无报错，数据库中自动创建 retail_orders 表，补齐新列。

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/retail_order.py backend/app/models/stock_movement.py backend/app/models/transaction.py backend/app/models/subscription_order.py backend/app/main.py
git commit -m "feat: 模型层变更 — 新增 retail_orders，StockMovement/Transaction 新增 FK，SubscriptionOrder 重命名列"
```

---

### Task 2: Repository 层适配

**Files:**
- Modify: `backend/app/repositories/stock_movement_repo.py`
- Modify: `backend/app/repositories/transaction_repo.py`
- Create: `backend/app/repositories/retail_order_repo.py`

- [ ] **Step 1: 更新 StockMovementRepository**

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

    def get_by_delivery(self, delivery_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.delivery_id == delivery_id
        ).all()

    def get_by_purchase_order(self, purchase_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.purchase_order_id == purchase_order_id
        ).all()

    def get_by_subscription_order(self, subscription_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.subscription_order_id == subscription_order_id
        ).all()

    def get_inventory(self) -> list:
        """按 product_id 汇总库存（不再按 shelf_id 分组）"""
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

    def validate_stock(self, items: list):
        """库存校验：按 product_id 汇总检查"""
        inventory = {
            r.product_id: r.stock
            for r in self.get_inventory()
        }
        # 合并同产品多行
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

- [ ] **Step 2: 更新 TransactionRepository**

```python
# backend/app/repositories/transaction_repo.py — 增加 get_amounts_by_deliveries 中 category 映射
# 修改 get_ar_by_customer 和 get_receivables 中的 category 列表

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

    def get_by_delivery(self, delivery_id: int) -> List[Transaction]:
        return self.db.query(Transaction).filter(
            Transaction.delivery_id == delivery_id
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
                Transaction.delivery_id,
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(Transaction.delivery_id.in_(delivery_ids))
            .group_by(Transaction.delivery_id, Transaction.category)
            .all()
        )
        result: dict[int, dict] = {did: {"total_amount": 0.0, "paid_amount": 0.0} for did in delivery_ids}
        for row in rows:
            if row.category in ("distribution", "delivery", "delivery_cancel"):
                result[row.delivery_id]["total_amount"] += row.total
            elif row.category == "payment":
                result[row.delivery_id]["paid_amount"] += row.total
        for did, amounts in result.items():
            amounts["unpaid_amount"] = amounts["total_amount"] - amounts["paid_amount"]
        return result

    def list_all(self):
        return self.db.query(Transaction).order_by(Transaction.created_at.desc()).limit(200).all()
```

- [ ] **Step 3: 创建 RetailOrderRepository**

```python
# backend/app/repositories/retail_order_repo.py
from sqlalchemy.orm import Session
from app.models.retail_order import RetailOrder


class RetailOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, customer_id: int | None = None) -> RetailOrder:
        order = RetailOrder(customer_id=customer_id)
        self.db.add(order)
        self.db.flush()
        return order
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/
git commit -m "feat: repository 层适配 — 去 shelf_id、新增 retail_order_repo、更新应收查询"
```

---

### Task 3: Schema 层变更

**Files:**
- Modify: `backend/app/schemas/subscription.py`
- Modify: `backend/app/schemas/sale.py`
- Modify: `backend/app/schemas/wastage.py`
- Modify: `backend/app/schemas/delivery.py`
- Modify: `backend/app/schemas/return_schema.py`
- Modify: `backend/app/schemas/purchase.py`

- [ ] **Step 1: 更新 SubscriptionCreate 和 SubscriptionDeduct**

```python
# backend/app/schemas/subscription.py
from pydantic import BaseModel
from typing import List, Optional


class SubscriptionCreate(BaseModel):
    customer_id: int
    paid_amount: float
    is_paid: bool = True
    note: str = ""


class SubscriptionDeductItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[float] = None
    is_promo: bool = False


class SubscriptionDeduct(BaseModel):
    items: List[SubscriptionDeductItem]
```

- [ ] **Step 2: 更新 SaleCreate（新增 retail_order_id 关联）**

```python
# backend/app/schemas/sale.py
from pydantic import BaseModel
from typing import List, Optional


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_promo: bool = False


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItem]
    paid: bool = True
    note: str = ""
```

- [ ] **Step 3: 更新 WastageCreate（去 shelf_id）**

```python
# backend/app/schemas/wastage.py
from pydantic import BaseModel
from typing import List, Optional


class WastageItem(BaseModel):
    product_id: int
    quantity: int
    reason: str


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
```

- [ ] **Step 4: 更新 DeliveryCreate（新增 is_promo）**

先读取当前 delivery schema：
```python
# backend/app/schemas/delivery.py — 在 DeliveryCreateItem 中新增 is_promo 字段
```

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DeliveryCreateItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_promo: bool = False


class DeliveryCreate(BaseModel):
    customer_id: int
    delivery_date: date
    items: List[DeliveryCreateItem]
    subscription_order_id: Optional[int] = None
    paid: bool = False
    note: str = ""


class ExchangeItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class ExchangeCreate(BaseModel):
    return_items: List[ExchangeItem]
    new_items: List[ExchangeItem]
```

- [ ] **Step 4b: 更新 ReturnItem — 去 shelf_id**

```python
# backend/app/schemas/return_schema.py
class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_wasted: bool = False


class ReturnCreate(BaseModel):
    customer_id: int
    delivery_id: Optional[int] = None
    items: List[ReturnItem]
    note: str = ""
```

- [ ] **Step 4c: 更新 PurchaseItem — 去 shelf_id**

```python
# backend/app/schemas/purchase.py
class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class PurchaseCreate(BaseModel):
    supplier_id: int
    purchase_date: date
    items: List[PurchaseItem]
    note: str = ""
    status: str = "confirmed"


class PurchaseConfirm(BaseModel):
    items: Optional[List[PurchaseItem]] = None
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: schema 层变更 — 订奶改金额模式，零售/分销新增 is_promo，去 shelf_id"
```

---

### Task 4: SubscriptionService 核心改造

**Files:**
- Modify: `backend/app/services/subscription_service.py`

- [ ] **Step 1: 重写 create_order**

```python
# backend/app/services/subscription_service.py
from sqlalchemy.orm import Session
from app.repositories.subscription_order_repo import SubscriptionOrderRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sub_repo = SubscriptionOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_order(self, data: SubscriptionCreate):
        order = self.sub_repo.create(
            customer_id=data.customer_id,
            paid_amount=data.paid_amount,
            remaining_amount=data.paid_amount,
            note=data.note,
            status="active",
        )
        if data.is_paid:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="payment",
                amount=data.paid_amount,
                subscription_order_id=order.id,
            )
        self.db.commit()
        return {
            "id": order.id,
            "paid_amount": order.paid_amount,
            "remaining_amount": order.remaining_amount,
            "status": order.status,
        }
```

- [ ] **Step 2: 实现 unit_price 解析方法**

```python
    def _resolve_unit_price(self, customer_id: int, product_id: int, unit_price: float | None) -> float:
        """解析优先级：手动填入 > 客户专属价 > 等级价(批发价) > 默认零售价"""
        if unit_price is not None:
            return unit_price

        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return 0.0

        # 客户专属价
        from app.models.product_customer_price import ProductCustomerPrice
        custom = self.db.query(ProductCustomerPrice).filter(
            ProductCustomerPrice.customer_id == customer_id,
            ProductCustomerPrice.product_id == product_id,
        ).first()
        if custom:
            return custom.price

        # 等级价：批发客户用批发价
        from app.models.customer import Customer
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if customer and customer.price_tier == "批发":
            return product.default_wholesale_price

        # 默认零售价
        return product.default_retail_price

    def _get_purchase_cost(self, product_id: int) -> float:
        """获取产品进价（默认进货价）"""
        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            return product.default_purchase_price
        return 0.0
```

- [ ] **Step 3: 重写 deduct 方法**

```python
    def deduct(self, order_id: int, data: SubscriptionDeduct):
        order = self.sub_repo.get_by_id(order_id)
        if not order:
            raise ValueError("订奶单不存在")
        if order.status != "active":
            raise ValueError("订奶单非活跃状态")

        # 计算付费行合计并校验金额
        paid_total = 0.0
        items_for_validate = []
        for item in data.items:
            if not item.is_promo:
                price = self._resolve_unit_price(order.customer_id, item.product_id, item.unit_price)
                paid_total += item.quantity * price
            items_for_validate.append({"product_id": item.product_id, "quantity": item.quantity})

        if paid_total > order.remaining_amount:
            raise ValueError(f"超出余额，剩余 ¥{order.remaining_amount:.2f}，本次扣减 ¥{paid_total:.2f}")

        self.stock_repo.validate_stock(items_for_validate)

        for item in data.items:
            unit_price = 0.0 if item.is_promo else self._resolve_unit_price(order.customer_id, item.product_id, item.unit_price)
            purchase_cost = self._get_purchase_cost(item.product_id)
            total_price = item.quantity * unit_price
            total_cost = item.quantity * purchase_cost

            # StockMovement - 定奶出库
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "direction": "out",
                "reason": "subscription",
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subscription_order_id": order_id,
            }])

            if item.is_promo:
                # 赠送行：记促销成本
                if total_cost > 0:
                    self.txn_repo.create(
                        customer_id=order.customer_id,
                        category="promo",
                        amount=-total_cost,
                        subscription_order_id=order_id,
                    )
            else:
                # 付费行：收入确认 + 成本
                self.txn_repo.create(
                    customer_id=order.customer_id,
                    category="subscription",
                    amount=total_price,
                    subscription_order_id=order_id,
                )
                if total_cost > 0:
                    self.txn_repo.create(
                        customer_id=order.customer_id,
                        category="cogs",
                        amount=-total_cost,
                        subscription_order_id=order_id,
                    )

        # 更新余额
        order.remaining_amount -= paid_total
        if order.remaining_amount <= 0:
            order.status = "completed"

        self.db.commit()
        return {
            "remaining_amount": order.remaining_amount,
            "status": order.status,
            "deducted": paid_total,
        }
```

- [ ] **Step 4: 启动后端，用 curl 测试创建和扣减**

```bash
# 测试创建（已收款）
curl -X POST http://localhost:8000/api/subscription-orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "paid_amount": 500, "is_paid": true, "note": "测试"}'

# 测试扣减
curl -X POST http://localhost:8000/api/subscription-orders/1/deduct \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": 1, "quantity": 2, "unit_price": 10, "is_promo": false}]}'
```
Expected: 创建返回 `{"id": ..., "remaining_amount": 500, "status": "active"}`，扣减返回余额变化。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/subscription_service.py
git commit -m "feat: subscription_service 核心改造 — 金额模式、unit_price 解析、cogs/promo 记账"
```

---

### Task 5: SaleService 适配（零售出库 + retail_order + cogs）

**Files:**
- Modify: `backend/app/services/sale_service.py`

- [ ] **Step 1: 重写 SaleService**

```python
# backend/app/services/sale_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.retail_order_repo import RetailOrderRepository
from app.schemas.sale import SaleCreate
from app.models.transaction import Transaction
from app.models.product import Product


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.retail_repo = RetailOrderRepository(db)

    def create_sale(self, data: SaleCreate):
        self.stock_repo.validate_stock(data.items)

        retail_order = self.retail_repo.create(customer_id=data.customer_id)

        total = 0.0
        movements = []
        for item in data.items:
            unit_price = 0.0 if item.is_promo else item.unit_price
            amount = item.quantity * unit_price
            if not item.is_promo:
                total += amount
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "retail",
                "quantity": item.quantity,
                "unit_price": unit_price,
                "retail_order_id": retail_order.id,
            })

        self.stock_repo.bulk_create(movements)

        # 收入
        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="retail",
                amount=total,
                retail_order_id=retail_order.id,
            )

        # cogs + promo 成本
        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}
        for item in data.items:
            cost = costs.get(item.product_id, 0)
            if cost > 0:
                category = "promo" if item.is_promo else "cogs"
                self.txn_repo.create(
                    customer_id=data.customer_id,
                    category=category,
                    amount=-(item.quantity * cost),
                    retail_order_id=retail_order.id,
                )

        # 已收款 → payment Transaction
        if data.paid and total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="payment",
                amount=total,
                retail_order_id=retail_order.id,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items), "retail_order_id": retail_order.id}

    def list_sales(self):
        return self.db.query(Transaction).filter(
            Transaction.category.in_(["retail", "sale"])
        ).order_by(Transaction.created_at.desc()).all()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/sale_service.py
git commit -m "feat: sale_service 适配 — retail_order 关联、cogs/promo 记账、去 shelf_id"
```

---

### Task 6: WastageService 适配（损耗记账）

**Files:**
- Modify: `backend/app/services/wastage_service.py`

- [ ] **Step 1: 重写 WastageService**

```python
# backend/app/services/wastage_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.wastage import WastageCreate
from app.models.product import Product


class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_wastage(self, data: WastageCreate):
        self.stock_repo.validate_stock(data.items)

        product_ids = list({item.product_id for item in data.items})
        costs = {p.id: p.default_purchase_price for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()}

        movements = []
        total_cost = 0.0
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "direction": "out",
                "reason": "wastage",
                "quantity": item.quantity,
            })
            cost = costs.get(item.product_id, 0)
            total_cost += item.quantity * cost

        self.stock_repo.bulk_create(movements)

        if total_cost > 0:
            self.txn_repo.create(
                category="wastage",
                amount=-total_cost,
            )

        self.db.commit()
        return {"item_count": len(data.items), "total_cost": total_cost}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/wastage_service.py
git commit -m "feat: wastage_service 适配 — 新增 wastage Transaction 记账、去 shelf_id"
```

---

### Task 7: DeliveryService & ReturnService & PurchaseService 适配

**Files:**
- Modify: `backend/app/services/delivery_service.py`
- Modify: `backend/app/services/return_service.py`
- Modify: `backend/app/services/purchase_service.py`

- [ ] **Step 1: 更新 DeliveryService — 去 shelf_id，新增 is_promo 支持**

DeliveryService 改动点：
1. `create_delivery` 中 `movements` 去 `shelf_id`，reason 改为 `"distribution"`
2. `create_delivery` 中 category 改为 `"distribution"`
3. 支持 `is_promo`：`unit_price` 强制为 0，记 `promo` Transaction
4. `exchange` 中去 `shelf_id`

具体代码（只展示变更部分，完整文件太长）：

```python
# 在 create_delivery 中:
for item in data.items:
    unit_price = 0.0 if item.is_promo else item.unit_price
    amount = item.quantity * unit_price
    if not item.is_promo:
        total += amount
    movements.append({
        "product_id": item.product_id,
        "direction": "out",
        "reason": "distribution",
        "quantity": item.quantity,
        "unit_price": unit_price,
        "delivery_id": delivery.id,
    })

# ...

if total > 0:
    self.txn_repo.create(
        customer_id=data.customer_id,
        category="distribution",
        amount=total,
        delivery_id=delivery.id,
    )

# promo 成本
for item in data.items:
    if item.is_promo and item.unit_price == 0:
        # 查进价
        from app.models.product import Product
        product = self.db.query(Product).filter(Product.id == item.product_id).first()
        if product and product.default_purchase_price > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="promo",
                amount=-(item.quantity * product.default_purchase_price),
                delivery_id=delivery.id,
            )
```

exchange 方法中去掉 `shelf_id`：

```python
# return_movements 和 new_movements 中去掉 "shelf_id" key
return_movements.append({
    "product_id": item.product_id,
    "direction": "in",
    "reason": "exchange",
    "quantity": item.quantity,
    "unit_price": item.unit_price,
    "delivery_id": delivery_id,
    "created_at": now,
})
```

get_delivery_detail 中 category 兼容新旧名称：

```python
delivery_total = sum(t.amount for t in transactions if t.category in ("distribution", "delivery", "delivery_cancel"))
```

- [ ] **Step 2: 更新 ReturnService — 去 shelf_id**

```python
# 去掉 stock_movement dict 中的 "shelf_id" key
self.stock_repo.bulk_create([{
    "product_id": item.product_id,
    "direction": "in",
    "reason": "return",
    "quantity": item.quantity,
    "unit_price": item.unit_price,
    "delivery_id": data.delivery_id,
}])
```

- [ ] **Step 3: 更新 PurchaseService — 去 shelf_id，cancel 改用新 reason/category**

`_confirm_items`、`cancel_order`、`import_confirm` 中的 `movements` dict 去掉 `"shelf_id"` key。CSV 导入中去掉 `shelf_name` 列。

`cancel_order` 中 reason 从 `"purchase_cancel"` 改为 `"cancel"`，Transaction category 从 `"purchase_cancel"` 改为 `"purchase"`（负数冲抵）：

```python
# cancel_order 中:
reverses.append({
    "product_id": item.product_id,
    "direction": "out",
    "reason": "cancel",        # 原 purchase_cancel → cancel
    "quantity": item.quantity,
    "unit_price": item.unit_price,
    "purchase_order_id": order_id,
})
# ...
self.txn_repo.create(
    supplier_id=order.supplier_id,
    category="purchase",        # 原 purchase_cancel → purchase
    amount=-reverse_total,      # 负数冲抵
    purchase_order_id=order_id,
)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/delivery_service.py backend/app/services/return_service.py backend/app/services/purchase_service.py
git commit -m "feat: delivery/return/purchase service 适配 — 去 shelf_id，category 改名 distribution，支持 is_promo"
```

---

### Task 8: API 层变更

**Files:**
- Modify: `backend/app/api/subscriptions.py`
- Modify: `backend/app/api/inventory.py`
- Modify: `backend/app/api/dashboard.py`
- Modify: `backend/app/api/wastage.py`

- [ ] **Step 1: 更新 subscriptions API — 新增详情、扣减记录**

```python
# backend/app/api/subscriptions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionCreate, SubscriptionDeduct
from app.repositories.stock_movement_repo import StockMovementRepository
from app.models.stock_movement import StockMovement

router = APIRouter(prefix="/api/subscription-orders", tags=["subscriptions"])


def get_subscription_service(db: Session = Depends(get_db)):
    return SubscriptionService(db)


@router.post("", status_code=201)
def create_order(data: SubscriptionCreate, svc: SubscriptionService = Depends(get_subscription_service)):
    return svc.create_order(data)


@router.post("/{order_id}/deduct")
def deduct(order_id: int, data: SubscriptionDeduct, svc: SubscriptionService = Depends(get_subscription_service)):
    try:
        return svc.deduct(order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_orders(svc: SubscriptionService = Depends(get_subscription_service)):
    return svc.sub_repo.list_all()


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    from app.repositories.subscription_order_repo import SubscriptionOrderRepository
    sub_repo = SubscriptionOrderRepository(db)
    order = sub_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订奶单不存在")

    stock_repo = StockMovementRepository(db)
    movements = stock_repo.get_by_subscription_order(order_id)

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "paid_amount": order.paid_amount,
        "remaining_amount": order.remaining_amount,
        "note": order.note,
        "status": order.status,
        "created_at": str(order.created_at),
        "deductions": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "quantity": m.quantity,
                "unit_price": m.unit_price,
                "created_at": str(m.created_at),
            }
            for m in movements
        ],
    }
```

- [ ] **Step 2: 更新 inventory API — 去 shelf_id**

```python
# backend/app/api/inventory.py
@router.get("")
def get_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    return [
        {"product_id": r.product_id, "stock": r.stock}
        for r in rows if r.stock != 0
    ]


@router.get("/export")
def export_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    products = {p.id: p.name for p in db.query(Product).all()}
    csv_lines = ["产品名称,库存"]
    for r in rows:
        if r.stock != 0:
            pname = products.get(r.product_id, str(r.product_id))
            csv_lines.append(f"{pname},{r.stock}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=inventory.csv"})
```

- [ ] **Step 3: 更新 dashboard API — category 名称适配**

```python
# backend/app/api/dashboard.py
today_sales = db.query(func.sum(Transaction.amount)).filter(
    Transaction.category.in_(["retail", "subscription", "distribution", "sale", "delivery", "delivery_cancel"]),
    func.date(Transaction.created_at) == today,
).scalar() or 0.0

# low_stock 返回去 shelf_id
low_stock = [
    {"product_id": r.product_id, "stock": r.stock}
    for r in inventory_rows if 0 < r.stock < 10
]
```

- [ ] **Step 4: 更新 wastage API — 去 shelf_id**

```python
# backend/app/api/wastage.py — 导出中去掉货架列
csv_lines = ["产品名称,数量,时间"]
for r in rows:
    pname = products.get(r.product_id, str(r.product_id))
    csv_lines.append(f"{pname},{r.quantity},{r.created_at}")
```

- [ ] **Step 5: 删除 shelves API router**

从 `backend/app/api/router.py` 中移除 shelves router 的注册。

- [ ] **Step 6: 启动后端验证所有 API 正常**

```bash
cd backend && uvicorn app.main:app --reload
# 访问 http://localhost:8000/docs 检查所有 endpoint
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/
git commit -m "feat: API 层变更 — 订阅详情接口、去 shelf_id、category 名称适配"
```

---

### Task 9: 前端改造

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/SubscriptionsPage.tsx`
- Create: `frontend/src/pages/SubscriptionDetailPage.tsx`
- Modify: `frontend/src/pages/SalesPage.tsx`
- Modify: `frontend/src/pages/DeliveriesPage.tsx`
- Modify: `frontend/src/pages/WastagePage.tsx`
- Modify: `frontend/src/pages/ReturnsPage.tsx`
- Modify: `frontend/src/pages/PurchasesPage.tsx`
- Modify: `frontend/src/pages/InventoryPage.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: 更新 TypeScript 类型定义**

```typescript
// frontend/src/types/index.ts
export interface Transaction {
  id: number;
  category: string;
  amount: number;
  created_at: string;
}

export interface StockMovement {
  id: number;
  product_id: number;
  direction: string;
  reason: string;
  quantity: number;
  unit_price?: number;
}

export interface SubscriptionOrder {
  id: number;
  customer_id: number;
  paid_amount: number;
  remaining_amount: number;
  note: string;
  status: string;
  created_at: string;
}

// 删除 Shelf 接口

// 更新接口（去 shelf_id，新增 is_promo）
export interface SaleItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo?: boolean;
}

export interface DeliveryCreateItem {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo?: boolean;
}

export interface PurchaseItem {
  product_id: number;
  quantity: number;
  unit_price: number;
}

export interface PurchaseOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
}
```

- [ ] **Step 2: 更新 API service**

```typescript
// frontend/src/services/api.ts — subscriptionApi 新增 get
export const subscriptionApi = {
  create: (data: any) => api.post('/subscription-orders', data).then(r => r.data),
  deduct: (id: number, data: any) => api.post(`/subscription-orders/${id}/deduct`, data).then(r => r.data),
  list: () => api.get('/subscription-orders').then(r => r.data),
  get: (id: number) => api.get(`/subscription-orders/${id}`).then(r => r.data),
};

// 删除 shelfApi

// inventoryApi 返回类型变化
export const inventoryApi = {
  list: () => api.get('/inventory').then(r => r.data),
};
```

- [ ] **Step 3: 重写 SubscriptionsPage（创建表单 + 列表）**

```tsx
// frontend/src/pages/SubscriptionsPage.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { CustomerSelect } from '../components/business/CustomerSelect';
import { subscriptionApi, customerApi } from '../services/api';

export default function SubscriptionsPage() {
  const navigate = useNavigate();
  const [customerId, setCustomerId] = useState<number | string>('');
  const [paidAmount, setPaidAmount] = useState(0);
  const [isPaid, setIsPaid] = useState(true);
  const [note, setNote] = useState('');
  const [orders, setOrders] = useState<any[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<number, string>>({});

  useEffect(() => {
    subscriptionApi.list().then(setOrders);
    customerApi.list().then((data: any) =>
      setCustomerNames(Object.fromEntries(data.map((c: any) => [c.id, c.name])))
    );
  }, []);

  const handleCreate = async () => {
    if (!customerId || paidAmount <= 0) { alert('请填写完整'); return; }
    await subscriptionApi.create({
      customer_id: Number(customerId),
      paid_amount: paidAmount,
      is_paid: isPaid,
      note,
    });
    alert('订奶单创建成功');
    setCustomerId(''); setPaidAmount(0); setIsPaid(true); setNote('');
    subscriptionApi.list().then(setOrders);
  };

  const statusLabel = (s: string) =>
    s === 'active' ? '进行中' : s === 'completed' ? '已完成' : s === 'cancelled' ? '已取消' : s;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">订奶管理</h2>

      {/* 创建表单 */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <h3 className="font-semibold">新建订奶单</h3>
        <div>
          <label className="text-sm font-medium text-gray-700">客户</label>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
        </div>
        <Input
          label="实付金额"
          type="number"
          value={String(paidAmount)}
          onChange={(e) => setPaidAmount(Number(e.target.value))}
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isPaid} onChange={(e) => setIsPaid(e.target.checked)} />
          已收款
        </label>
        <Input placeholder="备注（可选）" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button onClick={handleCreate}>创建订奶单</Button>
      </div>

      {/* 列表 */}
      <h3 className="text-lg font-semibold mb-2">订奶单列表</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-gray-600">
              <th className="px-4 py-2">#</th>
              <th className="px-4 py-2">客户</th>
              <th className="px-4 py-2">实付金额</th>
              <th className="px-4 py-2">剩余金额</th>
              <th className="px-4 py-2">状态</th>
              <th className="px-4 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o: any) => (
              <tr key={o.id} className="border-b">
                <td className="px-4 py-2">#{o.id}</td>
                <td className="px-4 py-2">{customerNames[o.customer_id] || `客户#${o.customer_id}`}</td>
                <td className="px-4 py-2">¥{o.paid_amount}</td>
                <td className="px-4 py-2 font-medium">¥{o.remaining_amount}</td>
                <td className="px-4 py-2">{statusLabel(o.status)}</td>
                <td className="px-4 py-2">
                  <Button size="sm" variant="secondary" onClick={() => navigate(`/subscriptions/${o.id}`)}>
                    详情
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 创建 SubscriptionDetailPage（详情 + 扣减弹窗）**

```tsx
// frontend/src/pages/SubscriptionDetailPage.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { ProductSelect } from '../components/business/ProductSelect';
import { subscriptionApi, customerApi, productApi } from '../services/api';

interface DeductItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

export default function SubscriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<any>(null);
  const [customerName, setCustomerName] = useState('');
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  // 扣减弹窗
  const [deductOpen, setDeductOpen] = useState(false);
  const [deductItems, setDeductItems] = useState<DeductItemRow[]>([
    { product_id: 0, quantity: 1, unit_price: 0, is_promo: false },
  ]);

  const loadOrder = async () => {
    const data = await subscriptionApi.get(Number(id));
    setOrder(data);
    customerApi.get(data.customer_id).then((c: any) => setCustomerName(c.name));
  };

  useEffect(() => {
    loadOrder();
    productApi.list().then((data: any) =>
      setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name])))
    );
  }, [id]);

  const updateDeductItem = (idx: number, field: keyof DeductItemRow, value: number | boolean) => {
    setDeductItems(prev =>
      prev.map((item, i) => {
        if (i !== idx) return item;
        const updated = { ...item, [field]: value };
        // 选赠送时 unit_price 强制为 0
        if (field === 'is_promo' && value === true) {
          updated.unit_price = 0;
        }
        return updated;
      })
    );
  };

  const paidTotal = deductItems
    .filter(i => !i.is_promo)
    .reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  const handleDeduct = async () => {
    if (deductItems.some(i => !i.product_id || !i.quantity)) {
      alert('请填写完整信息'); return;
    }
    try {
      await subscriptionApi.deduct(Number(id), { items: deductItems });
      alert('扣减成功');
      setDeductOpen(false);
      setDeductItems([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);
      loadOrder();
    } catch (err: any) {
      alert(err?.response?.data?.detail || '扣减失败');
    }
  };

  if (!order) return <div className="text-center py-8 text-gray-400">加载中...</div>;

  const statusLabel = (s: string) =>
    s === 'active' ? '进行中' : s === 'completed' ? '已完成' : s === 'cancelled' ? '已取消' : s;

  return (
    <div>
      <button onClick={() => navigate('/subscriptions')} className="text-blue-600 text-sm mb-4 block">
        &larr; 返回订奶列表
      </button>

      {/* 概要 */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <h2 className="text-lg font-bold mb-3">订奶单 #{order.id}</h2>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div><span className="text-gray-500">客户:</span> {customerName}</div>
          <div><span className="text-gray-500">实付金额:</span> ¥{order.paid_amount}</div>
          <div>
            <span className="text-gray-500">剩余金额:</span>{' '}
            <strong className={order.remaining_amount > 0 ? 'text-green-600' : 'text-gray-400'}>
              ¥{order.remaining_amount}
            </strong>
          </div>
          <div><span className="text-gray-500">状态:</span> {statusLabel(order.status)}</div>
          <div><span className="text-gray-500">备注:</span> {order.note || '-'}</div>
          <div><span className="text-gray-500">创建时间:</span> {new Date(order.created_at).toLocaleDateString()}</div>
        </div>
        {order.status === 'active' && (
          <div className="mt-4">
            <Button onClick={() => setDeductOpen(true)}>配送扣减</Button>
          </div>
        )}
      </div>

      {/* 扣减记录 */}
      <h3 className="text-lg font-semibold mb-2">扣减记录</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        {order.deductions?.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-gray-600">
                <th className="px-4 py-2">产品</th>
                <th className="px-4 py-2">数量</th>
                <th className="px-4 py-2">单价</th>
                <th className="px-4 py-2">小计</th>
                <th className="px-4 py-2">时间</th>
              </tr>
            </thead>
            <tbody>
              {order.deductions.map((d: any) => (
                <tr key={d.id} className="border-b">
                  <td className="px-4 py-2">{productNames[d.product_id] || `产品#${d.product_id}`}</td>
                  <td className="px-4 py-2">{d.quantity}</td>
                  <td className="px-4 py-2">¥{d.unit_price}</td>
                  <td className="px-4 py-2">¥{(d.quantity * d.unit_price).toFixed(2)}</td>
                  <td className="px-4 py-2">{new Date(d.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-8 text-gray-400">暂无扣减记录</div>
        )}
      </div>

      {/* 扣减弹窗 */}
      <Modal open={deductOpen} onClose={() => setDeductOpen(false)} title="配送扣减">
        <div className="space-y-3">
          {deductItems.map((item, idx) => (
            <div key={idx} className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-gray-500">产品</label>
                <ProductSelect value={item.product_id} onChange={(v) => updateDeductItem(idx, 'product_id', v)} onlyInStock />
              </div>
              <div className="w-20">
                <label className="text-xs text-gray-500">数量</label>
                <Input type="number" value={String(item.quantity)} onChange={(e) => updateDeductItem(idx, 'quantity', Number(e.target.value))} />
              </div>
              <div className="w-24">
                <label className="text-xs text-gray-500">单价</label>
                <Input type="number" value={String(item.unit_price)} onChange={(e) => updateDeductItem(idx, 'unit_price', Number(e.target.value))} disabled={item.is_promo} />
              </div>
              <label className="flex items-center gap-1 text-xs pb-2">
                <input type="checkbox" checked={item.is_promo} onChange={(e) => updateDeductItem(idx, 'is_promo', e.target.checked)} />
                赠送
              </label>
              <Button variant="danger" size="sm" onClick={() => setDeductItems(deductItems.filter((_, i) => i !== idx))} disabled={deductItems.length <= 1}>×</Button>
            </div>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setDeductItems([...deductItems, { product_id: 0, quantity: 1, unit_price: 0, is_promo: false }])}>+ 加行</Button>

          <div className="border-t pt-3 text-sm space-y-1">
            <div>本次扣减合计: <strong>¥{paidTotal.toFixed(2)}</strong></div>
            <div>剩余余额: ¥{order.remaining_amount} → ¥{(order.remaining_amount - paidTotal).toFixed(2)}</div>
            {paidTotal > order.remaining_amount && (
              <div className="text-red-600 font-medium">超出余额，无法提交</div>
            )}
          </div>
          <Button onClick={handleDeduct} disabled={paidTotal > order.remaining_amount}>确认扣减</Button>
        </div>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 5: 更新 SalesPage — 去 shelf_id，新增赠送勾选**

```tsx
// frontend/src/pages/SalesPage.tsx — 改动点
// 1. 去掉 shelf_id 相关 state 和 UI
// 2. SaleItem 接口去 shelf_id，新增 is_promo
// 3. 新增赠送勾选列

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_promo: boolean;
}

// 初始状态去掉 shelf_id
const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_price: 0, is_promo: false }]);

// 去掉 shelves 加载和货架选择 UI
// 在每行末尾加赠送勾选:
<label className="flex items-center gap-1 text-xs pb-2">
  <input type="checkbox" checked={item.is_promo} onChange={(e) => updateItem(idx, 'is_promo', e.target.checked)} />
  赠送
</label>

// submit 中去掉 shelf_id 校验:
if (items.some(i => !i.product_id || !i.quantity)) { alert('请填写完整信息'); return; }
```

- [ ] **Step 6: 更新 DeliveriesPage — 去 shelf_id，新增赠送勾选**

与 SalesPage 类似的改造：
1. `DeliveryItem` 接口去掉 `shelf_id`，新增 `is_promo`
2. 去掉货架选择 UI
3. 每行新增赠送勾选
4. submit 校验中去掉 `shelf_id`

- [ ] **Step 7: 更新 WastagePage — 去 shelf_id**

```tsx
// 去掉 shelf_id 相关字段和 UI
interface WastageItem {
  product_id: number;
  quantity: number;
  reason: string;
}
// 去掉货架选择列
```

- [ ] **Step 8: 更新 ReturnsPage — 去 shelf_id**

```tsx
// 去掉 shelf_id，接口改为:
interface ReturnItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
  is_wasted: boolean;
}
// 去掉货架选择列和 shelves 加载
```

- [ ] **Step 8b: 更新 PurchasesPage — 去 shelf_id**

```tsx
// frontend/src/pages/PurchasesPage.tsx — 改动点
// 1. ItemRow 去 shelf_id:
interface ItemRow {
  product_id: number;
  quantity: number;
  unit_price: number;
}
// 2. 初始状态去 shelf_id，state 声明去掉 shelves 相关
// 3. 表单中去掉货架选择列
// 4. submit 校验中去掉 i.shelf_id
// 5. 详情弹窗中去掉货架列展示和 shelf_name
```

- [ ] **Step 8c: 更新 DashboardPage — 去 shelf_id**

```tsx
// frontend/src/pages/DashboardPage.tsx — 改动点
// 1. 去掉 shelfApi import 和加载
// 2. low_stock 展示中去掉 shelfNames 引用:
//    <span>{productNames[item.product_id] || `产品#${item.product_id}`} 库存: {item.stock}</span>
```

- [ ] **Step 9: 更新 InventoryPage — 去 shelf_id 展示**

```tsx
// frontend/src/pages/InventoryPage.tsx
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi, productApi } from '../services/api';
import { Button } from '../components/ui/Button';

export default function InventoryPage() {
  const { data: inventory = [], isLoading } = useQuery({ queryKey: ['inventory'], queryFn: dashboardApi.getInventory });
  const [productNames, setProductNames] = useState<Record<number, string>>({});

  useEffect(() => {
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">库存总览</h2><Button variant="secondary" size="sm" onClick={() => window.open('/api/inventory/export')}>导出 CSV</Button></div>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
            <th className="px-4 py-3">产品</th><th className="px-4 py-3">库存数量</th>
          </tr></thead>
          <tbody>
            {isLoading ? <tr><td colSpan={2} className="text-center py-8 text-gray-400">加载中...</td></tr> :
              inventory.length === 0 ? <tr><td colSpan={2} className="text-center py-8 text-gray-400">暂无库存</td></tr> :
                inventory.map((item: any, i: number) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">{productNames[item.product_id] || `产品#${item.product_id}`}</td>
                    <td className="px-4 py-3 font-medium">{item.stock}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 10: 更新 App.tsx 路由和 Layout.tsx 导航**

```tsx
// App.tsx — 新增路由
import SubscriptionDetailPage from './pages/SubscriptionDetailPage';
// ...
<Route path="/subscriptions/:id" element={<SubscriptionDetailPage />} />

// Layout.tsx navItems — 删除 shelves 导航项
// 去掉 { to: '/shelves', label: '货架' }
```

- [ ] **Step 11: 启动前端验证**

```bash
cd frontend && npm run dev
# 访问页面: 订奶列表、详情、扣减弹窗、销售页、送货单页
```

- [ ] **Step 12: Commit**

```bash
git add frontend/src/
git commit -m "feat: 前端改造 — 订奶金额模式、详情页、赠送勾选、去 shelf_id"
```

---

### 自检清单

**1. Spec 覆盖检查：**

| Spec 要求 | 对应 Task |
|-----------|----------|
| retail_orders 表 | Task 1 |
| StockMovement 改列 | Task 1, 2 |
| Transaction 改列 | Task 1, 2 |
| shelves 表删除 | Task 8 (去路由), Task 9 (去前端) |
| SubscriptionOrder 列改名 | Task 1 |
| 订奶创建新逻辑 | Task 3, 4 |
| 订奶扣减新逻辑(cogs/promo/unit_price解析) | Task 3, 4 |
| 零售出库(cogs+retail_order) | Task 3, 5 |
| 促销赠送各入口 | Task 5, 7, 9 |
| 损耗记账(wastage Transaction) | Task 3, 6 |
| category 映射对照 | Task 4, 5, 6, 7 |
| API 修改+新增 | Task 8 |
| 前端: 列表/创建/扣减/详情/赠送入口 | Task 9 |
| dashboard/receivables 适配 | Task 2, 8 |
| shelves 相关全部清除 (后端+前端) | Task 1, 2, 3, 5, 6, 7, 8, 9 |
| PurchasesPage 去 shelf_id | Task 9 |
| DashboardPage 去 shelf_id | Task 9 |

**2. Placeholder 扫描：** 无 TBD/TODO/待实现。

**3. Type 一致性：**
- `SubscriptionOrder.paid_amount` / `remaining_amount` 前后端一致
- `SubscriptionDeduct.items[].is_promo` 前后端一致
- `StockMovement.reason` 值列表: purchase/return/wastage/exchange/cancel/retail/subscription/distribution
- `Transaction.category` 值列表: payment/retail/subscription/distribution/purchase/refund/cogs/promo/wastage

**4. 待确认事项：**
- 现有数据库中 `subscription_orders` 历史数据的 `total_bottles`/`paid_bottles`/`free_bottles` 列在 SQLite `RENAME COLUMN` 后不会自动删除，需手动处理（不在本期范围）
- `shelves` 物理表删除手工操作：`DROP TABLE shelves`（SQLite 支持），前端删除后不会报错
- `stock_movements` 历史数据的 `shelf_id` 列保留但不再写入（SQLite 不支持 DROP COLUMN）
- `unit_price` 解析逻辑复用 `CustomerService.resolve_product_price` 现有模式：专属价 → 等级(批发价) → 零售价，已验证模型存在

---

### 执行顺序

```
Task 1 (模型) → Task 2 (repo) → Task 3 (schema)
                                     ↓
Task 4 (subscription service) ←────────┘
Task 5 (sale service)          ←────────┘
Task 6 (wastage service)       ←────────┘
Task 7 (delivery/return/purchase service)
                                     ↓
Task 8 (API) ←──────────────────────┘
Task 9 (前端) ← 可与 Task 8 并行
```

Task 1-3 必须顺序执行（有依赖），Task 4-7 可部分并行（都依赖 Task 3 的 schema），Task 8-9 在所有 service 完成后执行。
