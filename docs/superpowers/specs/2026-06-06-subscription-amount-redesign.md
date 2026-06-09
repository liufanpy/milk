# 库存资金流水统一设计 & 订奶金额模式重构

## 设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | 货钱分离 | StockMovement 管货，Transaction 管钱，各自独立 |
| 2 | 只增不改 | 错误靠反向冲抵，不 UPDATE 流水记录 |
| 3 | 每笔出库必记成本 | 销售、促销、损耗出库都必须有成本 Transaction |
| 4 | 分类 = 来源 | 一个 reason/category 答"从哪来"，性质用字段区分 |
| 5 | 可追溯 | 每条流水挂源单 FK，没有空关联 |
| 6 | 收入与收款分开 | 货出去（收入确认）和钱到账（收款）是两个时间点 |
| 7 | 可扩展 | 新业务类型只加 reason/category，不改表结构 |
| 8 | 可维护 | 所有业务模块同一套流水写入模式 |
| 9 | 可拆分查询 | StockMovement 和 Transaction 各自独立闭环，不 JOIN 也能查 |

## 表结构变更

### 新增 retail_orders 表

```
id, customer_id(nullable), created_at
```

零售每个交易建一条，散客 customer_id 为空。

### StockMovement

```
保留:  id, product_id, direction, reason, quantity, unit_price, created_at
保留:  delivery_id, purchase_order_id, subscription_order_id, retail_order_id (新增)
删除:  shelf_id
```

### Transaction

```
保留:  id, category, amount, note, created_at
保留:  customer_id, supplier_id, delivery_id, purchase_order_id
新增:  subscription_order_id, retail_order_id (nullable FK)
```

### 追溯链路

```
StockMovement / Transaction
  → retail_order_id        → retail_orders → customer_id(可空)
  → subscription_order_id  → subscription_orders → customer_id
  → delivery_id            → deliveries → customer_id
  → purchase_order_id      → purchase_orders → supplier_id
```

### shelves 表

删除。当前只有一个仓库，用 product_id 汇总即可得库存。客户维度库存通过 order → customer_id 链路查询。

### SubscriptionOrder 表

```
保留:  id, customer_id, note, status, created_at
改名:  total_amount       → paid_amount
改名:  remaining_bottles  → remaining_amount
删除:  total_bottles, paid_bottles, free_bottles
```

状态流转：`active` → `completed`(remaining_amount ≤ 0)、`cancelled`

### SubscriptionCreate schema

```python
class SubscriptionCreate(BaseModel):
    customer_id: int
    paid_amount: float
    is_paid: bool = True   # 默认已收款，取消勾选则不记 payment
    note: str = ""
```

### SubscriptionDeduct schema

```python
class SubscriptionDeductItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float | None = None  # 空则自动从客户定价解析
    is_promo: bool = False           # 赠送行 unit_price 强制为 0

class SubscriptionDeduct(BaseModel):
    items: List[SubscriptionDeductItem]
```

unit_price 解析优先级：手动填入 > 客户专属价 > 等级价(price_tier) > 默认零售价。

## StockMovement reason

| reason | direction | 关联 | 含义 |
|--------|:---:|------|------|
| `purchase` | in | purchase_order_id | 进货入库 |
| `return` | in | retail_order_id / subscription_order_id / delivery_id | 退货入库 |
| `wastage` | in | — | 损耗冲抵入库 |
| `exchange` | in | delivery_id | 换货退回入库 |
| `cancel` | out | purchase_order_id | 进货撤销出库 |
| `retail` | out | retail_order_id | 零售出库 |
| `subscription` | out | subscription_order_id | 定奶出库 |
| `distribution` | out | delivery_id | 分销出库 |
| `wastage` | out | — / delivery_id / subscription_order_id | 损耗出库 |
| `exchange` | out | delivery_id | 换货新发出库 |

逆向区分：`return(in)` 按 FK 区分来源，`wastage(in)` 独立。`wastage(out)` 无 FK = 仓库损耗，有 delivery_id/subscription_order_id = 配送中损耗。

不设 `promo` reason。赠送行通过 `unit_price = 0` 区分，reason 仍为对应业务线（`subscription` 或 `retail`）。

## Transaction category

正数 = 流入 / 负数 = 流出

| category | 方向 | 关联 | 含义 |
|----------|:---:|------|------|
| `payment` | + | customer_id, subscription_order_id 或 delivery_id | 收款到账 |
| `retail` | + | customer_id(可空) | 零售收入 |
| `subscription` | + | customer_id, subscription_order_id | 定奶收入（扣减时确认） |
| `distribution` | + | customer_id, delivery_id | 分销收入 |
| `purchase` | - | supplier_id, purchase_order_id | 采购支出 |
| `refund` | - | customer_id, delivery_id | 退货退款 |
| `cogs` | - | customer_id(可空) | 销售成本（进价×出库量） |
| `promo` | - | customer_id(可空) | 促销成本（进价×赠送量） |
| `wastage` | - | — | 损耗成本（进价×损耗量） |

### category 变动对照

