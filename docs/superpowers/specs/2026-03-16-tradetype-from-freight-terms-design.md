# TradeType From Freight Terms Design

## Goal

Keep the draft field name `TradeType`, but make its extraction source explicitly come from `Freight Terms` or `Incoterm`.

## Scope

- Strengthen the customs LLM prompt in `app/main.py`
- Add rules fallback aliases in `app/customs_submission.py`
- Add focused backend tests

## Required Behavior

- `TradeType` remains the draft and site payload field name
- `TradeType` should be extracted from `Freight Terms`, `Incoterm`, or `Incoterms`
- `TradeType` should not be inferred from unrelated transport, payment, or remark fields

## Architecture

This is a semantic change, not a protocol change. The draft contract stays the same so the frontend and site submission code remain compatible. The LLM prompt and rules fallback are aligned so both the direct LLM path and fallback mapping use the same source semantics.

## Testing

- prompt explicitly says `TradeType` comes from `Freight Terms` or `Incoterm`
- rules fallback maps `Freight Terms` to `TradeType`
- existing `TradeType` field handling continues to work
