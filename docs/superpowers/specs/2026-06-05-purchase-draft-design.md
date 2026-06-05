# 进货单草稿保存品项

## 背景

进货单草稿状态下 items 不写入 stock_movements，导致详情页看不到品项。要等到确认入库才有数据。

## 目标

草稿创建时就将 items 写入 stock_movements，用 `reason=purchase_draft` 区分，确认时改 reason，撤销时删除。

库存查询排除草稿流水，不影响库存计算。

## 改动

### 后端

1. **创建草稿时写入 stock_movements**
   - `purchase_service.create_purchase`: draft 状态也调用 `_confirm_items`（但传 reason=purchase_draft）
   - 或抽取公共方法，status=draft 时 reason=purchase_draft

2. **确认草稿时改 reason**
   - `purchase_service.confirm_order`: UPDATE stock_movements SET reason='purchase' WHERE purchase_order_id=X AND reason='purchase_draft'
   - 然后创建 transaction

3. **撤销草稿时删除流水**
   - `purchase_service.cancel_order`: draft 状态 DEL stock_movements（不创建反向流水）

4. **库存查询排除草稿**
   - `stock_movement_repo.get_inventory`: 加 `.filter(StockMovement.reason != 'purchase_draft')`

### 前端（不改）

详情页自动就能查到草稿品项了，不需要额外改。

## 未解决

- 草稿编辑功能（后续）
- 草稿操作日志（后续随 LogService 一起加）
