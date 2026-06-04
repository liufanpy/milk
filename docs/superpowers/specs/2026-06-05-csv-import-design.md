# CSV 导入功能设计

## 范围

产品和客户两个模块的 CSV 导入，先预览再确认入库。供应商不做。

## 后端 API

| 接口 | 作用 |
|------|------|
| POST /api/products/import | 上传 CSV → 解析校验 → 返回预览 |
| POST /api/products/import/confirm | 入库勾选的行 |
| POST /api/customers/import | 同上 |
| POST /api/customers/import/confirm | 同上 |

## 校验规则

- 名称必填
- 同名产品/客户跳过（去重）
- 数字字段格式校验（价格为非负数）
- CSV 表头支持中英文双名

## 返回格式

import 返回 `{headers, rows: [{index, data, status, msg}], summary: {total, ok, error}}`
confirm 入参 `{rows: [0, 2, 5]}`，返回 `{success, errors}`

## 前端

产品页和客户页各加"导入"按钮 → 选文件 → 预览弹窗（标红错误 + 勾选确认） → 入库
