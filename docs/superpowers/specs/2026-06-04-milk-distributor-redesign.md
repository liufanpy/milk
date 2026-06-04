# 奶记重建设计文档

## 概述

**定位：** 快消品代理商的数据驱动经营工具  
**第一阶段（MVP）：** 完整记录日常经营（进出货 + 收付款），库存和应收自动准确  
**后续：** 决策建议 → 异常发现 → 预警驱动  
**平台：** 响应式 Web（移动端优先），单机部署，架构预留多租户  

## 技术栈

| 层 | 选型 |
|---|------|
| 后端框架 | Python FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite（SQLAlchemy 抽象，未来可切 PostgreSQL） |
| 前端 | React 19 + TypeScript + TailwindCSS |
| 状态管理 | React Query（服务端状态）+ Zustand（UI 状态） |
| 构建 | Vite |
| 测试 | pytest + Vitest |
| 数据库迁移 | Alembic |
| AI | 暂不加，基础做扎实再扩展 |

## 后端架构

经典四层：`API → Service → Repository → Model`

- **API 层：** 参数校验（Pydantic）+ 调用 Service + 返回 Response，不写业务逻辑
- **Service 层：** 全部业务逻辑 + 事务管理 + 跨 Repository 编排，每个业务操作一个事务保证货流+钱流一致性
- **Repository 层：** 纯数据访问（CRUD + 查询过滤 + 聚合），不写业务判断
- **Model 层：** SQLAlchemy ORM 定义

## 前端架构

- **App.tsx ≤ 50 行：** 路由壳，不持有业务状态
- **每个页面 ≤ 300 行：** 超出拆子组件
- **React Query：** 管理所有服务端数据（列表、详情），自动缓存和同步
- **Zustand：** 仅管理纯 UI 状态（侧栏折叠、弹窗开关），不放业务数据
- **组件分层：** pages（页面） → components/ui（基础 UI） → components/business（业务组件）

## 数据模型

核心设计：**货流管库存，钱流管应收，都是算出来的不存死数。**

### 10 张表

#### 基础资料

| 表 | 关键字段 | 说明 |
|----|---------|------|
| Product | name, brand, category, unit, barcode, default_retail_price, default_wholesale_price, shelf_life_days | 两个默认价仅是录入建议，实际价以成交为准 |
| Customer | name, phone, address, price_tier(wholesale/retail/subscription), default_payment(immediate/credit) | 标签属性非硬分类，不存 balance 字段 |
| Supplier | name, contact, phone | 简单记录 |
| Shelf | name, customer_id(nullable) | 仓库货架/客户店内货架 |

#### 核心流水

| 表 | 关键字段 | 说明 |
|----|---------|------|
| **StockMovement** | product_id, shelf_id, direction(in/out), reason(purchase/sale/return/wastage/transfer/adjust), quantity, unit_cost, delivery_id(nullable), subscription_order_id(nullable) | 库存 = SUM(quantity × direction) 按 shelf 分组 |
| **Transaction** | customer_id(nullable), category(sale/payment/subscription/refund/purchase), amount(正数), delivery_id(nullable) | AR = SUM(sale - payment - subscription - refund) 按 customer 分组 |
| **Delivery** | customer_id, delivery_date, status(pending/delivered), subscription_order_id(nullable) | status 跟踪配送状态；财务状态由未付金额实时判定 |

#### 业务单据

| 表 | 关键字段 | 说明 |
|----|---------|------|
| SubscriptionOrder | customer_id, total_amount, total_bottles, paid_bottles, free_bottles, remaining_bottles, status | 预收款 + 待配送瓶数，每次配送/自取扣减 |
| ProductCustomerPrice | product_id, customer_id, price | 可选，为议价客户配置 |

#### 辅助

| 表 | 关键字段 | 说明 |
|----|---------|------|
| OperationLog | action, entity_type, entity_id, changes(JSON), created_at | 所有修改可追溯 |

### Transaction category 对 AR 的影响

