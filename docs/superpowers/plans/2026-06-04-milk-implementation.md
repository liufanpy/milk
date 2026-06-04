# 奶记重建实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零重建快消品代理商经营记录系统，支持完整进出货+收付款记录，库存和应收自动准确

**Architecture:** 后端 FastAPI 四层架构（API→Service→Repository→Model），前端 React+React Query+Zustand，SQLite 单机部署

**Tech Stack:** Python FastAPI + SQLAlchemy + SQLite + React 19 + TypeScript + TailwindCSS + React Query + Zustand + Vite

**Repo:** `/Users/liufan/program/milk`

---

## Phase 1: 后端基础设施

### Task 1: 项目脚手架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 requirements.txt**

```
fastapi==0.115.*
uvicorn[standard]==0.34.*
sqlalchemy==2.0.*
alembic==1.14.*
pydantic==2.*
pydantic-settings==2.*
python-dotenv==1.*
```

- [ ] **Step 2: 创建 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///milk.db"
    app_name: str = "奶记"
    debug: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: 创建 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建 main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 安装依赖并验证启动**

```bash
cd /Users/liufan/program/milk/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
# 访问 http://localhost:8000/api/health 应返回 {"status":"ok"}
```

- [ ] **Step 6: Commit**

```bash
cd /Users/liufan/program/milk
git add backend/
git commit -m "feat: backend scaffolding with FastAPI + SQLAlchemy"
```

---

### Task 2: 数据库模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/product.py`
- Create: `backend/app/models/customer.py`
- Create: `backend/app/models/supplier.py`
- Create: `backend/app/models/shelf.py`
- Create: `backend/app/models/stock_movement.py`
- Create: `backend/app/models/transaction.py`
- Create: `backend/app/models/delivery.py`
- Create: `backend/app/models/subscription_order.py`
- Create: `backend/app/models/product_customer_price.py`
- Create: `backend/app/models/operation_log.py`

- [ ] **Step 1: 创建 Product 模型**

```python
# backend/app/models/product.py
from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(100), default="")
    category = Column(String(50), default="")  # 鲜奶/酸奶/常温奶
    unit = Column(String(20), default="箱")
    barcode = Column(String(100), default="")
    default_retail_price = Column(Float, default=0.0)
    default_wholesale_price = Column(Float, default=0.0)
    shelf_life_days = Column(Integer, default=0)
```

- [ ] **Step 2: 创建 Customer 模型**

```python
# backend/app/models/customer.py
from sqlalchemy import Column, Integer, String
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(50), default="")
    address = Column(String(500), default="")
    price_tier = Column(String(20), default="retail")  # wholesale/retail/subscription
    default_payment = Column(String(20), default="immediate")  # immediate/credit
```

- [ ] **Step 3: 创建 Supplier 模型**

```python
# backend/app/models/supplier.py
from sqlalchemy import Column, Integer, String
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(100), default="")
    phone = Column(String(50), default="")
```

- [ ] **Step 4: 创建 Shelf 模型**

```python
# backend/app/models/shelf.py
from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
```

- [ ] **Step 5: 创建 StockMovement 模型**

```python
# backend/app/models/stock_movement.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    shelf_id = Column(Integer, ForeignKey("shelves.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # in / out
    reason = Column(String(30), nullable=False)  # purchase/sale/return/wastage/transfer/adjust
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, default=0.0)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True)
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 6: 创建 Transaction 模型**

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
    category = Column(String(30), nullable=False)  # sale/payment/subscription/refund/purchase
    amount = Column(Float, nullable=False)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: 创建 Delivery 模型**

```python
# backend/app/models/delivery.py
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    delivery_date = Column(Date, default=date.today)
    status = Column(String(20), default="pending")  # pending/delivered
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 8: 创建 SubscriptionOrder 模型**

```python
# backend/app/models/subscription_order.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class SubscriptionOrder(Base):
    __tablename__ = "subscription_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    total_bottles = Column(Integer, nullable=False)
    paid_bottles = Column(Integer, default=0)
    free_bottles = Column(Integer, default=0)
    remaining_bottles = Column(Integer, nullable=False)
    status = Column(String(20), default="active")  # active/completed/cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 9: 创建 ProductCustomerPrice 模型**

```python
# backend/app/models/product_customer_price.py
from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.database import Base


class ProductCustomerPrice(Base):
    __tablename__ = "product_customer_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    price = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "customer_id", name="uq_product_customer"),
    )
