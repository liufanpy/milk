# 换货重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 简化换货逻辑——只处理金额不变的换货（同产品/等值换货），金额不一致直接拒绝，stock_movement 统一用 reason=exchange，不改 transaction 和 delivery.total_amount

**Architecture:** 后端 `exchange` 方法删掉所有 transaction 操作，只做 amount 校验 + stock_movement 入库/出库。`get_delivery_detail` 中 items 过滤掉 exchange 类 movement，新增 exchanges 字段按时间分组展示换货记录。前端详情弹窗新增换货时间线，换货弹窗增加金额一致性前置校验。

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React/TypeScript (frontend)

---

### Task 1: 后端 — 重写 exchange 方法

**Files:**
- Modify: `backend/app/services/delivery_service.py:81-142`

- [ ] **Step 1: 替换 exchange 方法实现**

将 `exchange` 方法从当前的"全量冲抵 + 重算应收"改为"金额校验 + 纯库存操作"：

```python
def exchange(self, delivery_id: int, data: ExchangeCreate):
    delivery = self.delivery_repo.get_by_id(delivery_id)
    if not delivery:
        raise ValueError("送货单不存在")

    return_total = sum(item.quantity * item.unit_price for item in data.return_items)
    new_total = sum(item.quantity * item.unit_price for item in data.new_items)

    if return_total != new_total:
        raise ValueError("换货金额不一致，请走退货结算后重新开单")

    # 退回入库
    for item in data.return_items:
        self.stock_repo.bulk_create([{
            "product_id": item.product_id,
            "shelf_id": item.shelf_id,
            "direction": "in",
            "reason": "exchange",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "delivery_id": delivery_id,
        }])

    # 新发出库（带库存校验）
    self.stock_repo.validate_stock(data.new_items)
    for item in data.new_items:
        self.stock_repo.bulk_create([{
            "product_id": item.product_id,
            "shelf_id": item.shelf_id,
            "direction": "out",
            "reason": "exchange",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "delivery_id": delivery_id,
        }])

    self.db.commit()
    return {"return_total": return_total, "new_total": new_total}
```

- [ ] **Step 2: 运行现有测试确认无回归**

```bash
cd backend && python -m pytest tests/test_delivery.py -v
```

Expected: 两个现有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/delivery_service.py
git commit -m "refactor: 换货改为纯库存操作，金额不一致直接拒绝"
```

---

### Task 2: 后端 — get_delivery_detail 增加换货时间线

**Files:**
- Modify: `backend/app/services/delivery_service.py:55-79`

- [ ] **Step 1: 修改 get_delivery_detail 的 items 过滤和新增 exchanges 字段**

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

    # 换货记录：按 created_at 分组
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
        "customer_id": delivery.customer_id,
        "delivery_date": str(delivery.delivery_date),
        "status": delivery.status,
        "note": delivery.note,
        "items": [
            {"product_id": m.product_id, "quantity": m.quantity, "reason": m.reason, "direction": m.direction}
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
```

- [ ] **Step 2: 运行现有测试**

```bash
cd backend && python -m pytest tests/test_delivery.py -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/delivery_service.py
git commit -m "feat: get_delivery_detail 新增 exchanges 时间线字段，items 过滤换货记录"
```

---

### Task 3: 后端 — 换货功能测试

**Files:**
- Create: `backend/tests/test_exchange.py`

- [ ] **Step 1: 编写测试文件**

