# 库存盘点功能设计

## 概述

为总仓库存新增盘点功能。盘点单纯粹记录理论库存 vs 实盘数量的对比结果，作为独立档案留存。确认盘点时**不产生任何 StockMovement**，差异由人工后续处理。

## 数据模型

### InventoryCheck — 盘点单

沿用现有 `document_id` 作主键关联 `documents` 表的 pattern。

| 字段 | 类型 | 说明 |
|---|---|---|
| document_id | FK → documents.id | 主键 |
| check_date | date | 盘点日期 |
| status | str(20) | `draft` / `confirmed` |
| note | str(500) | 备注 |
| created_at | datetime | 创建时间 |
| confirmed_at | datetime | 确认时间（可为 null） |

### InventoryCheckItem — 盘点明细

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int | 主键 |
| document_id | FK → documents.id | 关联盘点单 |
| product_id | FK → products.id | 产品 |
| theoretical_qty | int | 理论库存（确认时快照） |
| actual_qty | int | 实盘数量（可为 null = 未盘） |
| difference | int | actual_qty - theoretical_qty |

## 单号规则

`IC + 日期8位 + 序号4位`，如 `IC202606120001`。

需在 `DocumentType` 枚举中新增 `inventory_check = "inventory_check"`，在 `PREFIX_MAP` 中新增 `DocumentType.inventory_check: "IC"`。

## 业务流程

### 1. 创建盘点单
- 用户点击"新建盘点"
- 系统创建盘点单（status=draft），自动生成单号
- 页面展示所有产品，每行显示：产品名称、理论库存（从 StockMovement 实时计算）、实盘数量（空输入框）

### 2. 录入实盘数
- 用户逐款产品填入实际盘点数量
- 实时显示差异 = 实盘数 - 理论数
- 正数为盘盈，负数为盘亏
- 支持保存草稿（部分录入）

### 3. 确认盘点
- 所有产品盘点完毕后，点击"确认盘点"
- 系统锁定盘点单（status=draft → confirmed）
- 快照当前 theoretical_qty 和 difference 到明细表
- **不产生 StockMovement**，差异仅记录不调整库存

### 4. 差异处理（人工）
- 用户在盘点详情中查看差异
- 根据实际情况通过现有入口手动处理（Wastage 报损 / Purchase 补录入库等）

## API 设计

### POST /api/inventory-checks — 创建盘点单
```
Response: { id, order_number, check_date, status }
```

### GET /api/inventory-checks — 盘点单列表
```
Query: date_from, date_to, status
Response: [{ id, order_number, check_date, status, item_count, confirmed_at }]
```

### GET /api/inventory-checks/{id} — 盘点单详情
```
Response: {
  id, order_number, check_date, status, note,
  items: [{ product_id, product_name, theoretical_qty, actual_qty, difference }]
}
```

### PUT /api/inventory-checks/{id}/items — 保存明细（草稿状态）
```
Body: { items: [{ product_id, actual_qty }] }
```

### POST /api/inventory-checks/{id}/confirm — 确认盘点

## 前端页面

### 盘点列表页 `/inventory-checks`
- 表格：单号、日期、状态、产品数、备注
- 新建盘点按钮

### 盘点详情页 `/inventory-checks/{id}`
- 标题栏：单号、日期、状态标签
- 产品列表（表格）：
  - 产品名称、理论库存、实盘数量（可编辑输入框）、差异（盘盈/盘亏）
- 底部：保存草稿 / 确认盘点 按钮
- 确认后所有字段只读

## 已知局限

- 盘点仅支持总仓（store_id=null），不涉及门店库存
- 确认后差异由人工处理，系统不自动生成调整流水
- 首个版本不支持 CSV 导入导出（后续按需添加）