```

- [ ] **Step 10: 创建 OperationLog 模型**

```python
# backend/app/models/operation_log.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False)  # create/update/delete
    entity_type = Column(String(50), nullable=False)  # product/customer/...
    entity_id = Column(Integer, nullable=True)
    changes = Column(Text, default="{}")  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 11: 创建 models/__init__.py 导入所有模型**

```python
from app.models.product import Product
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.shelf import Shelf
from app.models.stock_movement import StockMovement
from app.models.transaction import Transaction
from app.models.delivery import Delivery
from app.models.subscription_order import SubscriptionOrder
from app.models.product_customer_price import ProductCustomerPrice
from app.models.operation_log import OperationLog
```

- [ ] **Step 12: 验证模型可创建表**

```bash
cd /Users/liufan/program/milk/backend
source venv/bin/activate
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine); print('OK')"
```

- [ ] **Step 13: Commit**

```bash
cd /Users/liufan/program/milk
git add backend/app/models/
git commit -m "feat: all 10 database models"
```

---

### Task 3: Alembic 迁移初始化

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: 初始化 Alembic**

```bash
cd /Users/liufan/program/milk/backend
source venv/bin/activate
pip install alembic
alembic init alembic
```

- [ ] **Step 2: 修改 alembic/env.py 指向我们的 models**

找到 `target_metadata = None` 替换为：

```python
from app.database import Base
from app.models import *  # noqa: F401,F403
target_metadata = Base.metadata
```

同时修改 `sqlalchemy.url` 读取方式：

```python
from app.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url)
```

- [ ] **Step 3: 生成初始迁移**

```bash
cd /Users/liufan/program/milk/backend
source venv/bin/activate
alembic revision --autogenerate -m "init"
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
cd /Users/liufan/program/milk
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: alembic migration setup"
```

---

### Task 4: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/product.py`
- Create: `backend/app/schemas/customer.py`
- Create: `backend/app/schemas/supplier.py`
- Create: `backend/app/schemas/shelf.py`
- Create: `backend/app/schemas/purchase.py`
- Create: `backend/app/schemas/sale.py`
- Create: `backend/app/schemas/delivery.py`
- Create: `backend/app/schemas/return_schema.py`
- Create: `backend/app/schemas/wastage.py`
- Create: `backend/app/schemas/settlement.py`
- Create: `backend/app/schemas/subscription.py`

- [ ] **Step 1: 创建 Product schemas**

```python
# backend/app/schemas/product.py
from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    brand: str = ""
    category: str = ""
    unit: str = "箱"
    barcode: str = ""
    default_retail_price: float = 0.0
    default_wholesale_price: float = 0.0
    shelf_life_days: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    barcode: Optional[str] = None
    default_retail_price: Optional[float] = None
    default_wholesale_price: Optional[float] = None
    shelf_life_days: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    name: str
    brand: str
    category: str
    unit: str
    barcode: str
    default_retail_price: float
    default_wholesale_price: float
    shelf_life_days: int

    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建 Customer schemas**

```python
# backend/app/schemas/customer.py
from pydantic import BaseModel, Field
from typing import Optional


class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=200)
    phone: str = ""
    address: str = ""
    price_tier: str = "retail"
    default_payment: str = "immediate"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    price_tier: Optional[str] = None
    default_payment: Optional[str] = None


class CustomerOut(BaseModel):
    id: int
    name: str
    phone: str
    address: str
    price_tier: str
    default_payment: str

    class Config:
        from_attributes = True
```

- [ ] **Step 3: 创建 Supplier schemas**

```python
# backend/app/schemas/supplier.py
from pydantic import BaseModel, Field
from typing import Optional


class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    contact: str = ""
    phone: str = ""


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None


class SupplierOut(BaseModel):
    id: int
    name: str
    contact: str
    phone: str

    class Config:
        from_attributes = True
```

- [ ] **Step 4: 创建 Shelf schemas**

```python
# backend/app/schemas/shelf.py
from pydantic import BaseModel, Field
from typing import Optional


class ShelfCreate(BaseModel):
    name: str = Field(..., max_length=200)
    customer_id: Optional[int] = None


class ShelfUpdate(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[int] = None


class ShelfOut(BaseModel):
    id: int
    name: str
    customer_id: Optional[int] = None

    class Config:
        from_attributes = True
```

- [ ] **Step 5: 创建 Purchase schema**

```python
# backend/app/schemas/purchase.py
from pydantic import BaseModel
from typing import List


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    shelf_id: int


class PurchaseCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseItem]
    note: str = ""
