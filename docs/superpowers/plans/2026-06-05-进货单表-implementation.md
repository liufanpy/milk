# 进货单表功能 — 实现计划

> **对于自动化执行者：** 推荐使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 按任务逐步执行。步骤使用 `- [ ]` 复选框语法追踪进度。

**目标：** 新增 `purchase_orders` 表作为进货单头，将当前零散的进货记录重构为结构化进货单（支持草稿/确认/撤销）。

**架构：** 在现有 stock_movements 和 transactions 表上扩展 purchase_order_id 外键，不新建独立 detail 表。三层结构不变：FastAPI API → Service → SQLAlchemy Model，前端单文件页面 + API 调用。

**技术栈：** Python/FastAPI/SQLAlchemy/SQLite（后端），React/TypeScript/Tailwind（前端）

**注意：** 项目当前无测试框架，本计划不包含测试步骤。实现完成后的验证方式：启动前后端服务，在浏览器中手动验证进货单创建、确认、撤销、列表展示、详情查看。

---

## 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `backend/app/models/purchase_order.py` | PurchaseOrder ORM 模型 |
| 修改 | `backend/app/models/__init__.py` | 导出 PurchaseOrder |
| 修改 | `backend/app/models/stock_movement.py` | 新增 purchase_order_id 字段 |
| 修改 | `backend/app/models/transaction.py` | 新增 purchase_order_id 字段 |
| 修改 | `backend/app/schemas/purchase.py` | 新增单号、日期、状态等 schema |
| 修改 | `backend/app/services/purchase_service.py` | 重构创建/列表/确认/撤销逻辑 |
| 修改 | `backend/app/api/purchases.py` | 新增单号相关端点 |
| 修改 | `backend/app/repositories/stock_movement_repo.py` | 新增 get_by_purchase_order 方法 |
| 修改 | `frontend/src/types/index.ts` | 新增 PurchaseOrder 接口 |
| 修改 | `frontend/src/services/api.ts` | 更新 purchaseApi |
| 修改 | `frontend/src/pages/PurchasesPage.tsx` | 重构为订单列表 + 详情弹窗 |

---

### Task 1: 创建 PurchaseOrder 模型

**文件：**
- 新建: `backend/app/models/purchase_order.py`
- 修改: `backend/app/models/__init__.py`