| 旧 | 新 | 说明 |
|----|-----|------|
| `sale` | `retail` | 改名 |
| `delivery` | `distribution` | 改名 |
| `subscription`(旧) | 拆分 | 删除，拆为 `payment` + `subscription` |
| `subscription_deduct` | `subscription` | 并入 |
| `subscription_payment` | `payment` | 并入 |
| `delivery_cancel` | 删除 | 走 `distribution` 负数冲抵 |
| `purchase_cancel` | 删除 | 走 `purchase` 负数冲抵 |
| — | `cogs` | 新增 |
| — | `promo` | 新增 |
| — | `wastage` | 新增 |

## 定奶业务逻辑

### 创建订奶单

```
输入: 客户 + 实付金额 + 是否已收款(默认是) + 备注(可选)
输出: 订奶单(status=active, remaining_amount=paid_amount)
动账: is_paid=true → Transaction(+payment, amount=paid_amount)
      is_paid=false → 不记 payment（应收，后续单独收款）
```

### 配送扣减

```
校验:
  1. 订奶单 status = active
  2. SUM(非促销行 quantity × unit_price) ≤ remaining_amount
  3. 库存充足

动账（每行）:
  付费行:
    StockMovement("out", "subscription", unit_price, subscription_order_id)
    Transaction(+subscription, 售价×数量, customer_id, subscription_order_id)
    Transaction(-cogs, 进价×数量, customer_id, subscription_order_id)
  赠送行(is_promo=true):
    StockMovement("out", "subscription", unit_price=0, subscription_order_id)
    Transaction(-promo, 进价×数量, customer_id, subscription_order_id)

更新:
  remaining_amount -= 付费行合计
  remaining_amount ≤ 0 → completed
```

### 零售出库

```
前置: 创建 retail_order(customer_id 可空)
动账:
  StockMovement("out", "retail", unit_price, retail_order_id)
  Transaction(+retail, 售价×数量, customer_id, retail_order_id)
  Transaction(-cogs, 进价×数量, customer_id, retail_order_id)
```

### 促销赠送（零售场景）

```
前置: 创建 retail_order(customer_id 可空)
动账:
  StockMovement("out", "retail", unit_price=0, retail_order_id)
  Transaction(-promo, 进价×数量, customer_id, retail_order_id)
```

### 促销赠送（分销场景）

```
前置: delivery 已存在
动账:
  StockMovement("out", "distribution", unit_price=0, delivery_id)
  Transaction(-promo, 进价×数量, customer_id, delivery_id)
```

### 损耗

```
动账:
  StockMovement("out", "wastage")
  Transaction(-wastage, 进价×数量)
```

## API

### 修改接口

```
POST /api/subscription-orders              — 创建，参数改为新 schema
POST /api/subscription-orders/{id}/deduct  — 扣减，参数改为新 schema，取消 shelf_id
GET  /api/subscription-orders              — 列表，返回字段调整
```

### 新增接口

```
GET /api/subscription-orders/{id}          — 详情 + 扣减记录列表
```

## 前端

### 订奶单列表页

- 展示: paid_amount / remaining_amount / status
- 操作: 创建 / 扣减 / 查看详情

### 新建订奶单

- 客户选择 + 实付金额 + 已收款勾选(默认选中) + 备注(可选)

### 扣减弹窗

- 选产品 + 数量 + 单价(自动带出，可改) + 赠送勾选
- 底部显示: 本次扣减合计 / 剩余余额变化
- 超出余额时阻止提交

### 详情页（新增）

- 订奶单概要 + 扣减记录列表（按配送批次分组）

### 赠送入口

各业务开单行级加"赠送"勾选，选后 `unit_price` 强制 0：

| 入口 | 位置 |
|------|------|
| 定奶扣减弹窗 | 已有 `is_promo` |
| 零售开单 | 加产品行后勾选 |
| 分销送货 | 加产品行后勾选 |

## 利润计算

### 收入

```sql
SELECT SUM(amount) FROM transactions WHERE category IN ('retail', 'subscription', 'distribution')
```

按产品拆分：
```sql
SELECT product_id, SUM(quantity * unit_price) AS revenue
FROM stock_movements
WHERE reason IN ('retail', 'subscription', 'distribution')
  AND unit_price > 0
GROUP BY product_id
```

### 出库成本

```sql
SELECT SUM(amount) FROM transactions WHERE category IN ('cogs', 'promo', 'wastage')
```

`purchase` 是采购现金流（含未售库存），不参与利润计算。

### 毛利

```
毛利 = SUM(retail + subscription + distribution + cogs + promo + wastage)
```

- `retail + subscription + distribution` — 收入确认（货已出）
- `cogs + promo + wastage` — 出库成本（已售/已送/已损耗）
- `payment` — 收款流水，不参与利润
- `purchase` — 采购现金流，不参与利润（未售库存不算成本）
- `refund` — 退款现金流

## 不在此范围

- 退款/退订流程
- 定价锁定/版本
- 多仓库/多货架
- 采购批次成本追踪
- 历史数据迁移
