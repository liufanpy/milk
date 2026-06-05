# 销售/送货/损耗选品时过滤无库存产品

## 背景

销售、送货单、损耗（定奶扣减）选择产品时，当前显示全部产品，用户可能选到已无库存的产品。需要在这些场景下只显示有库存的产品，并在后端提交时做库存不足校验。

## 方案

方案 A：前端本地过滤 + 后端补校验

- 前端 ProductSelect 组件新增 `onlyInStock` prop，开启时并行请求 products 和 inventory，取交集渲染
- 后端 sale_service、wastage_service、subscription_service 补库存校验，库存不足时拒绝并返回 400

## 前端改动

### ProductSelect.tsx（核心组件）

- 新增 `onlyInStock?: boolean` prop，默认 false
- 为 true 时：`Promise.all([productApi.list(), dashboardApi.getInventory()])`，提取库存中的 product_id 集合，过滤产品列表
- 为 false 时行为不变

### 页面加 prop（4 个页面）

| 页面 | 位置 | onlyInStock |
|------|------|-------------|
| SalesPage | 创建销售产品选择 | 是 |
| DeliveriesPage | 创建送货单产品选择 | 是 |
| DeliveriesPage | 换货-新品项产品选择 | 是 |
| WastagePage | 创建损耗产品选择 | 是 |
| SubscriptionsPage | 扣减弹窗产品选择 | 是 |

> DeliveriesPage 换货的"退回品项"不加（退库不需要库存）

## 后端改动

### 补库存校验（3 个 service）

统一校验逻辑，参照 delivery_service.create_delivery 已有的实现：

```python
inventory = {
    (r.product_id, r.shelf_id): r.stock
    for r in self.stock_repo.get_inventory()
}
for item in data.items:
    stock = inventory.get((item.product_id, item.shelf_id), 0)
    if stock < item.quantity:
        raise ValueError(f"产品库存不足，当前库存 {stock}，需要 {item.quantity}")
```

应用位置：
- sale_service.create_sale()
- wastage_service.create_wastage()
- subscription_service.deduct()

### API 层 catch ValueError

- sales.py create_sale：加 try/except ValueError → 400
- wastage.py create_wastage：加 try/except ValueError → 400
- subscriptions.py deduct：已有 try/except，无需改
- deliveries.py：已有，无需改

## 改动文件清单（7 个文件）

```
frontend/src/components/business/ProductSelect.tsx
frontend/src/pages/SalesPage.tsx
frontend/src/pages/DeliveriesPage.tsx
frontend/src/pages/WastagePage.tsx
frontend/src/pages/SubscriptionsPage.tsx
backend/app/services/sale_service.py
backend/app/services/wastage_service.py
backend/app/services/subscription_service.py
backend/app/api/sales.py
backend/app/api/wastage.py
```
