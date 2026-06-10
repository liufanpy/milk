# 待改：source 多态引用 → 全局文档 ID

**日期**: 2026-06-10

**当前状态:** `source_type` + `source_id` 两列实现多态关联

## 问题

- `source_id` 是各订单表自增整数，跨表会重复
- SQLite 不支持跨表外键约束，引用完整性靠应用层兜底
- 删掉 `source_type` 简化查询的前提是 `source_id` 必须全局唯一

## 方案

建 `documents` 基表统一生成全局 ID，所有订单表主键引用它：

```sql
CREATE TABLE documents (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type VARCHAR(20)
);

-- 各订单表 PK 改为引用 documents.id
purchase_orders.id   → REFERENCES documents(id)
retail_orders.id     → REFERENCES documents(id)
deliveries.id        → REFERENCES documents(id)
...

-- StockMovement / Transaction 只剩一列
source_id → REFERENCES documents(id)
```

## 代价

1. 所有订单创建前需先生成 documents 记录
2. 迁移时 stock_movements/transactions 每行 `source_id` 需重新映射到全局 ID
3. 数据越多迁移越重

## 建议时机

趁数据量少尽早做。越晚成本越大。
