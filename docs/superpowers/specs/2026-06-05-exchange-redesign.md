# 换货重设计

## 背景

当前换货逻辑存在两个问题：

1. **金额计算有 bug**：场景三（不同价值互换）中全量冲掉旧应收后只按 `new_total` 重算，漏算了客户留下未退的旧货价值。
2. **设计过度通用**：三种换货场景（同产品、同价值不同品、不同价值）混在一个流程里，但实际上前两种占绝大多数且金额不变，场景三极少且应走退货+重开。

## 设计方案

### 换货只处理金额不变的场景

换货接口统一校验：`return_total != new_total` 时直接拒绝，提示走退货结算后重新开单。

### 三种场景处理

| | 判定条件 | stock_movement | transaction | delivery.total_amount |
|---|---|---|---|---|
| 场景一：同产品互换 | 同产品同数量同价 | in+out (reason=exchange) | 不动 | 不动 |
| 场景二：同价值换不同品 | 金额相等 | in+out (reason=exchange) | 不动 | 不动 |
| 场景三：不同价值互换 | 不处理 | — | — | — |

### 后端改动

**`POST /api/deliveries/{id}/exchange`**

1. 计算 `return_total` 和 `new_total`
2. 金额不一致 → 400 拒绝
3. 退回入库：stock_movement（direction=in, reason=exchange）
4. 新发出库：stock_movement（direction=out, reason=exchange），带库存校验
5. 不写 transaction，不改 delivery.total_amount
6. 提交事务

**`GET /api/deliveries/{id}` — `get_delivery_detail`**

- items 过滤：只返回原始送货品项（`reason != "exchange"`），即换货记录不混入品项列表
- 新增 `exchanges` 字段：按 `created_at` 分组 exchange 类 movement，每组 in 为退回、out 为新发。极低概率的同秒两次换货场景可接受合并展示（不影响数据正确性，仅时间线展示略微归并）

```python
exchange_movements = [m for m in movements if m.reason == "exchange"]
groups = {}
for m in exchange_movements:
    groups.setdefault(m.created_at, []).append(m)
exchanges = [
    {
        "created_at": str(ts),
        "return_items": [m for m in ms if m.direction == "in"],
        "new_items":    [m for m in ms if m.direction == "out"],
    }
    for ts, ms in groups.items()
]
```

### 前端改动

**详情弹窗**

- 品项列表保持不变（原始送货单状态）
- 品项列表下方新增"换货记录"区域，时间线样式展示

```
换货记录
┌─────────────────────────────────────────┐
│ 2026-06-05 14:30                        │
│ 退回: 鲜牛奶 ×1 (¥10)                   │
│ 新发: 酸奶 ×2 (¥5×2=¥10)               │
│ 等值换货                                │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 2026-06-04 09:15                        │
│ 退回: 鲜牛奶 ×1 (¥10)                   │
│ 新发: 鲜牛奶 ×1 (¥10)                   │
│ 同产品临期换货                           │
└─────────────────────────────────────────┘
```

**换货弹窗**

- 提交前前端做金额一致性校验，不一致时直接提示，避免无效请求
- 失败提示"换货金额不一致，请走退货结算后重新开单"

### 关于换货挂靠送货单

由于系统无批次管理，无法自动溯源货品来自哪个送货单。换货关联的送货单由操作人主观选择（通常是最近一单），系统不做自动溯源。

### 不改动的部分

- 数据库 schema 不变，复用 stock_movements 表
- 不新增 exchange_logs 表
- 不修改 delivery 模型
