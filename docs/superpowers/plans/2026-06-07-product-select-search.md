# 产品下拉列表搜索功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为全部 7 处产品下拉列表添加本地搜索过滤能力

**Architecture:** 新增通用 `ComboBox` UI 组件（聚焦展开 + 本地过滤 + 键盘导航），`ProductSelect` 改用 `ComboBox` 渲染，`CustomersPage` 改用 `ProductSelect`。无需后端改动，无需新依赖。

**Tech Stack:** React 19, TypeScript, Tailwind CSS 4, Vite

---

### Task 1: 创建 ComboBox UI 组件

**Files:**
- Create: `frontend/src/components/ui/ComboBox.tsx`

- [ ] **Step 1: 创建 ComboBox.tsx**

```tsx
import { useState, useRef, useEffect } from 'react';

interface ComboBoxOption {
  value: string | number;
  label: string;
}

interface ComboBoxProps {
  value: string | number;
  onChange: (value: string | number) => void;
  options: ComboBoxOption[];
  placeholder?: string;
  emptyMessage?: string;
}

export function ComboBox({
  value,
  onChange,
  options,
  placeholder = '请选择',
  emptyMessage = '无匹配结果',
}: ComboBoxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedOption = options.find((o) => o.value === value);

  const filtered = searchText
    ? options.filter((o) =>
        o.label.toLowerCase().includes(searchText.toLowerCase()),
      )
    : options;

  // 搜索文字变化时重置高亮
  useEffect(() => {
    setHighlightedIndex(0);
  }, [searchText]);

  // 点击外部关闭
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selectOption = (opt: ComboBoxOption) => {
    onChange(opt.value);
    setSearchText('');
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === 'ArrowDown') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + 1) % filtered.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(
          (prev) => (prev - 1 + filtered.length) % filtered.length,
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (filtered[highlightedIndex]) {
          selectOption(filtered[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setSearchText('');
        break;
    }
  };

  const handleClear = () => {
    onChange('');
    setSearchText('');
    setIsOpen(true);
    inputRef.current?.focus();
  };

  const hasValue = value !== '' && value !== undefined && value !== 0;

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center border border-gray-300 rounded px-2 py-1 text-sm bg-white focus-within:ring-2 focus-within:ring-blue-500">
        <input
          ref={inputRef}
          type="text"
          className="flex-1 outline-none bg-transparent"
          placeholder={selectedOption ? selectedOption.label : placeholder}
          value={searchText}
          onChange={(e) => {
            setSearchText(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
        />
        {hasValue && (
          <button
            type="button"
            className="text-gray-400 hover:text-gray-600 ml-1"
            onClick={handleClear}
            tabIndex={-1}
          >
            &times;
          </button>
        )}
        <span className="text-gray-400 ml-1 pointer-events-none text-[10px]">&#9660;</span>
      </div>
      {isOpen && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded shadow-lg max-h-48 overflow-y-auto">
          {filtered.length === 0 ? (
            <li className="px-2 py-1 text-sm text-gray-400">{emptyMessage}</li>
          ) : (
            filtered.map((opt, idx) => (
              <li
                key={opt.value}
                className={`px-2 py-1 text-sm cursor-pointer hover:bg-blue-50 ${
                  idx === highlightedIndex ? 'bg-blue-100' : ''
                }`}
                onClick={() => selectOption(opt)}
                onMouseEnter={() => setHighlightedIndex(idx)}
              >
                {opt.label}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: TypeScript 编译检查**

```bash
cd frontend && npx tsc --noEmit src/components/ui/ComboBox.tsx 2>&1
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ui/ComboBox.tsx
git commit -m "feat: 新增 ComboBox 通用组合框组件

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: ProductSelect 改用 ComboBox

**Files:**
- Modify: `frontend/src/components/business/ProductSelect.tsx`

- [ ] **Step 1: 修改 ProductSelect.tsx**

将渲染部分从原生 `<select>` 替换为 `<ComboBox>`，数据加载逻辑保持不变。

