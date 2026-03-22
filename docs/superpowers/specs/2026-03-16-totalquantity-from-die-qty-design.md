# TotalSheets From Die Qty Design

## Goal

Keep the draft field name `TotalSheets`, but make it represent total die/wafer quantity rather than package count or generic quantity.

## Scope

- strengthen the customs LLM prompt in `app/main.py`
- add rules fallback aliases in `app/customs_submission.py`
- apply detected-field override for trusted quantity aliases
- add focused backend tests

## Required Behavior

- `TotalSheets` remains the draft and site payload field name
- `TotalSheets` should be extracted from `Die Qty`, `WaferQty`, `Wafer Qty`, or similar total-die fields
- if OCR result contains one of these trusted fields, it should override an incorrect LLM value

## Testing

- prompt explicitly says `TotalSheets` means total die quantity from `Die Qty` or `WaferQty`
- rules fallback maps `Die Qty` to `TotalSheets`
- LLM path is corrected by detected `Die Qty` / `WaferQty` values
