# 销售记录改造

## 目标

以 `retail_orders` 为主体重构销售记录，对齐进货单的表格+详情弹窗+撤销模式。

## 数据模型

`retail_orders` 表新增字段：

| 字段 | 类型 | 默认值 |
|------|------|--------|
| status | String(20) | "confirmed" |
| updated_at | DateTime | now |

状态机：`confirmed` → `cancelled`

## 后端 API

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/sales | 创建销售（不变） |
| GET | /api/sales | 改查 retail_orders，返回单头+品项摘要 |
| GET | /api/sales/{id} | 新增：详情（品项明细） |
| POST | /api/sales/{id}/cancel | 新增：撤销 |

### list_sales 改造

从查 `transactions` 表改为查 `retail_orders`，JOIN customers 拿客户名，JOIN stock_movements 拿品项摘要。

已收款判定：检查是否存在 `category="payment"` 且 `retail_order_id` 匹配的 transaction。

返回结构：
```json
[{id, customer_id, customer_name, item_count, total_amount, paid, status, items_summary, created_at}, …]
```

前端据此显示：已收款(绿) / 未收款(黄) / 已撤销(红)。

### get_sale_detail

查 retail_orders + stock_movements 品项明细 + products 名称。结构跟进货单详情一致。

### cancel_sale

1. 检查 status != "cancelled"
2. 查 stock_movements (retail_order_id) 拿原始出库品项
3. 反向建 stock_movements (direction="in", reason="cancel")
4. 原 transaction 反向冲抵（负金额）
5. status → "cancelled"

## 前端

| 文件 | 改动 |
|------|------|
| types/index.ts | 加 RetailOrder, RetailOrderDetail 接口 |
| services/api.ts | saleApi 加 get(id), cancel(id) |
| pages/SalesPage.tsx | 表格+弹窗+撤销 |

### 销售记录列表

表格列：客户 | 品项摘要 | 金额 | 状态 | 日期 | 操作

品项摘要格式："纯牛奶×3, 酸奶×2"，超过 2 个产品时显示 "纯牛奶×3 等5件"。

状态标签：已收款(绿) / 未收款(黄) / 已撤销(红)

### 详情弹窗

点击行打开，跟进货单详情弹窗结构一致：顶部客户+日期+状态，中间品项表格（产品/数量/售价/小计），底部合计+撤销按钮。

赠送品项在详情中标记。

### 撤销

仅 confirmed 状态的行显示撤销按钮。点击 → confirm → cancel API → 刷新。
