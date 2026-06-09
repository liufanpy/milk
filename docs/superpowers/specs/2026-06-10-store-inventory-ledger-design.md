# 店铺库存与资金流水设计

## 目标

引入店铺（Store）维度，实现：
- 总仓与店铺库存分离追踪
- 送货单同时记总仓出库和店铺入库
- 盘点单：录入实盘数，自动算销量，生成利润流水（成本 + 收入）
- 库存流水和资金流水按店铺筛选

## 业务规则

### 送货 = 应收 + 库存转移（买断制）

- 送货单创建即产生应收（现有逻辑不变）
- 送货到关联了 Store 的客户：除总仓出库外，多记一条店铺入库

### 售价优先级

- 客户协议价 > 产品 `default_wholesale_price`

### 成本与利润计算

- 成本不在 Transaction 表中冗余记录
- 利润 = 销售收入 - 出库成本
  - 收入：`SUM(Transaction.amount WHERE category IN retail/subscription/store_sales)`
  - 成本：`SUM(StockMovement.quantity × Product.default_purchase_price WHERE direction='out')`
- 零售和订奶现有的 `cogs` Transaction 一并移除

---

## 数据模型

### 新增表

**stores**
```sql
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    address VARCHAR(200) DEFAULT '',
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**inventory_checks** — 盘点单头
```sql
CREATE TABLE inventory_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number VARCHAR(20) UNIQUE,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    check_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed',
    note VARCHAR(500) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**inventory_check_items** — 盘点明细
```sql
CREATE TABLE inventory_check_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id INTEGER NOT NULL REFERENCES inventory_checks(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    actual_quantity INTEGER NOT NULL
);
```

### 改造表

**stock_movements** — 取消具体单据外键，改为多态引用 + 店铺维度

```sql
-- 删
ALTER TABLE stock_movements DROP COLUMN delivery_id;
ALTER TABLE stock_movements DROP COLUMN subscription_order_id;
ALTER TABLE stock_movements DROP COLUMN purchase_order_id;
ALTER TABLE stock_movements DROP COLUMN retail_order_id;
ALTER TABLE stock_movements DROP COLUMN return_order_id;
ALTER TABLE stock_movements DROP COLUMN wastage_order_id;

-- 加
ALTER TABLE stock_movements ADD COLUMN source_type VARCHAR(20);
ALTER TABLE stock_movements ADD COLUMN source_id INTEGER;
ALTER TABLE stock_movements ADD COLUMN store_id INTEGER REFERENCES stores(id);
ALTER TABLE stock_movements ADD COLUMN customer_id INTEGER REFERENCES customers(id);
```

**transactions** — 同理改造

```sql
-- 删
ALTER TABLE transactions DROP COLUMN delivery_id;
ALTER TABLE transactions DROP COLUMN purchase_order_id;
ALTER TABLE transactions DROP COLUMN subscription_order_id;
ALTER TABLE transactions DROP COLUMN retail_order_id;
ALTER TABLE transactions DROP COLUMN return_order_id;

-- 加
ALTER TABLE transactions ADD COLUMN source_type VARCHAR(20);
ALTER TABLE transactions ADD COLUMN source_id INTEGER;
ALTER TABLE transactions ADD COLUMN store_id INTEGER REFERENCES stores(id);
```

### source_type 枚举

| source_type | 对应表 |
|-------------|--------|
| purchase | purchase_orders |
| retail | retail_orders |
| return | return_orders |
| wastage | wastage_orders |
| delivery | deliveries |
| subscription | subscription_orders |
| inventory_check | inventory_checks |

---

## 业务流程

### 送货单创建

```
1. 校验总仓库存
2. 创建 Delivery
3. StockMovement: out, reason='distribution', source_type='delivery', store_id=NULL
4. Transaction: category='distribution', amount=总金额, source_type='delivery', customer_id=客户
5. 若客户关联了 Store：
     StockMovement: in, reason='store_receive', source_type='delivery', store_id=该店
```

### 盘点确认

对每个产品逐行计算：

```
期初库存 = 上次盘点该店该产品的 actual_quantity
期间进货 = 两次盘点之间 store_receive 入库量求和（按送货单 delivery_date 过滤，不是 created_at）
期末库存 = 本次录入的 actual_quantity
销量     = 期初 + 期间进货 - 期末
```

| 情况 | 库存变动 | 资金流水 |
|------|---------|---------|
| 销量 > 0 | StockMovement: out, reason='store_sales' | store_sales: +销量×售价 |
| 销量 < 0 | StockMovement: in, reason='store_gain' | 无 |

### 盘点撤销

```
1. 检查是否存在后续盘点（同一店铺、check_date > 当前盘点日期）
   若存在 → 禁止撤销："已被后续盘点引用，请先撤销 IC-xxx"
2. 删 StockMovement（source_type='inventory_check', source_id=该盘点单）
3. 删 Transaction（source_type='inventory_check', source_id=该盘点单）
4. 盘点单 status → cancelled
```

---

## API 设计

### 店铺

```
GET    /api/stores              列表
POST   /api/stores              新建
GET    /api/stores/{id}         详情
PUT    /api/stores/{id}         编辑
```

### 盘点

```
POST   /api/inventory-checks           创建（确认盘点）
GET    /api/inventory-checks           列表（支持 store_id, date_from, date_to）
GET    /api/inventory-checks/{id}      详情（含明细 + 销量/金额计算结果）
POST   /api/inventory-checks/{id}/cancel  撤销
```

### 流水（改造）

```
GET /api/stock-ledger        加 store_id 筛选
GET /api/transaction-ledger  加 store_id 筛选
```

---

## 前端页面

- **店铺管理页**：表格 + 新建/编辑弹窗，关联客户
- **盘点页**：选店铺 → 选日期 → 产品列表（含上次实盘数、期间进货参考）→ 填实盘数 → 确认
- **库存流水页**：加店铺筛选下拉
- **资金流水页**：加店铺筛选下拉
- **送货单创建**：选客户后自动关联店铺（无感）
- **App.tsx**：注册 `/stores` 和 `/inventory-checks` 路由
- **Layout.tsx**：侧边栏加"店铺管理"和"盘点管理"入口

---

## 迁移说明

### DDL 迁移
一个 migration 文件包含所有 DDL 变更。

### 数据迁移
- stock_movements：根据现有各外键列填充 source_type + source_id
- transactions：同上
- 旧外键列数据填充完毕后才能 drop
- store_id 和 customer_id 在数据迁移期间暂为 NULL，后续业务写入时填充

### 向后兼容
- 旧数据 source_type/source_id 正确填充，查询逻辑统一走新字段
- store_id / customer_id 可空，旧数据为 NULL，新数据正常写入
- 现有 API 返回格式不变
