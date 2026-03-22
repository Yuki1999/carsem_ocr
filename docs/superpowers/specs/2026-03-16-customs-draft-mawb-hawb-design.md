# Customs Draft Mawb Hawb Design

**Goal:** 将报关填报草稿协议从 `MainBLNo/SubBLNo` 调整为 `Mawb/Hawb`，并让报关填报工作区对未识别字段自动填入 `无`。

## Scope

- 后端报关草稿字段定义改为 `Mawb/Hawb`
- 大模型直出报关草稿时使用 `Mawb/Hawb`
- 前端报关填报工作区展示 `Mawb/Hawb`
- 未识别的头字段和明细字段统一自动填入 `无`
- 提交网站前，后端将 `Mawb/Hawb` 转换为站点接口要求的 `MainBLNo/SubBLNo`

## Architecture

现有链路保持不变，仍然是 `OCR -> LLM/规则生成 submission draft -> 前端人工确认 -> 服务端提交网站`。本次仅调整 draft 协议和缺省值策略，不改 API 入口，不改提交流程。

后端继续负责草稿归一化和提交兼容。前端负责展示、编辑和保存归一化后的草稿。这样 `Mawb/Hawb` 只在业务层出现，目标站点接口兼容细节仍留在后端。

## Draft Contract

`header` 字段调整为：

- `Mawb`
- `Hawb`
- `CustomerName`
- `TradeType`
- `OriginCountry`
- `InvoiceNo`
- `Quantity`
- `GrossWeight`
- `NetWeight`
- `TotalSheets`
- `TotalQuantity`
- `GoodQuantity`
- `TotalPrice`

`details[]` 字段保持为：

- `ItemCode`
- `ItemOrigin`
- `ItemQuantity`
- `ItemGoodQuantity`
- `ItemPrice`
- `ItemUnitPrice`

## Default Value Rules

- 对头字段，凡是未识别、缺失、空字符串，统一归一化为 `无`
- 对明细字段，凡是未识别、缺失、空字符串，统一归一化为 `无`
- 如果完全没有明细行，生成 1 行全部为 `无` 的占位明细
- `meta.required_missing` 仍保留，但由于缺省值自动补 `无`，其主要作用会转为结构合法性跟踪而不是空值提示

## LLM Behavior

生成报关草稿时，LLM 被明确要求直接返回：

- `header`
- `details`
- `meta`

并且 `header` 中使用 `Mawb/Hawb` 而不是 `MainBLNo/SubBLNo`。LLM 未能识别的字段允许返回空字符串，后端归一化阶段会补成 `无`。

## Submission Compatibility

提交网站时，服务端在拼装 payload 前进行字段转换：

- `Mawb -> MainBLNo`
- `Hawb -> SubBLNo`

这样不需要改动站点提交流程，也避免前端暴露站点内部字段名。

## Error Handling

- 如果 LLM 返回结构非法，接口继续报错，不静默编造结构
- 如果旧历史记录仍使用 `MainBLNo/SubBLNo`，归一化时兼容迁移到 `Mawb/Hawb`
- 自动补 `无` 仅用于空值和缺失字段，不覆盖已有有效值

## Testing

- 后端测试覆盖：
  - 规则映射输出 `Mawb/Hawb`
  - LLM 直出 `Mawb/Hawb`
  - 缺失字段自动补 `无`
  - 无明细时自动补占位明细
  - 提交 payload 将 `Mawb/Hawb` 转成 `MainBLNo/SubBLNo`
- 前端测试覆盖：
  - 草稿默认值为 `无`
  - `Mawb/Hawb` 字段可编辑
  - 旧草稿 `MainBLNo/SubBLNo` 可归一化到新字段
