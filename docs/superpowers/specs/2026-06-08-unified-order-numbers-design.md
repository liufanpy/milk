# 统一单号设计

## 目标

为所有 6 种单据统一单号格式，方便业务查询和手工对账。同时移除退货单无用的来源关联字段。

## 单号格式

```
XXYYYYMMDDNNNN

PO202606080001  进货
RO202606080001  零售
RT202606080001  退货
WO202606080001  损耗
DO202606080001  送货
SO202606080001  订奶
```

- **XX**：2 位单据类型前缀
- **YYYYMMDD**：8 位日期
- **NNNN**：4 位当日流水号，从 0001 起

14 位定长，无分隔符。

## 生成规则

每种单据独立序列。基准日期取 `date.today()`。

```
每个 Service 的 _next_order_number():
  1. 取当天日期 → prefix = "XX20260608"
  2. 查库: SELECT MAX(order_number) WHERE order_number LIKE "XX20260608%"
  3. 取最后 4 位解析为 int，+1
  4. 没有当天记录 → 0001
  5. 返回 "XX202606080001"
```

进货已有 `PO-YYYYMMDD-NNN`，需要改格式（去掉分隔符、4 位序号）。其余 5 种从零建。

## 数据库变更

### return_orders（删 + 加）

```sql
-- 删
ALTER TABLE return_orders DROP COLUMN source_type;
ALTER TABLE return_orders DROP COLUMN source_order_id;
-- 加
ALTER TABLE return_orders ADD COLUMN order_number VARCHAR(20);
CREATE UNIQUE INDEX idx_return_orders_number ON return_orders(order_number);
```

### retail_orders / wastage_orders / deliveries / subscription_orders（加）

```sql
ALTER TABLE xxx ADD COLUMN order_number VARCHAR(20);
CREATE UNIQUE INDEX idx_xxx_number ON xxx(order_number);
```

### purchase_orders（改格式）

已有 `order_number VARCHAR(20) UNIQUE INDEX`，不需改表结构。旧数据格式 `PO-20260608-001` 不再变，新数据从改造时刻起用新格式。

## 后端变更

### 模型层

| 模型 | 变更 |
|------|------|
| `ReturnOrder` | 删 `source_type`, `source_order_id`，加 `order_number` |
| `RetailOrder` | 加 `order_number` |
| `WastageOrder` | 加 `order_number` |
| `Delivery` | 加 `order_number` |
| `SubscriptionOrder` | 加 `order_number` |
| `PurchaseOrder` | 不改（已有） |

### Service 层

每个 Service 加 `_next_order_number(self) -> str`，在 `create_*` 中调用并写入。

**ReturnService：**
- Schema `ReturnCreate` 删 `source_type`, `source_order_id`
- `create_return` 删来源字段写入
- `list_returns` / `get_return_detail` 删来源字段返回，加 `order_number`

### API 层

| 文件 | 变更 |
|------|------|
| `returns.py` | 无结构变更（schema 驱动） |

### 迁移

一个 migration 文件包含所有 6 张表的变更。

## 前端变更

### 退货表单

- 删来源类型下拉 + 来源单号输入框
- `ReturnItem` interface 不变

### 列表列

6 个页面列表第一列从 `#id` 改为 `单号`，显示 `order_number`：

```
#id  →  单号
#1   →  PO202606080001
```

## 兼容性

- 旧数据（已有 `order_number` 的行）：进货单保留旧格式不做回填
- 旧数据（无 `order_number` 的行）：列默认为 NULL，列表渲染时 `NULL` 回退显示 `#id`
- 新数据：全部按新格式生成单号

## 测试

每个 Service 的 `_next_order_number` 方法需要覆盖：
- 当天无记录 → 返回 `XX202606080001`
- 当天有记录 → 递增
- 跨天 → 新日期从头 0001 起
- 4 位满 → 自动进位（9999 → 10000 超出 4 位时为正确性让步，不抛错）

已有测试不变（`order_number` 是后端生成，测试不依赖具体格式）。
