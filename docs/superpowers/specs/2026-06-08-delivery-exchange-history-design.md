# 送货单详情 — 展示换货历史记录

## 背景

后端 `get_delivery_detail` 已返回 `exchanges` 字段（含历史换货记录），但前端详情弹窗未渲染。

## 改动范围

仅修改 `frontend/src/pages/DeliveriesPage.tsx`，在详情弹窗的 `OrderDetailModal` 中，品项表格与金额/操作区之间插入换货历史区域。

## 展示规则

- 无换货记录时不显示该区域
- 每条换货记录展示：时间、退回品项列表（灰色/删除线）、换入品项列表
- 按时间倒序排列（最新的在上）

## 数据来源

后端已返回 `exchanges` 数组，结构：

```json
[
  {
    "created_at": "2024-06-08T14:30:00",
    "return_items": [{"product_id": 1, "quantity": 1, "unit_price": 100}],
    "new_items": [{"product_id": 2, "quantity": 1, "unit_price": 100}]
  }
]
```

使用已有的 `productNames` 映射将 `product_id` 转为产品名。

## 不做什么

- 不新增 API
- 不修改 OrderDetailModal 共享组件（通过 children 传入即可）
- 不修改后端
