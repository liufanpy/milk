# 所有产品下拉列表支持搜索

> 日期: 2026-06-07 | 状态: 待实施

## 背景

当前项目中有 7 处产品下拉列表，均使用原生 `<select>` 渲染全部产品为 `<option>` 元素。产品数量增多后，用户只能靠滚动盲找，效率低下。

后端 `/api/products?keyword=` 接口已支持关键字搜索，前端 `productApi.list(keyword)` 也已透传，但 `ProductSelect` 组件未使用该能力。

## 范围

- 新增 `ComboBox` 通用 UI 组件
- `ProductSelect` 改用 `ComboBox` 渲染（6 个页面获益）
- `CustomersPage` 客户价格弹窗中的产品下拉改用 `ProductSelect`（第 7 处获益）
- 所有产品下拉统一获得搜索能力，调用方 0 改动

### 不涉及

- 后端改动（接口已就绪）
- `CustomerSelect` / `SupplierSelect` 等非产品下拉
- 其他页面的通用 `Select` 组件

## 设计

### ComboBox 组件

**位置：** `frontend/src/components/ui/ComboBox.tsx`

**Props：**

```ts
interface ComboBoxProps {
  value: string | number;
  onChange: (value: string | number) => void;
  options: { value: string | number; label: string }[];
  placeholder?: string;    // 默认 "请选择"
  emptyMessage?: string;   // 默认 "无匹配结果"
}
```

受控组件模式，`value` 由父组件控制。

**内部状态：**

| 状态 | 类型 | 说明 |
|------|------|------|
| `isOpen` | boolean | 下拉展开/关闭 |
| `searchText` | string | 输入框中的搜索文字 |
| `highlightedIndex` | number | ↑↓ 键盘导航的高亮索引 |

**过滤逻辑：**

```
searchText 为空 → 显示全部 options
searchText 有值 → options.filter(o =>
    o.label.toLowerCase().includes(searchText.toLowerCase()))
```

**交互行为：**

| 操作 | 行为 |
|------|------|
| 聚焦输入框 | 展开全部选项 |
| 输入文字 | 本地过滤（label 任意位置匹配，忽略大小写） |
| 点击选项 | 选中并填入输入框，关闭列表，触发 onChange |
| 点击组件外部 | 关闭列表，恢复已选值文案 |
| Escape | 关闭列表，恢复已选值文案 |
| ↑↓ 方向键 | 高亮导航（到底部继续按下跳到顶，到顶部按上跳到底） |
| Enter | 选中当前高亮项 |
| 点击 × 清除按钮 | 清空选中值 → `onChange('')`，展开列表 |

**边界情况：**

| 场景 | 行为 |
|------|------|
| 搜索无匹配 | 显示 `emptyMessage` |
| options 为空数组 | 显示 `emptyMessage` |
| 已选中值在搜索中被过滤掉 | 仍在输入框中显示其 label（不清除） |
| value 没有对应的 option | 输入框显示空（不崩溃） |

**组件形态：**

输入框 + 下拉箭头 + 清除按钮（有值时）组合，点击或聚焦时展开下拉列表。点击选项后替换输入框文字。样式与现有 `Select` 组件风格一致（border-gray-300, rounded, text-sm）。

### ProductSelect 改动

**位置：** `frontend/src/components/business/ProductSelect.tsx`

- Props 接口不变：`value`、`onChange`、`onlyInStock?`
- 数据加载逻辑不变：`useEffect` 中根据 `onlyInStock` 拉取产品列表
- 渲染改为 `<ComboBox>`，`options` 从产品列表转换：`{ value: p.id, label: `${p.name} (${p.brand})` }`
- 选中回调适配：`onChange(v) → onChange(Number(v))`

### CustomersPage 改动

**位置：** `frontend/src/pages/CustomersPage.tsx`

客户特定价格弹窗中，产品选择器从通用 `Select` 改为 `ProductSelect`：

```
// 之前
<Select
  label="产品"
  options={productOptions}
  value={priceForm.product_id}
  onChange={(e) => setPriceForm({ ...priceForm, product_id: e.target.value })}
/>

// 之后
<ProductSelect
  value={priceForm.product_id}
  onChange={(v) => setPriceForm({ ...priceForm, product_id: String(v) })}
/>
```

删除不再需要的 `productOptions` 变量。

## 受影响文件

| 文件 | 改动类型 |
|------|----------|
| `frontend/src/components/ui/ComboBox.tsx` | 新增 |
| `frontend/src/components/business/ProductSelect.tsx` | 修改 |
| `frontend/src/pages/CustomersPage.tsx` | 修改 |

以下 6 个页面使用 `ProductSelect`，0 改动：
SalesPage、PurchasesPage、DeliveriesPage、ReturnsPage、WastagePage、SubscriptionDetailPage

## 技术约束

- 不引入任何第三方 UI 依赖
- 样式与现有组件风格一致
- 纯本地过滤，无额外网络请求