```

- [ ] **Step 6: 创建 Sale schema**

```python
# backend/app/schemas/sale.py
from pydantic import BaseModel
from typing import List, Optional


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None  # 散客可为空
    items: List[SaleItem]
    paid: bool = True
    note: str = ""
```

- [ ] **Step 7: 创建 Delivery schema**

```python
# backend/app/schemas/delivery.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DeliveryItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int


class DeliveryCreate(BaseModel):
    customer_id: int
    delivery_date: date
    items: List[DeliveryItem]
    paid: bool = False
    subscription_order_id: Optional[int] = None
    note: str = ""


class DeliveryOut(BaseModel):
    id: int
    customer_id: int
    delivery_date: date
    status: str
    subscription_order_id: Optional[int] = None
    note: str
    total_amount: float = 0.0
    paid_amount: float = 0.0
    unpaid_amount: float = 0.0

    class Config:
        from_attributes = True
```

- [ ] **Step 8: 创建 Return schema**

```python
# backend/app/schemas/return_schema.py
from pydantic import BaseModel
from typing import List, Optional


class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int
    is_wasted: bool = False  # 退回后是否直接报废


class ReturnCreate(BaseModel):
    customer_id: int
    delivery_id: Optional[int] = None  # 关联原送货单
    items: List[ReturnItem]
    note: str = ""
```

- [ ] **Step 9: 创建 Wastage schema**

```python
# backend/app/schemas/wastage.py
from pydantic import BaseModel
from typing import List


class WastageItem(BaseModel):
    product_id: int
    quantity: int
    shelf_id: int
    reason: str  # expired/damaged/self_consumed/giveaway/promotion


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
```

- [ ] **Step 10: 创建 Settlement schema**

```python
# backend/app/schemas/settlement.py
from pydantic import BaseModel


class SettlementCreate(BaseModel):
    amount: float
```

- [ ] **Step 11: 创建 Subscription schema**

```python
# backend/app/schemas/subscription.py
from pydantic import BaseModel
from typing import List, Optional


class SubscriptionCreate(BaseModel):
    customer_id: int
    total_amount: float
    total_bottles: int
    paid_bottles: int = 0
    free_bottles: int = 0


class SubscriptionDeduct(BaseModel):
    items: List["SubscriptionDeductItem"]
    shelf_id: int


class SubscriptionDeductItem(BaseModel):
    product_id: int
    quantity: int
```

- [ ] **Step 12: 创建 Exchange schema**

```python
# backend/app/schemas/delivery.py 底部追加
class ExchangeItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int


class ExchangeCreate(BaseModel):
    return_items: List[ExchangeItem]
    new_items: List[ExchangeItem]
```

- [ ] **Step 13: Commit**

```bash
cd /Users/liufan/program/milk
git add backend/app/schemas/
git commit -m "feat: pydantic schemas for all operations"
```

---

## Phase 2: 后端 CRUD 层

### Task 5: Base Repository

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/base.py`

- [ ] **Step 1: 创建 Base Repository**

```python
# backend/app/repositories/base.py
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, **kwargs) -> ModelType:
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        obj = self.get_by_id(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True
```

- [ ] **Step 2: Commit**

---

### Task 6: 产品 & 客户 & 供应商 & 货架 CRUD API

**Files:**
- Create: `backend/app/repositories/product_repo.py`
- Create: `backend/app/services/product_service.py`
- Create: `backend/app/api/products.py`
- Create: `backend/app/repositories/customer_repo.py`
- Create: `backend/app/services/customer_service.py`
- Create: `backend/app/api/customers.py`
- Create: `backend/app/repositories/supplier_repo.py`
- Create: `backend/app/services/supplier_service.py`
- Create: `backend/app/api/suppliers.py`
- Create: `backend/app/repositories/shelf_repo.py`
- Create: `backend/app/services/shelf_service.py`
- Create: `backend/app/api/shelves.py`
- Create: `backend/app/api/router.py`

每个模块结构相同，以 Product 为例：

- [ ] **Step 1: Product Repository**

```python
# backend/app/repositories/product_repo.py
from sqlalchemy.orm import Session
from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session):
        super().__init__(Product, db)

    def search(self, keyword: str = "", skip: int = 0, limit: int = 100):
        q = self.db.query(Product)
        if keyword:
            q = q.filter(Product.name.ilike(f"%{keyword}%"))
        return q.offset(skip).limit(limit).all()
```

- [ ] **Step 2: Product Service**

