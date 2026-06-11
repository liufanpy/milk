# 销售额、成本、利润与应收账款计算方案

## 背景

当前 dashboard 的三个核心指标存在以下问题：

- 销售额统计将铺货调拨当作销售，且漏了巡店推算的店铺销售额
- 出货量统计了全部出库类型（含调拨、损耗、冲销），与销售额口径不一致
- 应收账款将订奶预付款当作待收款，与预收款业务模型矛盾
- 缺少成本和毛利数据

## 设计目标

- 销售额和出货量只反映终端实际销售
- 应收账款按铺货按单结算模型
- dashboard 补齐成本、毛利、退款额

## 业务模型

```
铺货 (distribution) → 移库，不产生销售
             ↓
店铺实际卖出 → 盘点 → store_sales → 这才是销售
                         ↓
店铺按铺货单结算 ← 应收账款基于 distribution 维度
```

## Dashboard 指标

| 指标 | 数据源 | 统计逻辑 |
|------|--------|---------|
| 今日销售额 | transactions | `category IN (retail, subscription, store_sales)` SUM(amount) |
| 今日收款额 | transactions | `category = payment` SUM(amount) |
| 今日退款额 | transactions | `category = refund` SUM(amount) |
| 今日成本 | stock_movements | `direction=out AND source_type IN (retail, subscription, store_sales)` → 每行 quantity × 对应 product.default_purchase_price → SUM |
| 今日出货量 | stock_movements | 同成本条件，SUM(quantity) |
| 今日毛利 | 计算列 | 销售额 − 成本 |

## 应收账款

| 位置 | 公式 |
|------|------|
| get_ar_by_customer（单客户） | `distribution + retail − payment − refund` |
| get_receivables（客户列表） | 同上 |
| transaction_ledger 余额列 | 同上 |

`subscription`（订奶预付款）从应收账款中移除，因为客户是预付而非欠款。

## 改动清单

### 后端

| 文件 | 改动 |
|------|------|
| `dashboard.py` | `today_sales` 改为 `retail, subscription, store_sales`；删除死代码 `sale, delivery, delivery_cancel` |
| `dashboard.py` | `today_out` 加 `source_type IN (retail, subscription, store_sales)` 过滤 |
| `dashboard.py` | 新增 `today_cost` 计算（JOIN products 取进价） |
| `dashboard.py` | 新增 `today_refund` 查询 |
| `dashboard.py` | 新增 `today_gross_profit` 计算 |
| `transaction_repo.py` | `get_ar_by_customer` 和 `get_receivables` 去掉 `subscription` |
| `transaction_ledger.py` | 余额累加和显示都去掉 `subscription` |

### 前端

| 文件 | 改动 |
|------|------|
| Dashboard 页面 | 展示新增的退款、成本、毛利字段 |

### 不动

- 铺货交易（distribution）正常生成，按单结算逻辑不变
- 巡店交易（store_sales）正常生成
- 退货、损耗、赠送的交易记录不变

## 注意事项

- 退货退款不计入销售额，单独展示在退款额列
- 成本通过现有 `stock_movements` JOIN `products` 反推，不需要新表或新字段
- 历史数据无需迁移，新口径对旧数据同样适用