| category | 业务 | 对 AR |
|----------|------|-------|
| sale | 销售产生应收 | +amount |
| payment | 客户还款 | −amount |
| subscription | 订奶预收款 | −amount |
| refund | 退款 | −amount |
| purchase | 付供应商款 | 无关（无 customer_id） |

## API 设计

### 基础资料

- `GET/POST /api/products`, `GET/PUT/DELETE /api/products/:id`
- `GET/POST /api/customers`, `GET/PUT/DELETE /api/customers/:id`
- `GET/POST /api/suppliers`, `GET/PUT/DELETE /api/suppliers/:id`
- `GET/POST /api/shelves`, `GET/PUT/DELETE /api/shelves/:id`
- `GET/POST /api/customers/:id/prices`, `DELETE /api/customers/:id/prices/:price_id`

### 业务操作

| 操作 | 接口 | 说明 |
|------|------|------|
| 进货 | POST /api/purchases | StockMovement in + Transaction purchase |
| 直接销售 | POST /api/sales | StockMovement out + Transaction sale，无 Delivery |
| 送货销售 | POST /api/deliveries | Delivery + StockMovement out + Transaction sale |
| 换货 | POST /api/deliveries/:id/exchange | 原送货单下退旧换新 |
| 退货 | POST /api/returns | StockMovement in + Transaction refund |
| 损耗 | POST /api/wastage | StockMovement out，纯货流 |
| 结算 | POST /api/deliveries/:id/settle | Transaction payment，支持部分结算 |
| 订奶 | POST /api/subscription-orders + POST /api/subscription-orders/:id/deduct | 开单 + 配送扣减 |

### 列表/详情

业务操作对应的列表和详情 GET 接口遵循标准模式：
- `GET /api/deliveries` — 送货单列表（支持按客户/日期/状态筛选）
- `GET /api/deliveries/:id` — 送货单详情（含货流+钱流明细、已付/未付金额）
- `GET /api/sales` — 直接销售列表
- `GET /api/purchases` — 进货列表
- `GET /api/returns` — 退货列表
- `GET /api/subscription-orders` — 订奶单列表

### 查询

- `GET /api/inventory` — 库存汇总（按产品+货架）
- `GET /api/receivables` — 应收汇总（按客户，含未结送货单明细）
- `GET /api/dashboard` — 今日销售/收款/库存预警/应收排行
- `GET /api/operation-logs` — 操作日志

### Service 层保证

每个 POST 接口对应一个 Service 方法，在同一个数据库事务内创建所有相关记录，货流和钱流要么一起成功要么一起回滚。

## MVP 范围

**一句话：** 代理商打开系统，能完整记录每天所有进出货和收付款，库存和应收自动对得上。

**必做 15 项：** 产品管理、客户管理、供应商管理、货架管理、进货、直接销售、送货销售、换货、退货、损耗、结算、订奶、库存查看、应收查看、操作日志。

**后续版本：** 经营看板、决策建议、异常发现、临期预警、AI 录入、CSV 导入、盘点、多用户。

## 项目结构

### 后端

```
backend/app/
├── main.py, config.py, database.py
├── api/          # 路由层
├── services/     # 业务逻辑层
├── repositories/ # 数据访问层
├── models/       # SQLAlchemy ORM
└── schemas/      # Pydantic
```

### 前端

```
frontend/src/
├── App.tsx       # 路由壳 ≤50 行
├── pages/        # 页面组件 ≤300 行/个
├── components/   # ui/ + business/
├── hooks/        # React Query 封装
├── services/     # API 调用
├── store/        # Zustand
└── types/
```

## 价格策略

三层建议 + 实际为准：
1. ProductCustomerPrice（客户专属价）
2. price_tier 对应的默认价（批发/零售/订奶）
3. Product 默认售价
4. **最终以 SaleItem.unit_price 实际录入为准**

## 订奶模型

SubscriptionOrder = 预收款 + 承诺瓶数。每次配送或客户自取从 remaining_bottles 扣减，扣完自动完成。钱在开单时一次性入账（Transaction subscription）。