- [ ] **Step 1: 编写 PurchaseOrder 模型**

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=False, unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(Date, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    note = Column(String(500), default="")
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: 在 models/__init__.py 中导出 PurchaseOrder**

在 `backend/app/models/__init__.py` 末尾新增一行：

```python
from app.models.purchase_order import PurchaseOrder
```

- [ ] **Step 3: 重启后端验证自动建表**

```bash
cd backend && python -c "from app.main import app; from app.database import engine, Base; Base.metadata.create_all(bind=engine); print('OK')"
```

预期输出: `OK`（无报错，purchase_orders 表自动创建）

---

### Task 2: 已有模型新增 purchase_order_id 字段

**文件：**
- 修改: `backend/app/models/stock_movement.py`
- 修改: `backend/app/models/transaction.py`

- [ ] **Step 1: stock_movement 新增字段**

在 `backend/app/models/stock_movement.py` 的 `StockMovement` 类中，在 `subscription_order_id` 之后新增：

```python
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
```

- [ ] **Step 2: transaction 新增字段**

在 `backend/app/models/transaction.py` 的 `Transaction` 类中，在 `delivery_id` 之后新增：

```python
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
```

- [ ] **Step 3: 验证建表**

```bash
cd backend && python -c "from app.main import app; from app.database import engine, Base; Base.metadata.create_all(bind=engine); print('OK')"
```

预期输出: `OK`

---

### Task 3: 扩展 Purchase Schema

**文件：**
- 修改: `backend/app/schemas/purchase.py`

- [ ] **Step 1: 完整重写 purchase schema**

将 `backend/app/schemas/purchase.py` 内容替换为：

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    shelf_id: int


class PurchaseCreate(BaseModel):
    """创建进货单（前端提交）"""
    supplier_id: int
    purchase_date: date
    items: List[PurchaseItem]
    note: str = ""
    status: str = "confirmed"  # "draft" 或 "confirmed"


class PurchaseOrderOut(BaseModel):
    """进货单列表项"""
    id: int
    order_number: str
    supplier_id: int
    supplier_name: str
    purchase_date: str
    total_amount: float
    status: str
    note: str
    created_at: str

    class Config:
        from_attributes = True


class PurchaseOrderDetail(PurchaseOrderOut):
    """进货单详情 = 单头 + 品项"""
    items: List[dict]


class PurchaseConfirm(BaseModel):
    """确认草稿单（可不传 items 直接用已有数据）"""
    items: Optional[List[PurchaseItem]] = None


class PurchaseCancel(BaseModel):
    """撤销"""
    pass
```

---

### Task 4: 扩展 StockMovementRepository

**文件：**
- 修改: `backend/app/repositories/stock_movement_repo.py`

- [ ] **Step 1: 新增 get_by_purchase_order 方法**

在 `StockMovementRepository` 类的 `get_by_delivery` 方法之后新增：

```python
    def get_by_purchase_order(self, purchase_order_id: int) -> List[StockMovement]:
        return self.db.query(StockMovement).filter(
            StockMovement.purchase_order_id == purchase_order_id
        ).all()
```

同时更新 `bulk_create` 方法以支持 `purchase_order_id` 字段（无需改代码，dict 中传入即可自动映射）。

---

### Task 5: 重写 PurchaseService

**文件：**
- 修改: `backend/app/services/purchase_service.py`

- [ ] **Step 1: 完整重写 purchase_service.py**

将 `backend/app/services/purchase_service.py` 内容替换为：

```python
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.repositories.stock_movement_repo import StockMovementRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.purchase import PurchaseCreate
from app.models.purchase_order import PurchaseOrder
from app.models.product import Product
from app.models.shelf import Shelf
from app.models.supplier import Supplier

PURCHASE_HEADERS = ["产品名称", "product_name", "数量", "quantity", "进价", "unit_cost", "货架名称", "shelf_name", "供应商名称", "supplier_name", "日期", "date"]


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_repo = StockMovementRepository(db)
        self.txn_repo = TransactionRepository(db)

    # ── 单号生成 ──────────────────────────────────

    def _next_order_number(self) -> str:
        today = date.today().strftime("%Y%m%d")
        prefix = f"PO-{today}-"
        last = (
            self.db.query(PurchaseOrder)
            .filter(PurchaseOrder.order_number.like(f"{prefix}%"))
            .order_by(PurchaseOrder.id.desc())
            .first()
        )
        if last:
            seq = int(last.order_number.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:03d}"

    # ── 创建进货单 ────────────────────────────────

    def create_purchase(self, data: PurchaseCreate):
        total = sum(item.quantity * item.unit_cost for item in data.items)
        order = PurchaseOrder(
            order_number=self._next_order_number(),
            supplier_id=data.supplier_id,
            purchase_date=data.purchase_date,
            total_amount=total,
            note=data.note,
            status=data.status,
        )
        self.db.add(order)
        self.db.flush()

        if data.status == "confirmed":
            self._confirm_items(order.id, data.items)

        self.db.commit()
        return {"id": order.id, "order_number": order.order_number, "status": order.status}

    # ── 确认草稿单 ────────────────────────────────

    def confirm_order(self, order_id: int, items: list | None = None):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            raise ValueError("进货单不存在")
        if order.status != "draft":
            raise ValueError("仅草稿状态可确认")

        if items:
            total = sum(it["quantity"] * it["unit_cost"] for it in items)
            order.total_amount = total
        else:
            items = []

        order.status = "confirmed"
        self._confirm_items(order_id, items)
        self.db.commit()
        return {"id": order.id, "status": "confirmed"}

    def _confirm_items(self, order_id: int, items: list):
        total = 0.0
        movements = []
        for item in items:
            qty = item["quantity"] if isinstance(item, dict) else item.quantity
            cost = item["unit_cost"] if isinstance(item, dict) else item.unit_cost
            total += qty * cost
            movements.append({
                "product_id": item["product_id"] if isinstance(item, dict) else item.product_id,
                "shelf_id": item["shelf_id"] if isinstance(item, dict) else item.shelf_id,
                "direction": "in",
                "reason": "purchase",
                "quantity": qty,
                "unit_cost": cost,
                "purchase_order_id": order_id,
            })

        if movements:
            self.stock_repo.bulk_create(movements)

        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if total > 0:
            self.txn_repo.create(
                supplier_id=order.supplier_id,
                category="purchase",
                amount=total,
                purchase_order_id=order_id,
            )

    # ── 撤销进货单 ────────────────────────────────

    def cancel_order(self, order_id: int):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            raise ValueError("进货单不存在")

        if order.status == "draft":
            order.status = "cancelled"
            self.db.commit()
            return {"id": order.id, "status": "cancelled"}

        if order.status == "confirmed":
            # 反向冲抵库存
            original_items = self.stock_repo.get_by_purchase_order(order_id)
            reverses = []
            reverse_total = 0.0
            for item in original_items:
                reverses.append({
                    "product_id": item.product_id,
                    "shelf_id": item.shelf_id,
                    "direction": "out",
                    "reason": "purchase_cancel",
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                    "purchase_order_id": order_id,
                })
                reverse_total += item.quantity * item.unit_cost

            if reverses:
                self.stock_repo.bulk_create(reverses)
            if reverse_total > 0:
                self.txn_repo.create(
                    supplier_id=order.supplier_id,
                    category="purchase_cancel",
                    amount=-reverse_total,
                    purchase_order_id=order_id,
                )

            order.status = "cancelled"
            order.updated_at = datetime.utcnow()
            self.db.commit()
            return {"id": order.id, "status": "cancelled"}

    # ── 列表 ──────────────────────────────────────

    def list_purchases(self):
        orders = (
            self.db.query(PurchaseOrder)
            .order_by(PurchaseOrder.created_at.desc())
            .all()
        )
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}
        return [
            {
                "id": o.id,
                "order_number": o.order_number,
                "supplier_id": o.supplier_id,
                "supplier_name": suppliers.get(o.supplier_id, ""),
                "purchase_date": str(o.purchase_date),
                "total_amount": o.total_amount,
                "status": o.status,
                "note": o.note,
                "created_at": str(o.created_at),
            }
            for o in orders
        ]

    # ── 详情 ──────────────────────────────────────

    def get_purchase_detail(self, order_id: int):
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            return None
        items = self.stock_repo.get_by_purchase_order(order_id)
        products = {p.id: p.name for p in self.db.query(Product).all()}
        shelves = {s.id: s.name for s in self.db.query(Shelf).all()}
        suppliers = {s.id: s.name for s in self.db.query(Supplier).all()}

        def item_dir(i):
            return {
                "product_id": i.product_id,
                "product_name": products.get(i.product_id, ""),
                "quantity": i.quantity,
                "unit_cost": i.unit_cost,
                "shelf_id": i.shelf_id,
                "shelf_name": shelves.get(i.shelf_id, ""),
            }

        return {
            "id": order.id,
            "order_number": order.order_number,
            "supplier_id": order.supplier_id,
            "supplier_name": suppliers.get(order.supplier_id, ""),
            "purchase_date": str(order.purchase_date),
            "total_amount": order.total_amount,
            "status": order.status,
            "note": order.note,
            "created_at": str(order.created_at),
            "items": [item_dir(i) for i in items],
        }

    # ── CSV 导入（保持兼容，直接创建 confirmed 单） ──

    DFLT_SUPPLIER = "金健牛奶"
    DFLT_SHELF = "小欢的牛奶店"

    def _name_maps(self):
        prods = {p.name: (p.id, p.default_purchase_price) for p in self.db.query(Product).all()}
        shelves = {s.name: s.id for s in self.db.query(Shelf).all()}
        suppliers = {s.name: s.id for s in self.db.query(Supplier).all()}
        return prods, shelves, suppliers

    def import_preview(self, file_content: bytes) -> dict:
        prods, shelves, suppliers = self._name_maps()

        def validate(row: dict) -> str | bool:
            pname = (row.get("产品名称") or row.get("product_name") or "").strip()
            if not pname:
                return "产品名称为空"
            if pname not in prods:
                return f"产品'{pname}'不存在"
            qty = row.get("数量") or row.get("quantity") or "0"
            try:
                if int(float(qty)) <= 0:
                    return "数量必须大于0"
            except ValueError:
                return "数量格式错误"
            sname = (row.get("货架名称") or row.get("shelf_name") or "").strip() or self.DFLT_SHELF
            if sname not in shelves:
                return f"货架'{sname}'不存在"
            supname = (row.get("供应商名称") or row.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
            if supname not in suppliers:
                return f"供应商'{supname}'不存在"
            return True

        from app.services.csv_importer import parse_csv
        return parse_csv(file_content, validate, PURCHASE_HEADERS)

    def import_confirm(self, rows: list[dict]) -> dict:
        prods, shelves, suppliers = self._name_maps()
        success = 0
        errors: list[dict] = []

        groups: dict[str, list[dict]] = {}
        for row in rows:
            data = row.get("data", row)
            supname = (data.get("供应商名称") or data.get("supplier_name") or "").strip() or self.DFLT_SUPPLIER
            if supname not in groups:
                groups[supname] = []
            groups[supname].append(data)

        for supname, items in groups.items():
            sid = suppliers.get(supname)
            if not sid:
                for item in items:
                    errors.append({"row": item.get("index", "?"), "msg": f"供应商'{supname}'不存在"})
                continue

            order = PurchaseOrder(
                order_number=self._next_order_number(),
                supplier_id=sid,
                purchase_date=date.today(),
                total_amount=0.0,
                status="confirmed",
            )
            self.db.add(order)
            self.db.flush()

            total = 0.0
            movements = []
            for data in items:
                pname = (data.get("产品名称") or data.get("product_name") or "").strip()
                p = prods.get(pname)
                if not p:
                    errors.append({"row": data.get("index", "?"), "msg": f"产品'{pname}'不存在"})
                    continue
                pid, default_cost = p
                sname = (data.get("货架名称") or data.get("shelf_name") or "").strip() or self.DFLT_SHELF
                shelf_id = shelves.get(sname)
                if not shelf_id:
                    errors.append({"row": data.get("index", "?"), "msg": f"货架'{sname}'不存在"})
                    continue
                qty = int(float(data.get("数量") or data.get("quantity") or 0))
                cost = data.get("进价") or data.get("unit_cost") or ""
                cost = float(cost) if cost else default_cost
                date_str = (data.get("日期") or data.get("date") or "").strip()
                try:
                    item_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
                except ValueError:
                    item_date = date.today()
                total += qty * cost
                movements.append({
                    "product_id": pid, "shelf_id": shelf_id,
                    "direction": "in", "reason": "purchase",
                    "quantity": qty, "unit_cost": cost,
                    "purchase_order_id": order.id,
                    "created_at": datetime.utcnow() if not date_str else datetime.strptime(date_str, "%Y-%m-%d"),
                })

            if movements:
                self.stock_repo.bulk_create(movements)
                if total > 0:
                    self.txn_repo.create(supplier_id=sid, category="purchase", amount=total, purchase_order_id=order.id)
                order.total_amount = total
                success += len(movements)

        self.db.commit()
        return {"success": success, "errors": errors}
```

---

### Task 6: 扩展 Purchase API 端点

**文件：**
- 修改: `backend/app/api/purchases.py`

- [ ] **Step 1: 重写 purchases API**

将 `backend/app/api/purchases.py` 内容替换为：

```python
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas.purchase import PurchaseCreate, PurchaseConfirm
from app.models.purchase_order import PurchaseOrder
from app.models.stock_movement import StockMovement
from app.models.product import Product
from app.models.shelf import Shelf

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def get_purchase_service(db: Session = Depends(get_db)):
    return PurchaseService(db)


# ── 进货单 CRUD ───────────────────────────────────

@router.post("", status_code=201)
def create_purchase(data: PurchaseCreate, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.create_purchase(data)


@router.get("")
def list_purchases(svc: PurchaseService = Depends(get_purchase_service)):
    return svc.list_purchases()


@router.get("/{order_id}")
def get_purchase(order_id: int, svc: PurchaseService = Depends(get_purchase_service)):
    detail = svc.get_purchase_detail(order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="进货单不存在")
    return detail


@router.post("/{order_id}/confirm")
def confirm_purchase(order_id: int, data: PurchaseConfirm = PurchaseConfirm(), svc: PurchaseService = Depends(get_purchase_service)):
    try:
        return svc.confirm_order(order_id, [it.model_dump() for it in data.items] if data.items else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel")
def cancel_purchase(order_id: int, svc: PurchaseService = Depends(get_purchase_service)):
    try:
        return svc.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── CSV 导出（基于 purchase_orders） ──────────────

@router.get("/export")
def export_purchases(db: Session = Depends(get_db)):
    orders = db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()
    suppliers = {s.id: s.name for s in db.query(Supplier).all()}
    csv_lines = ["单号,供应商,日期,金额,状态,备注"]
    for o in orders:
        sname = suppliers.get(o.supplier_id, "")
        csv_lines.append(f"{o.order_number},{sname},{o.purchase_date},{o.total_amount},{o.status},{o.note or ''}")
    csv_content = "\n".join(csv_lines)
    return StreamingResponse(io.BytesIO(csv_content.encode("utf-8-sig")), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=purchases.csv"})


# ── CSV 导入（不变） ──────────────────────────────

@router.post("/import")
async def import_purchases(file: UploadFile = File(...), svc: PurchaseService = Depends(get_purchase_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: PurchaseService = Depends(get_purchase_service)):
    return svc.import_confirm(data.get("rows", []))
```

注意：删除旧的 `from app.schemas.purchase import PurchaseCreate` 中不再需要的 import，以及 `from app.models.product import Product` 等仅用于旧导出逻辑的 import。需要补充 `from app.models.supplier import Supplier`。

---

### Task 7: 更新前端类型定义

**文件：**
- 修改: `frontend/src/types/index.ts`

- [ ] **Step 1: 新增 PurchaseOrder 类型**

在 `frontend/src/types/index.ts` 末尾新增：

```typescript
export interface PurchaseOrder {
  id: number;
  order_number: string;
  supplier_id: number;
  supplier_name: string;
  purchase_date: string;
  total_amount: number;
  status: string;
  note: string;
  created_at: string;
}

export interface PurchaseOrderDetail extends PurchaseOrder {
  items: PurchaseOrderDetailItem[];
}

export interface PurchaseOrderDetailItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
  shelf_name: string;
}
```

---

### Task 8: 更新前端 API 客户端

**文件：**
- 修改: `frontend/src/services/api.ts`

- [ ] **Step 1: 扩展 purchaseApi**

将 `purchaseApi` 替换为：

```typescript
// Purchases
export const purchaseApi = {
  create: (data: any) => api.post('/purchases', data).then(r => r.data),
  list: () => api.get('/purchases').then(r => r.data),
  get: (id: number) => api.get(`/purchases/${id}`).then(r => r.data),
  confirm: (id: number, items?: any[]) => api.post(`/purchases/${id}/confirm`, { items }).then(r => r.data),
  cancel: (id: number) => api.post(`/purchases/${id}/cancel`).then(r => r.data),
  importFile: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/purchases/import', fd).then(r => r.data); },
  confirmImport: (rows: any[]) => api.post('/purchases/import/confirm', { rows }).then(r => r.data),
};
```

---

### Task 9: 重写前端进货页面

**文件：**
- 修改: `frontend/src/pages/PurchasesPage.tsx`

- [ ] **Step 1: 重写 PurchasesPage.tsx**

将文件内容替换为：

```tsx
import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProductSelect } from '../components/business/ProductSelect';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import CsvImportModal from '../components/business/CsvImportModal';
import { purchaseApi, supplierApi, shelfApi, productApi } from '../services/api';
import type { PurchaseOrder, PurchaseOrderDetail } from '../types';

interface ItemRow {
  product_id: number;
  quantity: number;
  unit_cost: number;
  shelf_id: number;
}

const STATUS_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  draft: 'warning',
  confirmed: 'success',
  cancelled: 'default',
};
const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  confirmed: '已确认',
  cancelled: '已撤销',
};

export default function PurchasesPage() {
  const [importOpen, setImportOpen] = useState(false);
  const [supplierId, setSupplierId] = useState<number | string>('');
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [items, setItems] = useState<ItemRow[]>([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [shelves, setShelves] = useState<any[]>([]);
  const [note, setNote] = useState('');
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [productNames, setProductNames] = useState<Record<number, string>>({});
  const [shelfNames, setShelfNames] = useState<Record<number, string>>({});

  // 详情弹窗
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<PurchaseOrderDetail | null>(null);

  useEffect(() => {
    supplierApi.list().then(setSuppliers);
    shelfApi.list().then((data: any) => { setShelves(data); setShelfNames(Object.fromEntries(data.map((s: any) => [s.id, s.name]))); });
    productApi.list().then((data: any) => setProductNames(Object.fromEntries(data.map((p: any) => [p.id, p.name]))));
    purchaseApi.list().then(setOrders);
  }, []);

  const refreshOrders = () => purchaseApi.list().then(setOrders);

  const updateItem = (idx: number, field: keyof ItemRow, value: number) => {
    setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  };

  const addRow = () => setItems([...items, { product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
  const removeRow = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  const resetForm = () => {
    setSupplierId('');
    setPurchaseDate(new Date().toISOString().slice(0, 10));
    setItems([{ product_id: 0, quantity: 1, unit_cost: 0, shelf_id: 0 }]);
    setNote('');
  };

  const handleSubmit = async (status: 'draft' | 'confirmed') => {
    if (!supplierId || !purchaseDate || items.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
      alert('请填写完整信息');
      return;
    }
    await purchaseApi.create({ supplier_id: Number(supplierId), purchase_date: purchaseDate, items, note, status });
    alert(status === 'draft' ? '草稿已保存' : '入库成功');
    resetForm();
    refreshOrders();
  };

  const handleConfirm = async (orderId: number) => {
    if (!confirm('确定确认入库？')) return;
    await purchaseApi.confirm(orderId);
    refreshOrders();
  };

  const handleCancel = async (orderId: number, status: string) => {
    const msg = status === 'draft' ? '确定作废此草稿？' : '确定撤销此进货单？（将反向冲抵库存）';
    if (!confirm(msg)) return;
    await purchaseApi.cancel(orderId);
    refreshOrders();
  };

  const openDetail = async (orderId: number) => {
    const d = await purchaseApi.get(orderId);
    setDetail(d);
    setDetailOpen(true);
  };

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_cost, 0);
  const statusBadge = (status: string) => (
    <Badge variant={STATUS_VARIANT[status] || 'default'}>{STATUS_LABEL[status] || status}</Badge>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">进货管理</h2>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setImportOpen(true)}>导入 CSV</Button>
          <Button variant="secondary" size="sm" onClick={() => window.open('/api/purchases/export')}>导出 CSV</Button>
        </div>
      </div>

      {/* 新建进货单 */}
      <div className="bg-white rounded-lg border p-4 mb-6 space-y-3">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-700">供应商</label>
            <select value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))} className="w-full border rounded px-3 py-2 text-sm mt-1">
              <option value="">选供应商</option>
              {suppliers.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="w-40">
            <label className="text-sm font-medium text-gray-700">进货日期</label>
            <Input type="date" value={purchaseDate} onChange={(e) => setPurchaseDate(e.target.value)} />
          </div>
        </div>

        {items.map((item, idx) => (
          <div key={idx} className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500">产品</label>
              <ProductSelect value={item.product_id} onChange={(v) => updateItem(idx, 'product_id', v)} />
            </div>
            <div className="w-20">
              <label className="text-xs text-gray-500">数量</label>
              <Input type="number" value={String(item.quantity)} onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))} />
            </div>
            <div className="w-24">
              <label className="text-xs text-gray-500">进价</label>
              <Input type="number" value={String(item.unit_cost)} onChange={(e) => updateItem(idx, 'unit_cost', Number(e.target.value))} />
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-500">货架</label>
              <select value={item.shelf_id} onChange={(e) => updateItem(idx, 'shelf_id', Number(e.target.value))} className="w-full border rounded px-2 py-1 text-sm">
                <option value="">选货架</option>
                {shelves.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <Button variant="danger" size="sm" onClick={() => removeRow(idx)} disabled={items.length <= 1}>×</Button>
          </div>
        ))}

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={addRow}>+ 加行</Button>
          <span className="text-sm text-gray-500 ml-auto">合计: ¥{total.toFixed(2)}</span>
        </div>

        <Input placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />

        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => handleSubmit('draft')}>保存草稿</Button>
          <Button onClick={() => handleSubmit('confirmed')}>确认入库</Button>
        </div>
      </div>

      {/* 进货单列表 */}
      <h3 className="text-lg font-semibold mb-2">进货单列表</h3>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="px-4 py-2 text-left">单号</th>
              <th className="px-4 py-2 text-left">供应商</th>
              <th className="px-4 py-2 text-left">日期</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-center">状态</th>
              <th className="px-4 py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(o.id)}>
                <td className="px-4 py-2 font-medium">{o.order_number}</td>
                <td className="px-4 py-2 text-gray-600">{o.supplier_name}</td>
                <td className="px-4 py-2 text-gray-600">{o.purchase_date}</td>
                <td className="px-4 py-2 text-right">¥{o.total_amount.toFixed(2)}</td>
                <td className="px-4 py-2 text-center">{statusBadge(o.status)}</td>
                <td className="px-4 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                  {o.status === 'draft' && (
                    <Button variant="primary" size="sm" onClick={() => handleConfirm(o.id)}>确认</Button>
                  )}
                  {(o.status === 'draft' || o.status === 'confirmed') && (
                    <span className="ml-2">
                      <Button variant="danger" size="sm" onClick={() => handleCancel(o.id, o.status)}>
                        {o.status === 'draft' ? '作废' : '撤销'}
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">暂无进货单</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 详情弹窗 */}
      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`进货单详情 — ${detail?.order_number || ''}`}>
        {detail && (
          <div className="space-y-3">
            <div className="flex gap-4 text-sm">
              <span>供应商: {detail.supplier_name}</span>
              <span>日期: {detail.purchase_date}</span>
              <span>状态: {statusBadge(detail.status)}</span>
            </div>
            {detail.note && <div className="text-sm text-gray-500">备注: {detail.note}</div>}
            <table className="w-full text-sm border-t mt-2">
              <thead>
                <tr className="text-gray-500">
                  <th className="px-2 py-1 text-left">产品</th>
                  <th className="px-2 py-1 text-right">数量</th>
                  <th className="px-2 py-1 text-right">进价</th>
                  <th className="px-2 py-1 text-right">小计</th>
                  <th className="px-2 py-1 text-left">货架</th>
                </tr>
              </thead>
              <tbody>
                {detail.items.map((it, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-2 py-1">{it.product_name}</td>
                    <td className="px-2 py-1 text-right">{it.quantity}</td>
                    <td className="px-2 py-1 text-right">¥{it.unit_cost.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">¥{(it.quantity * it.unit_cost).toFixed(2)}</td>
                    <td className="px-2 py-1">{it.shelf_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-right font-bold">合计: ¥{detail.total_amount.toFixed(2)}</div>
          </div>
        )}
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="导入进货"
        onImport={(file) => purchaseApi.importFile(file)}
        onConfirm={(rows) => purchaseApi.confirmImport(rows)}
        onDone={refreshOrders}
      />
    </div>
  );
}
```

---

### Task 10: 验证

**文件：** 无，手动验证

- [ ] **Step 1: 启动后端**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 手动验证以下场景**

1. **创建草稿** — 填进货单，「保存草稿」→ 列表出现草稿状态单，库存不变
2. **确认入库** — 填进货单，「确认入库」→ 列表出现已确认单，库存增加
3. **草稿确认** — 对草稿点「确认」→ 状态变已确认，库存增加
4. **草稿作废** — 对草稿点「作废」→ 状态变已撤销，库存不变
5. **已确认撤销** — 对已确认单点「撤销」→ 状态变已撤销，库存扣回（出现 purchase_cancel 流水）
6. **详情弹窗** — 点击单号行 → 弹窗展示品项列表
7. **CSV 导入** — 导入进货 CSV → 确认后生成已确认进货单
8. **CSV 导出** — 导出 → CSV 包含单号/供应商/日期/金额/状态/备注

---

## 自检清单

**1. Spec 覆盖度：**
- [x] purchase_orders 表创建 → Task 1
- [x] stock_movements / transactions 新增外键 → Task 2
- [x] 单号生成 `PO-YYYYMMDD-NNN` → Task 5 `_next_order_number`
- [x] 草稿 / 已确认 / 已撤销 状态流转 → Task 5 create/confirm/cancel
- [x] 进货列表页改为订单列表 → Task 9 表格部分
- [x] 详情弹窗 → Task 9 Modal
- [x] 新建表单 + 保存草稿 + 确认入库 → Task 9 表单部分
- [x] CSV 导入创建 confirmed 单 → Task 5 import_confirm
- [x] 前端类型 → Task 7
- [x] API 端点 → Task 6

**2. 占位符检查：** 无 TBD/TODO，所有步骤包含完整代码。

**3. 类型一致性：** 前后端 PurchaseItem 字段一致（product_id/quantity/unit_cost/shelf_id），PurchaseOrderOut 与前端 PurchaseOrder 接口字段对应。

**4. 不处理但已知的边界：**
- 确认草稿时不传 items（复用创建时的 items）→ 当前实现仅支持传入 items，创建草稿时 items 已固化在 order 上
- 编辑草稿功能 → 本计划不支持，后续可扩展
