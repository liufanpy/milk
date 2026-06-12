# 库存盘点功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为总仓库存新增盘点功能——创建盘点单、录入实盘数、确认锁定，纯记录不对库存做自动调整。

**Architecture:** 沿用现有 document + order + items 三层模式。新增 `InventoryCheck` / `InventoryCheckItem` 两个 model、一个 service、一个 API router。前端新增一个页面同时承载列表和详情。

**Tech Stack:** FastAPI + SQLAlchemy + React + TypeScript

---

### Task 1: 枚举 & 单号前缀

**Files:**
- Modify: `backend/app/enums.py:4-11`
- Modify: `backend/app/services/document_helpers.py:5-13`

- [ ] **Step 1: 在 DocumentType 枚举中新增 inventory_check**

```python
# backend/app/enums.py 第10行后插入
    inventory_check = "inventory_check"
```

- [ ] **Step 2: 在 PREFIX_MAP 中新增 IC 前缀**

```python
# backend/app/services/document_helpers.py 第12行后插入
    DocumentType.inventory_check: "IC",
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/enums.py backend/app/services/document_helpers.py
git commit -m "feat: 新增 inventory_check 枚举和 IC 单号前缀"
```

---

### Task 2: InventoryCheck 模型

**Files:**
- Create: `backend/app/models/inventory_check.py`
- Create: `backend/app/models/inventory_check_item.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 InventoryCheck 模型**

```python
# backend/app/models/inventory_check.py
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    check_date = Column(Date, default=date.today)
    status = Column(String(20), default="draft")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    confirmed_at = Column(DateTime, nullable=True)
```

- [ ] **Step 2: 创建 InventoryCheckItem 模型**

```python
# backend/app/models/inventory_check_item.py
from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class InventoryCheckItem(Base):
    __tablename__ = "inventory_check_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    theoretical_qty = Column(Integer, nullable=False, default=0)
    actual_qty = Column(Integer, nullable=True)
    difference = Column(Integer, nullable=False, default=0)
```

- [ ] **Step 3: 在 models/__init__.py 中注册**

在 `backend/app/models/__init__.py` 末尾追加：

```python
from app.models.inventory_check import InventoryCheck
from app.models.inventory_check_item import InventoryCheckItem
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/inventory_check.py backend/app/models/inventory_check_item.py backend/app/models/__init__.py
git commit -m "feat: 新增 InventoryCheck / InventoryCheckItem 模型"
```

---

### Task 3: InventoryCheckService

**Files:**
- Create: `backend/app/services/inventory_check_service.py`

- [ ] **Step 1: 创建 service 文件**

```python
# backend/app/services/inventory_check_service.py
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.enums import Direction, DocumentType
from app.models.document import Document
from app.models.inventory_check import InventoryCheck
from app.models.inventory_check_item import InventoryCheckItem
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.services.document_helpers import create_document


