# 客户运营中心设计

## 概述

为铺货客户提供一站式运营视图，两级页面 + 统一时间维度，支持 sell-through 数据录入与分析。

## 目标

- **经营总览页**：跨客户对比、全局趋势、异常预警，快速发现问题和机会
- **客户详情页**：单个客户深度分析 + 录入实销数据
- **时间维度**：全局筛选器（今日/近7天/近30天/本月），两级页面共享

## 数据模型

### sell_through 表（新增）

```sql
CREATE TABLE sell_through (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    unit_price REAL NOT NULL DEFAULT 0,
    amount REAL NOT NULL DEFAULT 0,
    date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, product_id, date)
);
```

### 说明

- 每个客户每个产品每天一条记录
- `unit_price` 记录实际终端售价（与批发价区分）
- 唯一约束防止重复录入同一客户同一天同一产品
- 后续可扩展为自动上报接口，数据结构不变

## 层级一：经营总览页

### 页面路径

`/customer-ops`

### 布局

```
┌──────────────────────────────────────────────────┐
│  时间筛选器: 今日 | 近7天 | 近30天 | 本月           │
├──────────────────────────────────────────────────┤
│  5个全局汇总卡片（实销/库存/应收/滞销/缺货）         │
├─────────────────────────┬────────────────────────┤
│  客户对比排名表            │  整体 Sell-through 趋势  │
│  (客户/实销/库存/周转/应收) │  (折线图 + TOP 客户叠加) │
├─────────────────────────┼────────────────────────┤
│  产品动销矩阵             │  预警聚合               │
│  (产品×客户 销量热力图)    │  (跨客户问题汇总)        │
└─────────────────────────┴────────────────────────┘
```

### 客户对比排名表

按实销量降序排列所有客户。每行显示：客户名、实销量、铺货库存金额、周转天数、应收余额、健康状态(🟢🟡🔴)。点击客户行进入该客户的详情页，时间筛选器跟随携带。

### 产品动销矩阵

行=产品，列=客户，值为近N天 sell-through 数量。颜色编码：绿(>日均)、黄(一般)、红(<日均或0)。横向看出产品在所有客户的表现，纵向看出客户整体动销情况。

### 预警聚合

汇总所有客户的严重问题，按优先级排列：
- 🔴 紧急：应收超期30天+、库存积压严重
- 🟠 关注：缺货风险、滞销单品

### 后端接口

`GET /api/customer-ops/overview?days=7`

返回：
```json
{
  "summary": {
    "total_sell_through_amount": 8520,
    "total_sell_through_qty": 156,
    "total_inventory_amount": 186500,
    "total_inventory_qty": 1850,
    "total_ar": 42300,
    "overdue_ar": 8600,
    "slow_moving_count": 12,
    "stockout_risk_count": 8
  },
  "customers": [
    {
      "id": 1, "name": "张三超市",
      "sell_through_amount": 1280, "sell_through_qty": 35,
      "inventory_amount": 32500, "turnover_days": 6,
      "ar_balance": 8640, "overdue_ar": 2100,
      "health": "warning"
    }
  ],
  "trend": [
    {"date": "2026-05-30", "total_qty": 20, "top_customers": [{"id":1,"qty":8},{"id":2,"qty":6}]}
  ],
  "product_matrix": [
    {"product_id": 1, "product_name": "纯牛奶", "by_customer": {"1": 24, "2": 18, "3": 8}}
  ],
  "alerts": [
    {"level": "red", "customer_id": 3, "customer_name": "王五小卖部",
     "type": "overdue_ar", "message": "超期30天+：¥8,500，回款及时率仅35%"}
  ]
}
```

## 层级二：客户运营详情页

### 页面路径

`/customer-ops/:id?days=7`

### 布局

```
┌──────────────────────────────────────────────────┐
│  客户选择器（下拉切换） + 基本信息 + 时间筛选器      │
├──────────────────────────────────────────────────┤
│  5个快照卡片（实销/库存/应收/滞销品数/缺货风险数）    │
├─────────────────────────┬────────────────────────┤
│  Sell-through 趋势图      │  铺货 vs 实销对比        │
│  (折线图, 支持按产品筛选)   │  (进度条列表, 含可卖天数) │
├─────────────────────────┼────────────────────────┤
│  预警清单                 │  回款健康度              │
│  (缺货/滞销, 红橙分级)     │  (应收构成 + 超期明细     │
│                          │   + 回款及时率)          │
├─────────────────────────┴────────────────────────┤
│  最近动态时间线（送货/退货/回款）                     │
├──────────────────────────────────────────────────┤
│                               [+ 录入今日实销] FAB  │
└──────────────────────────────────────────────────┘
```

### 5个快照卡片