```python
# backend/app/services/product_service.py
from sqlalchemy.orm import Session
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)

    def list_products(self, keyword: str = ""):
        return self.repo.search(keyword)

    def get_product(self, product_id: int):
        return self.repo.get_by_id(product_id)

    def create_product(self, data: ProductCreate):
        return self.repo.create(**data.model_dump())

    def update_product(self, product_id: int, data: ProductUpdate):
        return self.repo.update(product_id, **data.model_dump(exclude_unset=True))

    def delete_product(self, product_id: int):
        return self.repo.delete(product_id)
```

- [ ] **Step 3: Product API**

```python
# backend/app/api/products.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


def get_product_service(db: Session = Depends(get_db)):
    return ProductService(db)


@router.get("", response_model=list[ProductOut])
def list_products(
    keyword: str = Query(""),
    svc: ProductService = Depends(get_product_service),
):
    return svc.list_products(keyword)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, svc: ProductService = Depends(get_product_service)):
    return svc.get_product(product_id)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, svc: ProductService = Depends(get_product_service)):
    return svc.create_product(data)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, svc: ProductService = Depends(get_product_service)):
    return svc.update_product(product_id, data)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, svc: ProductService = Depends(get_product_service)):
    svc.delete_product(product_id)
```

- [ ] **Step 4: Customer、Supplier、Shelf 按同样模式创建（Repository → Service → API）**

Customer API 额外包含专属价格接口：
```python
# 在 customers.py 中
@router.get("/{customer_id}/prices")
def get_customer_prices(customer_id: int, ...):
    ...

@router.post("/{customer_id}/prices")
def add_customer_price(customer_id: int, ...):
    ...

@router.delete("/{customer_id}/prices/{price_id}")
def delete_customer_price(customer_id: int, price_id: int, ...):
    ...
```

- [ ] **Step 5: 创建 router.py 汇总所有路由**

```python
# backend/app/api/router.py
from fastapi import APIRouter
from app.api import products, customers, suppliers, shelves

api_router = APIRouter()
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(suppliers.router)
api_router.include_router(shelves.router)
```

- [ ] **Step 6: 在 main.py 中注册路由**

```python
from app.api.router import api_router
app.include_router(api_router)
```

- [ ] **Step 7: Commit**

---

## Phase 3: 后端业务操作

### Task 7: 进货 & 直接销售

**Files:**
- Create: `backend/app/repositories/stock_movement_repo.py`
- Create: `backend/app/repositories/transaction_repo.py`
- Create: `backend/app/services/purchase_service.py`
- Create: `backend/app/api/purchases.py`
- Create: `backend/app/services/sale_service.py`
- Create: `backend/app/api/sales.py`

- [ ] **Step 1: StockMovement Repository**

```python
# backend/app/repositories/stock_movement_repo.py
from typing import List
from sqlalchemy.orm import Session
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

    def get_inventory(self) -> list:
        from sqlalchemy import func, case
        return (
            self.db.query(
                StockMovement.product_id,
                StockMovement.shelf_id,
                func.sum(
                    case(
                        (StockMovement.direction == "in", StockMovement.quantity),
                        (StockMovement.direction == "out", -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .group_by(StockMovement.product_id, StockMovement.shelf_id)
            .having(func.sum(
                case(
                    (StockMovement.direction == "in", StockMovement.quantity),
                    (StockMovement.direction == "out", -StockMovement.quantity),
                )
            ) != 0)
            .all()
        )
```

- [ ] **Step 2: Transaction Repository**

```python
# backend/app/repositories/transaction_repo.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
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
                func.case(
                    (Transaction.category == "sale", Transaction.amount),
                    (Transaction.category == "payment", -Transaction.amount),
                    (Transaction.category == "subscription", -Transaction.amount),
                    (Transaction.category == "refund", -Transaction.amount),
                    else_=0,
                )
            )
        ).filter(Transaction.customer_id == customer_id).scalar()
        return result or 0.0

    def get_receivables(self) -> list:
        return (
            self.db.query(
                Transaction.customer_id,
                func.sum(
                    func.case(
                        (Transaction.category == "sale", Transaction.amount),
                        (Transaction.category == "payment", -Transaction.amount),
                        (Transaction.category == "subscription", -Transaction.amount),
                        (Transaction.category == "refund", -Transaction.amount),
                        else_=0,
                    )
                ).label("ar_balance"),
            )
            .filter(Transaction.customer_id.isnot(None))
            .group_by(Transaction.customer_id)
            .having(
                func.sum(
                    func.case(
                        (Transaction.category == "sale", Transaction.amount),
                        (Transaction.category == "payment", -Transaction.amount),
                        (Transaction.category == "subscription", -Transaction.amount),
                        (Transaction.category == "refund", -Transaction.amount),
                        else_=0,
                    )
                ) != 0
            )
            .all()
        )
```