class InventoryCheckService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, check_date: date | None = None, note: str = "") -> dict:
        doc = create_document(self.db, DocumentType.inventory_check)
        order = InventoryCheck(
            document_id=doc.id,
            check_date=check_date or date.today(),
            note=note,
        )
        self.db.add(order)
        self.db.commit()
        return {"id": doc.id, "order_number": doc.order_number, "check_date": str(order.check_date), "status": order.status}

    def list_checks(self) -> list[dict]:
        orders = self.db.query(InventoryCheck).order_by(InventoryCheck.created_at.desc()).all()
        if not orders:
            return []

        doc_ids = [o.document_id for o in orders]
        docs = {d.id: d for d in self.db.query(Document).filter(Document.id.in_(doc_ids)).all()}

        result = []
        for o in orders:
            item_count = self.db.query(InventoryCheckItem).filter(
                InventoryCheckItem.document_id == o.document_id
            ).count()
            doc = docs.get(o.document_id)
            result.append({
                "id": o.document_id,
                "order_number": doc.order_number if doc else "",
                "check_date": str(o.check_date),
                "status": o.status,
                "item_count": item_count,
                "note": o.note,
                "confirmed_at": str(o.confirmed_at) if o.confirmed_at else None,
                "created_at": str(o.created_at),
            })
        return result

    def get_detail(self, document_id: int) -> dict | None:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            return None

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        products = {p.id: p for p in self.db.query(Product).all()}

        if order.status == "draft":
            return self._build_draft_detail(order, doc, products)

        items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).all()

        item_list = []
        for it in items:
            p = products.get(it.product_id)
            item_list.append({
                "product_id": it.product_id,
                "product_name": p.name if p else "",
                "theoretical_qty": it.theoretical_qty,
                "actual_qty": it.actual_qty,
                "difference": it.difference,
            })

        return {
            "id": document_id,
            "order_number": doc.order_number if doc else "",
            "check_date": str(order.check_date),
            "status": order.status,
            "note": order.note,
            "confirmed_at": str(order.confirmed_at) if order.confirmed_at else None,
            "created_at": str(order.created_at),
            "items": item_list,
        }

    def _build_draft_detail(self, order, doc, products: dict) -> dict:
        theoretical = self._compute_warehouse_inventory()

        saved_items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == order.document_id
        ).all()
        saved_map = {it.product_id: it for it in saved_items}

        item_list = []
        for pid, theo_qty in theoretical.items():
            saved = saved_map.get(pid)
            actual_qty = saved.actual_qty if saved else None
            difference = (actual_qty - theo_qty) if actual_qty is not None else None
            p = products.get(pid)
            item_list.append({
                "product_id": pid,
                "product_name": p.name if p else "",
                "theoretical_qty": theo_qty,
                "actual_qty": actual_qty,
                "difference": difference,
            })

        return {
            "id": order.document_id,
            "order_number": doc.order_number if doc else "",
            "check_date": str(order.check_date),
            "status": order.status,
            "note": order.note,
            "confirmed_at": None,
            "created_at": str(order.created_at),
            "items": item_list,
        }

    def _compute_warehouse_inventory(self) -> dict[int, int]:
        from sqlalchemy import func, case
        rows = (
            self.db.query(
                StockMovement.product_id,
                func.sum(
                    case(
                        (StockMovement.direction == Direction.in_, StockMovement.quantity),
                        (StockMovement.direction == Direction.out, -StockMovement.quantity),
                    )
                ).label("stock"),
            )
            .filter(StockMovement.store_id.is_(None))
            .group_by(StockMovement.product_id)
            .all()
        )
        return {r.product_id: (r.stock or 0) for r in rows}

    def save_items(self, document_id: int, items: list[dict]) -> dict:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            raise ValueError("盘点单不存在")
        if order.status != "draft":
            raise ValueError("只有草稿状态的盘点单可以修改")

        self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).delete()

        for it in items:
            self.db.add(InventoryCheckItem(
                document_id=document_id,
                product_id=it["product_id"],
                actual_qty=it.get("actual_qty"),
            ))

        self.db.commit()
        return {"id": document_id, "item_count": len(items)}

    def confirm(self, document_id: int) -> dict:
        order = self.db.query(InventoryCheck).filter(
            InventoryCheck.document_id == document_id
        ).first()
        if not order:
            raise ValueError("盘点单不存在")
        if order.status != "draft":
            raise ValueError("只有草稿状态的盘点单可以确认")

        theoretical = self._compute_warehouse_inventory()

        items = self.db.query(InventoryCheckItem).filter(
            InventoryCheckItem.document_id == document_id
        ).all()

        for it in items:
            theo = theoretical.get(it.product_id, 0)
            it.theoretical_qty = theo
            it.difference = (it.actual_qty or 0) - theo

        order.status = "confirmed"
        order.confirmed_at = datetime.now()
        self.db.commit()
        return {"id": document_id, "status": "confirmed"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/inventory_check_service.py
git commit -m "feat: 新增 InventoryCheckService 服务层"
```

---

### Task 4: InventoryChecks API

**Files:**
- Create: `backend/app/api/inventory_checks.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: 创建 API router**

```python
# backend/app/api/inventory_checks.py
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.inventory_check_service import InventoryCheckService

router = APIRouter(prefix="/api/inventory-checks", tags=["inventory-checks"])


class SaveItemsBody(BaseModel):
    items: list[dict]


@router.post("")
def create_inventory_check(
    check_date: str | None = Query(None),
    note: str = Query(""),
    db: Session = Depends(get_db),
):
    svc = InventoryCheckService(db)
    d = date.fromisoformat(check_date) if check_date else None
    return svc.create(check_date=d, note=note)


@router.get("")
def list_inventory_checks(db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    return svc.list_checks()


@router.get("/{document_id}")
def get_inventory_check(document_id: int, db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    result = svc.get_detail(document_id)
    if not result:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "盘点单不存在"}, status_code=404)
    return result


@router.put("/{document_id}/items")
def save_inventory_check_items(
    document_id: int,
    body: SaveItemsBody,
    db: Session = Depends(get_db),
):
    svc = InventoryCheckService(db)
    return svc.save_items(document_id, body.items)


@router.post("/{document_id}/confirm")
def confirm_inventory_check(document_id: int, db: Session = Depends(get_db)):
    svc = InventoryCheckService(db)
    return svc.confirm(document_id)
```

- [ ] **Step 2: 注册 router**

在 `backend/app/api/router.py` 中：

```python
# import 行追加
from app.api import inventory_checks

# include_router 行追加
api_router.include_router(inventory_checks.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/inventory_checks.py backend/app/api/router.py
git commit -m "feat: 新增盘点 API (CRUD + confirm)"
```

---

### Task 5: 前端 API + 路由 + 导航

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: 在 api.ts 中添加 inventoryCheckApi**

```typescript
// frontend/src/services/api.ts 在 inventoryApi 下方追加
export const inventoryCheckApi = {
  create: (check_date?: string, note?: string) =>
    api.post('/inventory-checks', null, { params: { check_date, note } }).then(r => r.data),
  list: () => api.get('/inventory-checks').then(r => r.data),
  get: (id: number) => api.get(`/inventory-checks/${id}`).then(r => r.data),
  saveItems: (id: number, items: { product_id: number; actual_qty: number | null }[]) =>
    api.put(`/inventory-checks/${id}/items`, { items }).then(r => r.data),
  confirm: (id: number) => api.post(`/inventory-checks/${id}/confirm`).then(r => r.data),
};
```

- [ ] **Step 2: 在 App.tsx 中添加路由**

在 `frontend/src/App.tsx` 中：

```typescript
// import 区域追加
import InventoryChecksPage from './pages/InventoryChecksPage';

// Routes 内追加 (放在 /inventory 路由附近)
<Route path="/inventory-checks" element={<InventoryChecksPage />} />
<Route path="/inventory-checks/:id" element={<InventoryChecksPage />} />
```

- [ ] **Step 3: 在 Layout.tsx 中添加导航**

在 `frontend/src/components/Layout.tsx` 的 navItems 数组中，`/inventory` 之前插入：

```typescript
{ to: '/inventory-checks', label: '盘点' },
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: 前端盘点路由 + API + 导航入口"
```

---

### Task 6: 前端盘点页面

**Files:**
- Create: `frontend/src/pages/InventoryChecksPage.tsx`

- [ ] **Step 1: 创建盘点页面（列表 + 详情合一）**

```tsx
// frontend/src/pages/InventoryChecksPage.tsx
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { inventoryCheckApi, productApi } from '../services/api';
import { Button } from '../components/ui/Button';
import { OrderListTable } from '../components/business/OrderListTable';

const STATUS_LABELS: Record<string, string> = { draft: '草稿', confirmed: '已确认' };

export default function InventoryChecksPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ? Number(id) : null;

  // ——— list state ———
  const [checks, setChecks] = useState<any[]>([]);
  const [listLoading, setListLoading] = useState(false);

  // ——— detail state ———
  const [detail, setDetail] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    if (documentId) {
      loadDetail();
    } else {
      loadList();
    }
  }, [documentId]);

  const loadList = async () => {
    setListLoading(true);
    try {
      const data = await inventoryCheckApi.list();
      setChecks(data);
    } finally {
      setListLoading(false);
    }
  };

  const loadDetail = async () => {
    if (!documentId) return;
    setDetailLoading(true);
    try {
      const data = await inventoryCheckApi.get(documentId);
      setDetail(data);
      setItems(data.items || []);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const result = await inventoryCheckApi.create();
      navigate(`/inventory-checks/${result.id}`);
    } catch (e: any) {
      alert('创建失败：' + (e.response?.data?.detail || e.message));
    }
  };

  const handleSave = async () => {
    if (!documentId) return;
    const payload = items.map(it => ({
      product_id: it.product_id,
      actual_qty: it.actual_qty,
    }));
    try {
      await inventoryCheckApi.saveItems(documentId, payload);
      alert('保存成功');
      loadDetail();
    } catch (e: any) {
      alert('保存失败：' + (e.response?.data?.detail || e.message));
    }
  };

  const handleConfirm = async () => {
    if (!documentId) return;
    if (!confirm('确认后盘点单将锁定，不可再修改。确定要确认吗？')) return;
    try {
      await inventoryCheckApi.confirm(documentId);
      loadDetail();
    } catch (e: any) {
      alert('确认失败：' + (e.response?.data?.detail || e.message));
    }
  };

  // ——— list view ———
  if (!documentId) {
    const columns = [
      { key: 'order_number', title: '单号' },
      { key: 'check_date', title: '盘点日期' },
      {
        key: 'status',
        title: '状态',
        render: (r: any) => (
          <span className={r.status === 'confirmed' ? 'text-green-600 font-medium' : 'text-orange-500 font-medium'}>
            {STATUS_LABELS[r.status] || r.status}
          </span>
        ),
      },
      { key: 'item_count', title: '产品数' },
      { key: 'note', title: '备注' },
      { key: 'confirmed_at', title: '确认时间', render: (r: any) => r.confirmed_at?.slice(0, 19).replace('T', ' ') || '-' },
    ];

    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">盘点单</h2>
          <Button onClick={handleCreate}>新建盘点</Button>
        </div>
        <OrderListTable
          columns={columns}
          data={checks}
          rowKey={(r) => r.id}
          isLoading={listLoading}
          onRowClick={(r) => navigate(`/inventory-checks/${r.id}`)}
        />
      </div>
    );
  }

  // ——— detail view ———
  if (detailLoading) {
    return <div className="text-center py-8 text-gray-400">加载中...</div>;
  }
  if (!detail) {
    return <div className="text-center py-8 text-gray-400">盘点单不存在</div>;
  }

  const isDraft = detail.status === 'draft';

  const detailColumns = [
    { key: 'product_name', title: '产品' },
    { key: 'theoretical_qty', title: '理论库存', render: (r: any) => <span className="font-medium">{r.theoretical_qty}</span> },
    {
      key: 'actual_qty',
      title: '实盘数量',
      render: (_: any, idx: number) =>
        isDraft ? (
          <input
            type="number"
            className="border rounded px-2 py-1 w-24 text-sm"
            value={items[idx]?.actual_qty ?? ''}
            onChange={(e) => {
              const v = e.target.value;
              setItems((prev) => {
                const next = [...prev];
                next[idx] = { ...next[idx], actual_qty: v === '' ? null : Number(v) };
                return next;
              });
            }}
          />
        ) : (
          <span className="font-medium">{items[idx]?.actual_qty ?? '-'}</span>
        ),
    },
    {
      key: 'difference',
      title: '差异',
      render: (r: any) => {
        if (r.difference == null) return <span className="text-gray-400">-</span>;
        if (r.difference > 0) return <span className="text-green-600 font-medium">+{r.difference} 盘盈</span>;
        if (r.difference < 0) return <span className="text-red-600 font-medium">{r.difference} 盘亏</span>;
        return <span className="text-gray-500">0 持平</span>;
      },
    },
  ];

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate('/inventory-checks')} className="text-blue-600 hover:underline text-sm">
          &larr; 返回列表
        </button>
        <h2 className="text-xl font-bold">盘点单 {detail.order_number}</h2>
        <span className={`px-2 py-0.5 rounded text-sm font-medium ${isDraft ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
          {STATUS_LABELS[detail.status] || detail.status}
        </span>
      </div>

      <div className="text-sm text-gray-500 mb-4">
        盘点日期：{detail.check_date}
        {detail.confirmed_at && <> | 确认时间：{detail.confirmed_at?.slice(0, 19).replace('T', ' ')}</>}
        {detail.note && <> | 备注：{detail.note}</>}
      </div>

      <OrderListTable columns={detailColumns} data={items} rowKey={(r) => r.product_id} />

      {isDraft && (
        <div className="flex gap-3 mt-4">
          <Button onClick={handleSave}>保存草稿</Button>
          <Button variant="primary" onClick={handleConfirm}>确认盘点</Button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/InventoryChecksPage.tsx
git commit -m "feat: 盘点列表 + 详情页（录入实盘/确认锁定）"
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 启动后端确认 API 正常**

```bash
cd backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 2: 启动前端确认编译通过**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: 手动验证流程**

1. 访问 `/inventory-checks`，点击"新建盘点"
2. 在详情页填入各产品的实盘数量
3. 点击"保存草稿"，刷新页面确认数据保留
4. 点击"确认盘点"，确认状态变为已确认、输入框变为只读
5. 返回列表确认盘点单出现在列表中

- [ ] **Step 4: Commit (如有修复)**

```bash
git add -A && git commit -m "fix: 盘点功能端到端修复"
```