| 卡片 | 内容 | 数据来源 |
|------|------|----------|
| 今日实销 | 金额 + 件数 + 品数 | sell_through WHERE date=today |
| 当前铺货库存 | 金额 + 件数 + 品数 | stock_movement 汇总 |
| 应收余额 | 总应收 + 超期金额 | transactions 汇总 |
| 滞销品数 | 连续7天未动销的产品数 | sell_through 分析 |
| 缺货风险数 | 库存不足3天销量的产品数 | 库存÷日均销量 |

### Sell-through 趋势图

折线图，X轴日期，Y轴销量。支持按产品标签筛选（全部/按产品）。显示日均销量和环比趋势箭头。

### 铺货 vs 实销对比

每个已铺货产品一行进度条。左端=0，右端=铺货总量，填充部分=已卖数量。百分比高=卖得快，低=动销差。每行标注可卖天数（剩余库存÷日均销量）和状态标签。

### 预警清单

- 🔴 缺货风险：库存不足3天销量
- 🟠 滞销：连续7天 sell-through 为 0

### 回款健康度

- 应收总额构成（正常 vs 超期30天+）
- 超期车次明细
- 回款及时率（近10次回款，按时回款占比）

### 最近动态时间线

最近5条该客户的业务记录：送货、退货、回款，按时间倒序。

### Sell-through 录入弹窗

点击 FAB 按钮弹出：

```
┌─────────────────────────────────┐
│  录入实销 — 张三超市             │
│  日期: 2026-06-05                │
├─────────────────────────────────┤
│  产品       数量   单价    金额   │
│  ─────────────────────────────  │
│  纯牛奶     [  ]  [  ]   auto   │
│  酸奶       [  ]  [  ]   auto   │
│  面包       [  ]  [  ]   auto   │
│  ...                            │
│            [取消]  [保存]        │
└─────────────────────────────────┘
```

- 默认列出该客户当前有库存的所有产品
- 数量默认为 0，单价自动带出上次录入的价格
- 金额 = 数量 × 单价，自动计算
- 保存时只提交数量 > 0 的行

### 后端接口

`GET /api/customer-ops/{id}/summary?days=7`
```json
{
  "customer_id": 1, "customer_name": "张三超市",
  "last_delivery_date": "2026-06-02",
  "cooperation_days": 186,
  "today_sell_through": {"amount": 1280, "qty": 23, "products": 8},
  "inventory": {"amount": 32500, "qty": 312, "products": 12},
  "ar_balance": 8640, "overdue_ar": 2100,
  "slow_moving_count": 3,
  "stockout_risk_count": 2,
  "trend": [
    {"date": "2026-05-30", "by_product": {"1": 8, "2": 4}}
  ],
  "distribution_vs_sales": [
    {"product_id": 1, "product_name": "纯牛奶",
     "total_distributed": 60, "total_sold": 48, "remaining": 12,
     "daily_avg_sales": 5, "turnover_days": 2.5, "status": "stockout_risk"}
  ],
  "alerts": [...],
  "ar_detail": {"normal": 6540, "overdue": 2100, "overdue_details": [...], "payment_rate": 0.65},
  "recent_activities": [...]
}
```

`POST /api/sell-through` — 批量录入 sell-through
`GET /api/sell-through?customer_id=&date=&days=` — 查询 sell-through 数据

## 前端组件拆分

```
components/
├── TimeRangeFilter.tsx          # 时间筛选器（复用）
├── business/
│   ├── CustomerCompareTable.tsx # 客户对比排名表
│   ├── ProductMatrix.tsx        # 产品动销矩阵
│   ├── SellThroughTrend.tsx     # 趋势折线图
│   ├── DistVsSalesBars.tsx      # 铺货vs实销进度条
│   ├── AlertList.tsx            # 预警清单
│   ├── PaymentHealth.tsx        # 回款健康度
│   ├── RecentActivities.tsx     # 最近动态
│   └── SellThroughEntry.tsx     # 实销录入弹窗
pages/
├── CustomerOpsOverviewPage.tsx  # 经营总览
└── CustomerOpsDetailPage.tsx    # 客户详情
```

## 预警计算逻辑

| 预警类型 | 条件 | 级别 |
|----------|------|------|
| 缺货风险 | 剩余库存 ÷ 近7天日均销量 < 3 | 🔴 |
| 即将缺货 | 剩余库存 ÷ 近7天日均销量 < 5 | 🟠 |
| 滞销 | 连续7天 sell-through = 0 且剩余库存 > 0 | 🟠 |
| 严重滞销 | 连续30天 sell-through = 0 且剩余库存 > 0 | 🔴 |
| 应收超期 | 送货超过30天未结清 | 🔴 |

## 技术栈

遵循项目现有技术栈：
- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：React + TypeScript + Vite + Zustand + React Query + Tailwind CSS
- 图表：使用 SVG 手工绘制（不引入额外图表库，保持依赖最小）

## 范围外

- 沟通备注/拍照记录（明确不做）
- 自动上报接口（留扩展空间，本期不做）
- 同类客户对比/季节性提示/产品渗透率（后续迭代）
- 同比环比分析（后续迭代）