```tsx
import { useEffect, useState } from 'react';
import { productApi, dashboardApi } from '../../services/api';
import { ComboBox } from '../ui/ComboBox';

interface ProductSelectProps {
  value: number | string;
  onChange: (productId: number) => void;
  onlyInStock?: boolean;
}
export function ProductSelect({ value, onChange, onlyInStock }: ProductSelectProps) {
  const [products, setProducts] = useState<any[]>([]);
  useEffect(() => {
    let cancelled = false;
    if (onlyInStock) {
      Promise.all([productApi.list(), dashboardApi.getInventory()])
        .then(([all, inv]) => {
          if (cancelled) return;
          const inStockIds = new Set((inv as any[]).map((r: any) => r.product_id));
          setProducts(all.filter((p: any) => inStockIds.has(p.id)));
        })
        .catch(() => {});
    } else {
      productApi.list().then((data) => { if (!cancelled) setProducts(data); }).catch(() => {});
    }
    return () => { cancelled = true; };
  }, [onlyInStock]);
  return (
    <ComboBox
      value={value}
      onChange={(v) => onChange(Number(v))}
      options={products.map((p: any) => ({ value: p.id, label: `${p.name} (${p.brand})` }))}
      placeholder="选产品"
    />
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/business/ProductSelect.tsx
git commit -m "feat: ProductSelect 改用 ComboBox 支持搜索过滤

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: CustomersPage 改用 ProductSelect

**Files:**
- Modify: `frontend/src/pages/CustomersPage.tsx`

- [ ] **Step 1: 修改 CustomersPage.tsx**

三处改动：
1. 导入中加入 `ProductSelect`
2. 删除 `productOptions` 变量
3. 弹窗中 `<Select>` 替换为 `<ProductSelect>`

**导入部分（第 10 行，`import { Select }` 改为 `import { ProductSelect }`）：**

```tsx
import { ProductSelect } from '../components/business/ProductSelect';
```

> 注意：`Select` 仍在其他位置使用（priceTier/payment 下拉），不能删除其导入。只需新增 `ProductSelect` 导入。

以下为具体改动：

```diff
- import { Select } from '../components/ui/Select';
  import { Modal } from '../components/ui/Modal';
  import CsvImportModal from '../components/business/CsvImportModal';
+ import { ProductSelect } from '../components/business/ProductSelect';
```

**删除 productOptions 变量（第 106 行）：**

```diff
- const productOptions = products.map((p: any) => ({ value: p.id, label: `${p.name} (${p.brand})` }));
```

**替换产品下拉（第 160-165 行）：**

```diff
- <Select
-   label="产品"
-   options={productOptions}
-   value={priceForm.product_id}
-   onChange={(e) => setPriceForm({ ...priceForm, product_id: e.target.value })}
- />
+ <ProductSelect
+   value={priceForm.product_id}
+   onChange={(v) => setPriceForm({ ...priceForm, product_id: String(v) })}
+ />
```

`priceForm.product_id` 类型为 `string`，`ProductSelect.onChange` 传入 `number`，需要 `String(v)` 转回。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/CustomersPage.tsx
git commit -m "feat: CustomersPage 产品下拉改用 ProductSelect 获得搜索能力

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: 构建验证

- [ ] **Step 1: TypeScript 编译**

```bash
cd /Users/liufan/program/milk/frontend && npx tsc -b 2>&1
```
预期：无错误输出。

- [ ] **Step 2: Vite build**

```bash
cd /Users/liufan/program/milk/frontend && npx vite build 2>&1
```
预期：`✓ built in X.XXs`

- [ ] **Step 3: 提交**（如有 lint fix 等微调）

---

## 验证清单

实施完成后验证以下场景：

1. SalesPage — 点产品输入框，全部在库产品展开，输入关键字过滤，选中
2. PurchasesPage — 全部产品展开（无 onlyInStock），搜索过滤，选中
3. DeliveriesPage — 三处产品下拉（新建行 + 退货 + 换货）均正常搜索
4. ReturnsPage — 产品下拉搜索正常
5. WastagePage — 在库产品搜索正常
6. SubscriptionDetailPage — 扣减产品搜索正常
7. CustomersPage 定价弹窗 — 产品搜索正常
8. 键盘操作 — ↑↓ 导航、Enter 选中、Escape 关闭
9. 清除按钮 — 有值时显示 ×，点击清空
10. 点击外部 — 下拉关闭
