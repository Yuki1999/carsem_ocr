# Customs Quantity Normalization Design

**Goal:** 让报关填报草稿在生成后自动保证数量字段语义正确，较小或相等的值归入良品数量字段。

## Scope

- 作用于表头字段 `TotalQuantity` / `GoodQuantity`
- 作用于明细字段 `ItemQuantity` / `ItemGoodQuantity`
- 只在两边都能解析为数字时自动调整
- 规则在后端草稿归一化阶段执行，前端展示和最终提交保持一致

## Rule

- 如果 `GoodQuantity > TotalQuantity`，交换两者
- 如果 `ItemGoodQuantity > ItemQuantity`，交换两者
- 如果两者相等，不做变更
- 如果任一值不是数字占位之外的可解析数字，例如 `-1`、空值或杂项文本，则不交换

## Architecture

数量归一化放在 `app/customs_submission.py` 的草稿规范化流程里。这样无论草稿来自规则映射、LLM 直出，还是前端保存回写，都会在合并和生成时应用同一套规则。

这一步发生在现有数值清洗之后，因此像 `287111 EA`、`10.5 USD` 这类值会先变成纯数字文本，再决定是否需要交换数量字段。

## Error Handling

- 不为缺失字段编造新值
- 不对 `-1` 这类占位值做交换
- 不改动其他价格、重量字段

## Testing

- 表头：当 `GoodQuantity` 大于 `TotalQuantity` 时自动交换
- 明细：当 `ItemGoodQuantity` 大于 `ItemQuantity` 时自动交换
- 占位值 `-1` 不触发交换
- 相等值保持不变
