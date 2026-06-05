# 销售页与送货单按客户档位分离

## 目标

销售页只负责零售客户（含散客），送货单只负责批发客户，两边职责彻底分离。

## 不改的部分

- 收款方式、定价逻辑保持不变
- 散客（不选客户）在销售页照常可用
- 其他页面的 CustomerSelect 不受影响

## 改动点

### 1. CustomerSelect 组件

新增可选参数 `priceTier?: string`：

- 传入时，调用 `customerApi.list()` 带上 `price_tier` 查询参数
- 不传则不过滤，保持向后兼容

### 2. 后端 GET /api/customers

支持可选查询参数 `price_tier`，传入时过滤结果。

### 3. SalesPage

```tsx
<CustomerSelect value={customerId} onChange={setCustomerId} priceTier="零售" />
```

### 4. DeliveriesPage

```tsx
<CustomerSelect value={customerId} onChange={setCustomerId} priceTier="批发" />
```

送货单列表的客户筛选器同理。

## 涉及文件

| 文件 | 改动 |
|------|------|
| `frontend/src/components/business/CustomerSelect.tsx` | 新增 priceTier prop，传给 API |
| `frontend/src/services/api.ts` | customerApi.list 支持 priceTier 参数 |
| `frontend/src/pages/SalesPage.tsx` | CustomerSelect 传 priceTier="零售" |
| `frontend/src/pages/DeliveriesPage.tsx` | 两处 CustomerSelect 传 priceTier="批发" |
| `backend/app/api/customers.py` | 支持 price_tier 查询参数 |
| `backend/app/services/customer_service.py` | list_customers 支持 price_tier 过滤 |
| `backend/app/repositories/customer_repo.py` | search 支持 price_tier 过滤 |
