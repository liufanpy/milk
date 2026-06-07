# 单据页面统一设计

## 目标

统一进货、销售、送货、退货、损耗、订奶 6 个单据页面的列表与详情交互模式，消除重复代码，同时为退货/损耗补充缺失的单头层。

## 设计原则

- 公共部分抽取为组件，差异部分各页自己定义
- 新建和详情都用 Modal，页面主体只留列表
- 退货和损耗各建独立的 Order 表，跟上已有 4 种单据对齐

## 一、后端数据模型

### 新增表

**return_orders**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| customer_id | FK→customers, NOT NULL | 谁退的 |
| source_type | VARCHAR(20), 可空 | 来源类型：delivery / retail / subscription |
| source_order_id | INTEGER, 可空 | 来源单号 |
| note | VARCHAR(500) | |
| status | VARCHAR(20), DEFAULT 'confirmed' | confirmed / cancelled |
| created_at / updated_at | DATETIME | |

`total_refund` 不冗余存储，由关联 transactions 聚合计算。

**wastage_orders**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| note | VARCHAR(500) | |
| status | VARCHAR(20), DEFAULT 'confirmed' | confirmed / cancelled |
| created_at / updated_at | DATETIME | |

损耗品项行的原因（expired/damaged/self_consumed/giveaway/promotion）放在 stock_movements.reason 字段。

### 已有表加字段

**stock_movements：**
- `return_order_id` INTEGER FK，可空
- `wastage_order_id` INTEGER FK，可空

**transactions：**
- `return_order_id` INTEGER FK，可空

不加 `wastage_order_id`——损耗不涉及资金流动。

### 状态流转

```
return_orders:  confirmed → cancelled
wastage_orders: confirmed → cancelled
```

## 二、后端 API

### 退货

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/returns | 创建退货单（写 return_orders + stock_movements + transactions） |
| GET | /api/returns | 列表（查 return_orders，JOIN customers 拿客户名，聚合计费详情） |
| GET | /api/returns/{id} | 详情（单头 + 品项明细 + 退款流水） |
| POST | /api/returns/{id}/cancel | 撤销（反向冲抵库存 + 反向退款 transaction） |

### 损耗

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/wastage | 创建损耗单（写 wastage_orders + stock_movements） |
| GET | /api/wastage | 列表（查 wastage_orders + 品项摘要） |
| GET | /api/wastage/{id} | 详情（单头 + 品项明细） |
| POST | /api/wastage/{id}/cancel | 撤销（反向冲抵库存） |

创建接口的请求体保持不变（已有字段足够），只是 service 层内部改为先建单头再建品项。

## 三、前端组件架构

### 抽取的公共组件

| 组件 | 职责 |
|------|------|
| `OrderListTable` | 表格 + 加载态 + 空态 + 行点击 → 详情回调 |
| `OrderDetailModal` | 详情弹窗壳：头信息(grid) + 品项明细表 + 底部操作区 |
| `OrderFormModal` | 新建弹窗壳：表单内容区 + 提交/取消按钮 |
| `ItemRowEditor` | 品项行编辑：ProductSelect + 数量 + 单价 + 删除钮，通过 children slot 塞附加字段 |
| `ItemDetailTable` | 品项明细四列表格（产品 / 数量 / 单价 / 小计） |
| `StatusBadge` | 统一状态标签，接受 `statusConfig: Record<string, {label, variant}>` |

### 每页自己定义

- columns（列表列定义）
- createForm（新建弹窗内容：头字段 + 品项行 + 备注）
- detailActions（详情底部按钮：确认/撤销/结算/换货/扣减）
- onProductChange（选产品后自动填价策略）
- onSubmit（创建提交逻辑）
- api 对象
- statusConfig 映射表

### 页面结构示意

```tsx
function PurchasesPage() {
  return (
    <div>
      <PageHeader title="进货管理">
        <Button onClick={openCreate}>+ 新建</Button>
        <Button onClick={exportCsv}>导出</Button>
      </PageHeader>
      <OrderListTable
        columns={purchaseColumns}
        data={orders}
        isLoading={loading}
        onRowClick={openDetail}
        statusConfig={purchaseStatus}
      />
      <OrderFormModal open={createOpen} title="新建进货单">
        <PurchaseFormItems />
      </OrderFormModal>
      <OrderDetailModal order={detail} items={detail.items} statusConfig={purchaseStatus}>
        <PurchaseDetailActions />
      </OrderDetailModal>
    </div>
  );
}
```

### 组件树

```
订单页面 (PurchasesPage / SalesPage / ...)
├── PageHeader              ← 不抽（太简单）
├── OrderListTable          ← 公共
│   ├── <table> / 空态 / 加载态
│   └── StatusBadge         ← 公共
├── OrderFormModal          ← 公共壳
│   └── [页面自己的 Form 内容]
│       ├── ItemRowEditor   ← 公共
│       │   └── [slot: 赠送勾选 / 报废勾选 / 原因下拉]
│       └── 提交/草稿按钮   ← 页面自己
└── OrderDetailModal        ← 公共壳
    ├── 头信息 grid         ← 页面自己填
    ├── ItemDetailTable     ← 公共
    └── [页面自己的操作按钮]
```

## 四、逐页改造清单

| 页面 | 后端 | 前端 |
|------|------|------|
| 退货 | 建 return_orders + API 改造 | 列表表格化 + 详情弹窗 + 撤销 |
| 损耗 | 建 wastage_orders + API 改造 | 列表表格化 + 详情弹窗 + 撤销 |
| 销售 | 已有零售单头（上期改造完） | 列表表格化 + 详情弹窗 + 撤销 |
| 进货 | 已有 | 新建改弹窗 + 接入公共组件 |
| 送货 | 已有 | 新建改弹窗 + 接入公共组件 |
| 订奶 | 已有 | 列表接入公共组件，详情保持独立路由 |

## 五、不纳入范围

- 主数据页（客户/产品/供应商）——已规范，不动
- 订奶详情页保持独立路由 `/subscriptions/:id`——内容复杂度远超弹窗承载
- 促销搭赠（is_promo）留在销售/送货品项行，不纳入损耗
- CSV 导入导出各页保持现有实现，不做统一封装

## 六、错误处理

- 撤销时校验 status ≠ cancelled，已撤销的单据拒绝再次撤销
- 创建时必填项校验（前端 + 后端双重）
- 反向冲抵时金额计算精确匹配原始记录