- [ ] **Step 3: Purchase Service（在一个事务里创建 StockMovement + Transaction）**

```python
# backend/app/services/purchase_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.purchase import PurchaseCreate


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_purchase(self, data: PurchaseCreate):
        total = 0.0
        movements = []
        for item in data.items:
            total += item.quantity * item.unit_cost
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "purchase",
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                supplier_id=data.supplier_id,
                category="purchase",
                amount=total,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items)}
```

- [ ] **Step 4: Sale Service**

```python
# backend/app/services/sale_service.py
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.sale import SaleCreate


class SaleService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_sale(self, data: SaleCreate):
        total = 0.0
        movements = []
        for item in data.items:
            amount = item.quantity * item.unit_price
            total += amount
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "sale",
                "quantity": item.quantity,
                "unit_cost": 0.0,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="sale",
                amount=total,
            )

        self.db.commit()
        return {"total": total, "item_count": len(data.items)}
```

- [ ] **Step 5: Purchases API + Sales API**

```python
# backend/app/api/purchases.py
router = APIRouter(prefix="/api/purchases", tags=["purchases"])

@router.post("", status_code=201)
def create_purchase(data: PurchaseCreate, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.create_purchase(data)

@router.get("")
def list_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    return svc.list_purchases()
```

```python
# backend/app/api/sales.py
router = APIRouter(prefix="/api/sales", tags=["sales"])

@router.post("", status_code=201)
def create_sale(data: SaleCreate, svc: SaleService = Depends(get_sale_service)):
    return svc.create_sale(data)

@router.get("")
def list_sales(svc: SaleService = Depends(get_sale_service)):
    return svc.list_sales()
```

- [ ] **Step 6: 注册新路由到 router.py，Commit**

---

### Task 8: 送货销售 & 换货

**Files:**
- Create: `backend/app/repositories/delivery_repo.py`
- Create: `backend/app/services/delivery_service.py`
- Create: `backend/app/api/deliveries.py`

- [ ] **Step 1: Delivery Repository**

```python
# backend/app/repositories/delivery_repo.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.delivery import Delivery


class DeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Delivery:
        d = Delivery(**kwargs)
        self.db.add(d)
        self.db.flush()
        return d

    def get_by_id(self, id: int) -> Optional[Delivery]:
        return self.db.query(Delivery).filter(Delivery.id == id).first()

    def list_by_customer(self, customer_id: int) -> List[Delivery]:
        return self.db.query(Delivery).filter(Delivery.customer_id == customer_id).all()

    def list_all(self, customer_id: Optional[int] = None, status: Optional[str] = None):
        q = self.db.query(Delivery)
        if customer_id:
            q = q.filter(Delivery.customer_id == customer_id)
        if status:
            q = q.filter(Delivery.status == status)
        return q.order_by(Delivery.delivery_date.desc()).all()
```

- [ ] **Step 2: Delivery Service — 在一个事务里创建 Delivery + StockMovement + Transaction**

```python
# backend/app/services/delivery_service.py
from sqlalchemy.orm import Session
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.delivery import DeliveryCreate


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_delivery(self, data: DeliveryCreate):
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
                "reason": "sale",
                "quantity": item.quantity,
                "unit_cost": 0.0,
                "delivery_id": delivery.id,
            })

        self.stock_repo.bulk_create(movements)

        if total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="sale",
                amount=total,
                delivery_id=delivery.id,
            )

        delivery.status = "delivered"
        self.db.commit()
        return {"id": delivery.id, "total": total}

    def get_delivery_detail(self, delivery_id: int):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            return None
        movements = self.stock_repo.get_by_delivery(delivery_id)
        transactions = self.txn_repo.get_by_delivery(delivery_id)

        sale_total = sum(t.amount for t in transactions if t.category == "sale")
        paid_total = sum(t.amount for t in transactions if t.category == "payment")

        return {
            "delivery": delivery,
            "items": movements,
            "total_amount": sale_total,
            "paid_amount": paid_total,
            "unpaid_amount": sale_total - paid_total,
        }

    def exchange(self, delivery_id: int, return_items: list, new_items: list):
        """换货：原送货单上退旧换新"""
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        return_total = 0.0
        for item in return_items:
            amt = item["quantity"] * item["unit_price"]
            return_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item["product_id"],
                "shelf_id": item["shelf_id"],
                "direction": "in",
                "reason": "return",
                "quantity": item["quantity"],
                "delivery_id": delivery_id,
            }])

        if return_total > 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="refund",
                amount=return_total,
                delivery_id=delivery_id,
            )

        new_total = 0.0
        for item in new_items:
            amt = item["quantity"] * item["unit_price"]
            new_total += amt
            self.stock_repo.bulk_create([{
                "product_id": item["product_id"],
                "shelf_id": item["shelf_id"],
                "direction": "out",
                "reason": "sale",
                "quantity": item["quantity"],
                "delivery_id": delivery_id,
            }])

        if new_total > 0:
            self.txn_repo.create(
                customer_id=delivery.customer_id,
                category="sale",
                amount=new_total,
                delivery_id=delivery_id,
            )

        self.db.commit()
        return {"return_total": return_total, "new_total": new_total}
```

