# TotalSheets From Package Count Design

## Goal

Keep the draft field name `TotalSheets`, but make it represent package count / 件数 rather than literal sheet pages.

## Scope

- strengthen the customs LLM prompt in `app/main.py`
- add rules fallback aliases in `app/customs_submission.py`
- add focused backend tests

## Required Behavior

- `TotalSheets` remains the draft and site payload field name
- `TotalSheets` should be extracted from 件数 / 件数（如 CTN） / CTN / Carton / Packages style fields
- `TotalSheets` should not be interpreted as document pages or generic sheets count unless it clearly means package count

## Architecture

This is a semantic change only. The field contract and site payload stay unchanged. Prompt guidance and fallback aliases are aligned so both the LLM path and rules path use the same package-count meaning.

## Testing

- prompt explicitly says `TotalSheets` means 件数 / package count
- rules fallback maps `件数（如 CTN）` to `TotalSheets`
- existing numeric normalization for `TotalSheets` still works
