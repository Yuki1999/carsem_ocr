# Header Quantity Semantics Design

## Goal

Align the three customs draft header quantity fields with the intended business meanings:

- `TotalQuantity` = 总数量
- `GoodQuantity` = 良品总数量
- `TotalSheets` = 总片数

## Scope

- strengthen the customs LLM prompt in `app/main.py`
- correct rules fallback aliases in `app/customs_submission.py`
- correct detected-field overrides after LLM draft generation
- add focused backend tests

## Required Behavior

- `TotalQuantity` should come from `Qty`, `QTY`, `Summary Quantity`, or equivalent total-quantity fields
- `GoodQuantity` should come from `Gross Qty`, `Summary Gross Qty`, or equivalent good-quantity fields
- `TotalSheets` should come from `Die Qty`, `WaferQty`, `Wafer Qty`, or `Summary WaferQty`
- if detected OCR fields exist for these trusted aliases, they should override incorrect LLM header values

## Testing

- prompt explicitly documents all three field meanings
- rules fallback maps each trusted source field to the correct target field
- LLM path is corrected by detected trusted values