- [ ] **Step 3: Deliveries API**

```python
# backend/app/api/deliveries.py
router = APIRouter(prefix="/api/deliveries", tags=["deliveries"])

@router.post("", status_code=201)
def create_delivery(data: DeliveryCreate, svc: DeliveryService = Depends(...)):
    return svc.create_delivery(data)

@router.get("")
def list_deliveries(customer_id: int = None, status: str = None, svc: ...):
    return svc.delivery_repo.list_all(customer_id, status)

@router.get("/{delivery_id}")
def get_delivery(delivery_id: int, svc: ...):
    return svc.get_delivery_detail(delivery_id)

@router.post("/{delivery_id}/exchange")
def exchange(delivery_id: int, data: ExchangeCreate, svc: ...):
    return svc.exchange(delivery_id, data.return_items, data.new_items)
```

- [ ] **Step 4: Commit**

---

### Task 9: 退货 & 损耗 & 结算 & 订奶

**Files:**
- Create: `backend/app/services/return_service.py`
- Create: `backend/app/api/returns.py`
- Create: `backend/app/services/wastage_service.py`
- Create: `backend/app/api/wastage.py`
- Create: `backend/app/services/settlement_service.py`
- Create: `backend/app/api/settlements.py`
- Create: `backend/app/repositories/subscription_order_repo.py`
- Create: `backend/app/services/subscription_service.py`
- Create: `backend/app/api/subscriptions.py`

四个业务 Service 按同样模式实现：

- [ ] **Step 1: Return Service**

```python
# backend/app/services/return_service.py
class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_return(self, data: ReturnCreate):
        refund_total = 0.0
        for item in data.items:
            self.stock_repo.bulk_create([{
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "in",
                "reason": "return",
                "quantity": item.quantity,
                "delivery_id": data.delivery_id,
            }])
            if item.is_wasted:
                self.stock_repo.bulk_create([{
                    "product_id": item.product_id,
                    "shelf_id": item.shelf_id,
                    "direction": "out",
                    "reason": "wastage",
                    "quantity": item.quantity,
                }])
            refund_total += item.quantity * item.unit_price

        if refund_total > 0:
            self.txn_repo.create(
                customer_id=data.customer_id,
                category="refund",
                amount=refund_total,
                delivery_id=data.delivery_id,
            )

        self.db.commit()
        return {"refund_total": refund_total}
```

- [ ] **Step 2: Wastage Service**

```python
# backend/app/services/wastage_service.py
class WastageService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)

    def create_wastage(self, data: WastageCreate):
        movements = []
        for item in data.items:
            movements.append({
                "product_id": item.product_id,
                "shelf_id": item.shelf_id,
                "direction": "out",
                "reason": "wastage",
                "quantity": item.quantity,
            })
        self.stock_repo.bulk_create(movements)
        self.db.commit()
        return {"item_count": len(data.items)}
```

- [ ] **Step 3: Settlement Service（部分结算）**

```python
# backend/app/services/settlement_service.py
class SettlementService:
    def __init__(self, db: Session):
        self.db = db
        self.txn_repo = TransactionRepository(db)
        self.delivery_repo = DeliveryRepository(db)

    def settle(self, delivery_id: int, amount: float):
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery:
            raise ValueError("送货单不存在")

        self.txn_repo.create(
            customer_id=delivery.customer_id,
            category="payment",
            amount=amount,
            delivery_id=delivery_id,
        )
        self.db.commit()
        return {"delivery_id": delivery_id, "paid": amount}
```