```python
"""测试换货 — 金额一致换货 + 金额不一致拒绝"""
import pytest


class TestExchange:
    def test_exchange_same_product(self, client, seed_data):
        """同产品换货：库存增减相抵，应收不变"""
        s = seed_data["suppliers"][0]
        sh1 = seed_data["shelves"][0]
        p = seed_data["products"][0]
        c = seed_data["customers"][0]

        # 备货
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 20, "unit_price": 35, "shelf_id": sh1.id},
            ],
            "status": "confirmed",
        })

        # 创建送货单
        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p.id, "quantity": 3, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        delivery_id = resp.json()["id"]
        detail_before = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail_before["total_amount"] == 114  # 3 × 38

        # 同产品换货：退 1 换 1，同价
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
            "new_items": [
                {"product_id": p.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        assert resp.status_code == 200
        assert resp.json()["return_total"] == 38
        assert resp.json()["new_total"] == 38

        # 验证详情
        detail = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail["total_amount"] == 114  # 应收不变
        assert len(detail["items"]) == 1  # 只有原始送货品项
        assert len(detail["exchanges"]) == 1  # 一条换货记录
        assert detail["exchanges"][0]["return_items"][0]["quantity"] == 1
        assert detail["exchanges"][0]["new_items"][0]["quantity"] == 1

    def test_exchange_same_value_different_product(self, client, seed_data):
        """等值换不同产品：库存变化，应收不变"""
        s = seed_data["suppliers"][0]
        sh1 = seed_data["shelves"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        # 备货两种产品
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35, "shelf_id": sh1.id},
                {"product_id": p2.id, "quantity": 20, "unit_price": 42, "shelf_id": sh1.id},
            ],
            "status": "confirmed",
        })

        # 创建送货单
        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        delivery_id = resp.json()["id"]

        # p1 退 2(¥76) 换 p2 退 2(单价改 38，¥76，等值)
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 2, "unit_price": 38, "shelf_id": sh1.id},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 2, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        assert resp.status_code == 200

        detail = client.get(f"/api/deliveries/{delivery_id}").json()
        assert detail["total_amount"] == 76  # 应收不变
        assert len(detail["exchanges"]) == 1
        assert detail["exchanges"][0]["return_items"][0]["product_id"] == p1.id
        assert detail["exchanges"][0]["new_items"][0]["product_id"] == p2.id

    def test_exchange_amount_mismatch_rejected(self, client, seed_data):
        """金额不一致拒绝换货"""
        s = seed_data["suppliers"][0]
        sh1 = seed_data["shelves"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35, "shelf_id": sh1.id},
                {"product_id": p2.id, "quantity": 20, "unit_price": 42, "shelf_id": sh1.id},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        delivery_id = resp.json()["id"]

        # 退 1(¥38) 换 3(¥114)，金额不一致
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 3, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        assert resp.status_code == 400
        assert "金额不一致" in resp.json()["detail"]

    def test_exchange_insufficient_stock_fails(self, client, seed_data):
        """换货新发品项库存不足时拒绝"""
        s = seed_data["suppliers"][0]
        sh1 = seed_data["shelves"][0]
        p1 = seed_data["products"][0]
        p2 = seed_data["products"][1]
        c = seed_data["customers"][0]

        # 只给 p1 备货，不给 p2
        client.post("/api/purchases", json={
            "supplier_id": s.id,
            "purchase_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 20, "unit_price": 35, "shelf_id": sh1.id},
            ],
            "status": "confirmed",
        })

        resp = client.post("/api/deliveries", json={
            "customer_id": c.id,
            "delivery_date": "2026-06-05",
            "items": [
                {"product_id": p1.id, "quantity": 5, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        delivery_id = resp.json()["id"]

        # 退 p1 换 p2，但 p2 无库存
        resp = client.post(f"/api/deliveries/{delivery_id}/exchange", json={
            "return_items": [
                {"product_id": p1.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
            "new_items": [
                {"product_id": p2.id, "quantity": 1, "unit_price": 38, "shelf_id": sh1.id},
            ],
        })
        assert resp.status_code == 400
        assert "库存不足" in resp.json()["detail"]
```

- [ ] **Step 2: 运行测试**

```bash
cd backend && python -m pytest tests/test_exchange.py -v
```

Expected: 4 tests PASS

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
cd backend && python -m pytest -v
```

Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_exchange.py
git commit -m "test: 换货功能测试 — 等值换货 + 金额不一致拒绝 + 库存不足"
```

---

### Task 4: 前端 — 换货弹窗增加金额一致性前置校验

**Files:**
- Modify: `frontend/src/pages/DeliveriesPage.tsx:128-145`

