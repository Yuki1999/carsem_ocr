# Origin Country vs Dispatch Country Design

## Goal

Make `OriginCountry` unambiguously mean the goods' country of origin, not the dispatch/shipping country.

## Scope

- Strengthen the customs submission LLM prompt in `app/main.py`
- Keep rules-based fallback aligned with the same semantics
- Add backend tests covering both prompt wording and mapping behavior

## Required Behavior

- `OriginCountry` must map to 原产国 / Country of Origin / ORIGINAL OF COUNTRY
- `OriginCountry` must not map to 启运国 / 起运国 / From / dispatch country / export country
- If both origin country and dispatch country exist in the same source document, `OriginCountry` must use only the origin-country value

## Architecture

The current system already has two relevant layers:

1. LLM direct draft generation
2. rules-based fallback / alias mapping

This change must align both layers so they do not disagree. The prompt should guide the LLM strongly, while the fallback mapping should only recognize true origin-country aliases.

## Prompt Design

The customs-specific LLM prompt should explicitly state:

- `OriginCountry` means 原产国
- it must be extracted from fields such as `Country of Origin`, `原产国`, or `ORIGINAL OF COUNTRY`
- it must not use dispatch-country fields such as `启运国`, `From`, or other shipment-origin fields
- if both values appear, choose only the true origin country

## Rules Fallback Design

Rules fallback should keep `OriginCountry` limited to true origin-country aliases only.

Do not add dispatch-country aliases to `OriginCountry`.

## Testing

- prompt includes the new origin-country constraint
- a payload containing both 原产国 and 启运国 maps `OriginCountry` to 原产国
- existing origin-country mapping still works
