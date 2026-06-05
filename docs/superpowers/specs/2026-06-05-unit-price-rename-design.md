# unit_price 改名 + 进货自动带价

## 背景

`stock_movements.unit_cost` 字段名不准确：进货行存的是进价，出货行存的是售价，字段统一叫 `unit_price`（实际成交单价）更恰当。

另外前端进货表单不会自动填入默认进价，需要手动输入。

## 目标

1. `stock_movements.unit_cost` → `unit_price`（DB + 全部代码）
2. 进货页选产品自动填入 `product.default_purchase_price`

## 范围

不改架构。不改零售订单体系。不改导入逻辑（后续单独处理）。

## 改动清单

### 数据库
```sql
ALTER TABLE stock_movements RENAME COLUMN unit_cost TO unit_price;
```

### 后端 Model
- `stock_movement.py:15` — 列名改名

### 后端 Schema
- `purchase.py:9` — `PurchaseItem.unit_cost` → `unit_price`

### 后端 Service（纯 rename，无逻辑变更）

| 文件 | 处数 |
|---|---|
| `purchase_service.py` | 12 |
| `sale_service.py` | 1 |
| `delivery_service.py` | 3 |
| `return_service.py` | 2 |

### 前端类型
- `types/index.ts` — `PurchaseItem.unit_cost` → `unit_price`、`PurchaseOrderDetailItem.unit_cost` → `unit_price`

### 前端进货页
- `PurchasesPage.tsx` — 字段改名 + 选产品自动填入 `product.default_purchase_price`
- 标签 "进价" → "单价"

## 未解决（后续处理）

进货 CSV 导入时如果没填价格，默认进价应自动从产品表补上。

## 验证

1. 启动后端 + 前端
2. 进货：选产品 → 进价自动填入 default_purchase_price，可修改
3. 送货：选客户+产品 → 售价自动填入（客户专属价 > 等级价 > 零售价）
4. 零售：选产品 → 售价自动填入默认零售价
5. DB Browser 确认列名无误且值正确