- [ ] **Step 1: 在 handleExchange 中增加金额校验**

将 `handleExchange` 函数替换为：

```tsx
const handleExchange = async () => {
  if (!selectedDelivery) return;

  const returnTotal = returnItems.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);
  const newTotal = newItems.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);

  if (returnTotal !== newTotal) {
    alert('换货金额不一致，请走退货结算后重新开单');
    return;
  }

  if (returnItems.some(i => !i.product_id || !i.shelf_id || !i.quantity) ||
      newItems.some(i => !i.product_id || !i.shelf_id || !i.quantity)) {
    alert('请填写完整信息');
    return;
  }

  try {
    await exchangeMutation.mutateAsync({
      id: selectedDelivery.id,
      data: { return_items: returnItems, new_items: newItems },
    });
    alert('换货成功');
    setExchangeOpen(false);
    setReturnItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
    setNewItems([{ product_id: 0, quantity: 1, unit_price: 0, shelf_id: 0 }]);
    const detail = await deliveryApi.get(selectedDelivery.id);
    setSelectedDelivery(detail);
    refetch();
  } catch (err: any) {
    alert(err?.response?.data?.detail || '换货失败');
  }
};
```

- [ ] **Step 2: 换货弹窗中实时显示金额对比**

在换货弹窗的"确认换货"按钮上方加两行金额显示：

```tsx
{/* 在 </Button> 确认换货 之前插入 */}
<div className="text-sm text-gray-500 pt-2 border-t">
  <div>退回合计: ¥{returnItems.reduce((s, i) => s + i.quantity * i.unit_price, 0).toFixed(2)}</div>
  <div>新发合计: ¥{newItems.reduce((s, i) => s + i.quantity * i.unit_price, 0).toFixed(2)}</div>
  {returnItems.reduce((s, i) => s + i.quantity * i.unit_price, 0) !== newItems.reduce((s, i) => s + i.quantity * i.unit_price, 0) && (
    <div className="text-red-500 font-medium">金额不一致，无法换货</div>
  )}
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DeliveriesPage.tsx
git commit -m "feat: 换货弹窗增加金额一致性校验和实时对比显示"
```

---

### Task 5: 前端 — 详情弹窗增加换货记录时间线

**Files:**
- Modify: `frontend/src/pages/DeliveriesPage.tsx:232-258` (Detail Modal 区域)

- [ ] **Step 1: 在品项列表和收款记录之间插入换货时间线**

在详情弹窗中，品项列表 `</div>` 之后、收款记录 `<div>` 之前，插入换货记录区域：

```tsx
{selectedDelivery.exchanges && selectedDelivery.exchanges.length > 0 && (
  <div>
    <h4 className="text-sm font-medium mb-2">换货记录</h4>
    <div className="space-y-2">
      {selectedDelivery.exchanges.map((ex: any, i: number) => (
        <div key={i} className="bg-gray-50 rounded p-3 text-sm">
          <div className="text-gray-400 text-xs mb-1">
            {new Date(ex.created_at).toLocaleString()}
          </div>
          <div className="text-gray-600">
            退回: {ex.return_items.map((it: any) =>
              `${productNames[it.product_id] || '产品#' + it.product_id} ×${it.quantity} (¥${it.unit_price})`
            ).join(', ')}
          </div>
          <div className="text-gray-600">
            新发: {ex.new_items.map((it: any) =>
              `${productNames[it.product_id] || '产品#' + it.product_id} ×${it.quantity} (¥${it.unit_price})`
            ).join(', ')}
          </div>
          <div className="text-gray-400 text-xs mt-1">
            {ex.return_items.length === ex.new_items.length &&
             ex.return_items.every((it: any, j: number) =>
               it.product_id === ex.new_items[j].product_id &&
               it.quantity === ex.new_items[j].quantity
             ) ? '同产品换货' : '等值换货'}
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DeliveriesPage.tsx
git commit -m "feat: 详情弹窗新增换货记录时间线"
```