- [ ] **Step 4: Subscription Service**

```python
# backend/app/services/subscription_service.py
class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.sub_repo = SubscriptionOrderRepository(db)
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    def create_order(self, data: SubscriptionCreate):
        order = self.sub_repo.create(
            customer_id=data.customer_id,
            total_amount=data.total_amount,
            total_bottles=data.total_bottles,
            paid_bottles=data.paid_bottles,
            free_bottles=data.free_bottles,
            remaining_bottles=data.total_bottles,
            status="active",
        )
        self.txn_repo.create(
            customer_id=data.customer_id,
            category="subscription",
            amount=data.total_amount,
        )
        self.db.commit()
        return order

    def deduct(self, order_id: int, items: list, shelf_id: int):
        order = self.sub_repo.get_by_id(order_id)
        total_qty = sum(item.quantity for item in items)
        if order.remaining_bottles < total_qty:
            raise ValueError(f"瓶数不足，剩余 {order.remaining_bottles} 瓶")

        movements = []
        for item in items:
            movements.append({
                "product_id": item.product_id,
                "shelf_id": shelf_id,
                "direction": "out",
                "reason": "sale",
                "quantity": item.quantity,
                "subscription_order_id": order_id,
            })

        self.stock_repo.bulk_create(movements)
        order.remaining_bottles -= total_qty
        if order.remaining_bottles <= 0:
            order.status = "completed"
        self.db.commit()
        return {"remaining_bottles": order.remaining_bottles}
```

- [ ] **Step 5: 创建对应 API 路由，注册到 router.py，Commit**

---

### Task 10: 查询接口（库存/应收/看板/日志）

**Files:**
- Create: `backend/app/services/inventory_service.py`
- Create: `backend/app/api/inventory.py`
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/api/dashboard.py`
- Create: `backend/app/api/operation_logs.py`

- [ ] **Step 1: Inventory API**

```python
# backend/app/api/inventory.py
router = APIRouter(prefix="/api/inventory", tags=["inventory"])

@router.get("")
def get_inventory(db: Session = Depends(get_db)):
    repo = StockMovementRepository(db)
    rows = repo.get_inventory()
    return [
        {"product_id": r.product_id, "shelf_id": r.shelf_id, "stock": r.stock}
        for r in rows if r.stock != 0
    ]
```

- [ ] **Step 2: Receivables API**

```python
# backend/app/api/dashboard.py 中
@router.get("/api/receivables")
def get_receivables(db: Session = Depends(get_db)):
    repo = TransactionRepository(db)
    return repo.get_receivables()
```

- [ ] **Step 3: Dashboard API** — 今日销售/收款/库存预警/应收排行

- [ ] **Step 4: Operation Logs API** — GET /api/operation-logs

- [ ] **Step 5: Commit**

---

## Phase 4: 前端基础设施

### Task 11: 前端脚手架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: 初始化项目**

```bash
cd /Users/liufan/program/milk
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom @tanstack/react-query zustand axios
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: 配置 Tailwind**

```js
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

- [ ] **Step 3: 创建 App.tsx（路由壳 ≤50 行）**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import ProductsPage from './pages/ProductsPage'
// ... 其他页面

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/customers" element={<CustomersPage />} />
            {/* ... */}
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 4: 创建 types/index.ts** — 所有 TypeScript 类型定义

- [ ] **Step 5: 创建 services/api.ts** — axios 实例 + 所有 API 函数

- [ ] **Step 6: 创建 store/appStore.ts** — Zustand store（侧栏、弹窗等 UI 状态）

- [ ] **Step 7: 创建 Layout（Sidebar + Header）**

- [ ] **Step 8: 验证前端启动**

```bash
cd /Users/liufan/program/milk/frontend
npm run dev
# 访问 http://localhost:5173
```

- [ ] **Step 9: Commit**

---

### Task 12: 基础 UI 组件

**Files:**
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Input.tsx`
- Create: `frontend/src/components/ui/Table.tsx`
- Create: `frontend/src/components/ui/Modal.tsx`
- Create: `frontend/src/components/ui/Select.tsx`
- Create: `frontend/src/components/ui/Badge.tsx`
- Create: `frontend/src/components/business/ProductSelect.tsx`
- Create: `frontend/src/components/business/CustomerSelect.tsx`

- [ ] **Step 1-8: 逐个创建 UI 组件（Button, Input, Table, Modal, Select, Badge）**

- [ ] **Step 9: Commit**

