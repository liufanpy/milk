# 客户运营中心设计（极简版）

## 概述

为铺货客户提供两级运营视图 + sell-through 数据录入。先跑通最小闭环，后续迭代加功能。

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

- 每个客户每个产品每天一条记录
- `unit_price` = 终端售价，`amount` = quantity × unit_price
- 唯一约束防止重复录入
- 成本从 `products.unit_price`（进货价）读取，不单独存储

## 层级一：经营总览页

### 页面路径 `/customer-ops`

```
┌──────────────────────────────────────────┐
│  时间筛选器: 今日 | 近7天 | 近30天         │
├──────────────────────────────────────────┤
│  实销总额    │  总成本      │  毛利+毛利率  │
├──────────────────────────┬───────────────┤
│  客户对比排名表            │  整体趋势图     │
│  (客户/实销/成本/毛利/率)   │  (Sell-through)│
└──────────────────────────┴───────────────┘
```

### 汇总卡片（3个）

实销总额 / 总成本 / 毛利 + 毛利率，毛利卡绿色高亮

### 客户对比排名表

默认按毛利降序。列：客户名、实销金额、成本、毛利、毛利率。点击客户行进入详情页，时间参数跟随。

### 趋势图

近N天整体 sell-through 折线图，Y轴=销量，一条总汇总线。

### 后端接口

`GET /api/customer-ops/overview?days=7`

```json
{
  "summary": {
    "total_amount": 8520, "total_cost": 5370,
    "total_profit": 3150, "total_margin": 0.37
  },
  "customers": [
    {"id": 1, "name": "张三超市",
     "sell_through_amount": 1280, "cost": 780,
     "profit": 500, "margin": 0.391}
  ],
  "trend": [
    {"date": "2026-06-01", "total_qty": 22},
    {"date": "2026-06-02", "total_qty": 28}
  ]
}
```

## 层级二：客户运营详情页

### 页面路径 `/customer-ops/:id?days=7`

```
┌──────────────────────────────────────────┐
│  客户下拉选择器 + 时间筛选器               │
├──────────────────────────────────────────┤
│  实销金额    │  成本       │  毛利+毛利率   │
├──────────────────────────────────────────┤
│        Sell-through 趋势图                │
│        (折线图, 支持按产品筛选)             │
├──────────────────────────────────────────┤
│                  [+ 录入实销] FAB          │
└──────────────────────────────────────────┘
```

### 快照卡片（3个）

实销金额 / 成本 / 毛利 + 毛利率

### 趋势图

展示该客户近N天 sell-through 走势。产品标签筛选（全部/按产品），显示日均销量。

### Sell-through 录入弹窗

点击 FAB 弹出：

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

- 列出该客户当前有库存的所有产品
- 数量默认 0，单价自动带出上次录入价
- 金额 = 数量 × 单价，自动计算
- 保存时仅提交数量 > 0 的行

### 后端接口

`GET /api/customer-ops/{id}/summary?days=7`
```json
{
  "customer_id": 1, "customer_name": "张三超市",
  "summary": {"amount": 1280, "cost": 780, "profit": 500, "margin": 0.391},
  "trend": [
    {"date": "2026-06-01", "by_product": {"1": 8, "2": 4}}
  ]
}
```

`POST /api/sell-through` — 批量录入
`GET /api/sell-through?customer_id=&date=&days=` — 查询

## 前端组件

```
components/
├── TimeRangeFilter.tsx          # 时间筛选器（复用）
├── business/
│   ├── SummaryCards.tsx         # 实销/成本/毛利三卡片（复用）
│   ├── CustomerCompareTable.tsx # 客户对比排名表
│   ├── SellThroughTrend.tsx     # 趋势折线图（复用）
│   └── SellThroughEntry.tsx     # 实销录入弹窗
pages/
├── CustomerOpsOverviewPage.tsx  # 经营总览
└── CustomerOpsDetailPage.tsx    # 客户详情
```

## 技术栈

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：React + TypeScript + Vite + Zustand + React Query + Tailwind CSS
- 图表：SVG 手工绘制

## 范围外（本期不做）

- 产品动销矩阵、预警、回款健康度、最近动态、铺货vs实销对比
- 产品利润排名表、库存成本
- 沟通备注
- 自动上报接口