---

## Phase 5: 前端页面

### Task 13: 产品/客户/供应商/货架管理页面

**Files:**
- Create: `frontend/src/pages/ProductsPage.tsx`
- Create: `frontend/src/hooks/useProducts.ts`
- Create: `frontend/src/pages/CustomersPage.tsx`
- Create: `frontend/src/hooks/useCustomers.ts`
- Create: `frontend/src/pages/SuppliersPage.tsx`
- Create: `frontend/src/pages/ShelvesPage.tsx`

每个页面模式相同：React Query hook + 列表 + 创建/编辑弹窗。

以 ProductsPage 为例：

```tsx
// hooks/useProducts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'

export function useProducts(keyword = '') {
  return useQuery({
    queryKey: ['products', keyword],
    queryFn: () => api.getProducts(keyword),
  })
}

export function useCreateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.createProduct,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}
// ... useUpdateProduct, useDeleteProduct
```

- [ ] **Step 1-4: 创建 hooks + pages for products, customers**
- [ ] **Step 5-6: 创建 suppliers, shelves pages**
- [ ] **Step 7: Commit**

---

### Task 14: 进货 & 直接销售页面

**Files:**
- Create: `frontend/src/pages/PurchasesPage.tsx`
- Create: `frontend/src/pages/SalesPage.tsx`

- [ ] **Step 1: PurchasesPage — 表单（选供应商 + 选产品 + 数量/进价 + 选货架）+ 历史列表**
- [ ] **Step 2: SalesPage — 表单（选客户/散客 + 选产品 + 数量/售价 + 选货架 + 已收/未收）+ 历史列表**
- [ ] **Step 3: Commit**

---

### Task 15: 送货单页面

**Files:**
- Create: `frontend/src/pages/DeliveriesPage.tsx`
- Create: `frontend/src/hooks/useDeliveries.ts`

- [ ] **Step 1: 送货单创建 — 选客户 + 日期 + 产品行（带价格建议）+ 是否已收**
- [ ] **Step 2: 送货单列表 — 按客户/日期/状态筛选，显示每单总金额/已付/未付**
- [ ] **Step 3: 送货单详情 — 品项明细 + 收款历史 + 换货按钮 + 结算入口**
- [ ] **Step 4: 换货弹窗 — 选要退的品项 + 选要换的新品项**
- [ ] **Step 5: 结算弹窗 — 输入金额，支持部分结算**
- [ ] **Step 6: Commit**

---

### Task 16: 退货/损耗/订奶页面

**Files:**
- Create: `frontend/src/pages/ReturnsPage.tsx`
- Create: `frontend/src/pages/WastagePage.tsx`
- Create: `frontend/src/pages/SubscriptionsPage.tsx`

- [ ] **Step 1: ReturnsPage — 选客户 + 选品项 + 是否报废 + 退款金额**
- [ ] **Step 2: WastagePage — 选品项 + 数量 + 损耗原因选择**
- [ ] **Step 3: SubscriptionsPage — 开单 + 扣减 + 状态查看**
- [ ] **Step 4: Commit**

---

### Task 17: 库存/应收/看板/日志页面

**Files:**
- Create: `frontend/src/pages/InventoryPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/pages/OperationLogsPage.tsx`

- [ ] **Step 1: InventoryPage — 按货架+产品显示库存，只显示有库存的**
- [ ] **Step 2: DashboardPage — 今日销售/收款/库存预警/应收排行**
- [ ] **Step 3: OperationLogsPage — 操作日志列表**
- [ ] **Step 4: Commit**

---

### Task 18: 种子数据

**Files:**
- Create: `backend/seed.py`

创建演示用种子数据：几个产品、几个客户、供应商、货架、几笔历史交易。

- [ ] **Step 1: 编写 seed.py**
- [ ] **Step 2: Commit**

---

## Phase 6: 整体验证

### Task 19: 端到端验证

- [ ] **Step 1: 启动后端 + 前端，走一遍完整流程**
  1. 创建产品 → 2. 创建客户 → 3. 创建货架 → 4. 进货 → 5. 查库存（增加）
  6. 创建送货单 → 7. 查库存（减少） → 8. 查应收（增加）
  9. 部分结算 → 10. 查应收（减少） → 11. 换货 → 12. 退货 → 13. 损耗
  14. 订奶开单 → 15. 订奶扣减 → 16. 查看操作日志

- [ ] **Step 2: 修复发现的问题**
- [ ] **Step 3: 最终 commit**

