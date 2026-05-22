# Customs Material Packet Draft Design

## Goal

Support the first version of customs order draft generation at the level of one business packet, not one source file. A packet represents one customer commission / one set of customs materials / one customs order header. Invoice, packing list, and customer email are treated as sources for the same order draft.

## Confirmed Business Rules

- One packet generates one order header.
- Invoice and packing list are source files, not separate orders.
- Commodity details are generated from invoice original commodity rows.
- If two invoice rows are identical, they still produce two detail rows.
- Packing list rows are package-source rows. `C/T NO` rows are not commodity declaration rows.
- Packing list quantities are grouped by `ITEM + P/O No + SAMSUNG P/N` and used for matching, validation, and traceability.
- If invoice quantity differs from the grouped packing quantity, the draft is still generated. Invoice quantity is used, and the field is marked for manual review.
- Header conflicts across invoice, packing list, email, and rules receive a recommended value plus candidates. The field remains reviewable.
- Recommended values follow field-type priority:
  - Invoice fields: invoice number, currency, amount, unit price, origin country, commodity details.
  - Packing fields: package count, gross weight, net weight, volume, packaging type, packing quantity.
  - Email and rules: customer commission, business type, customs area, port, transport clues, supplier clues.
  - Semantic fields: shipper, consignee, destination/loading port, origin/destination place, final destination country use rules plus LLM judgment.

## Architecture

The first version adds a structured packet-draft layer on top of the existing extraction and customs submission draft flow.

```text
Source extraction results
  -> source-level structures
  -> packet merge and validation
  -> existing customs submission draft
```

This keeps current OCR, Excel parsing, LLM extraction, history, and submission APIs intact. The new layer produces extra metadata that the existing UI can display and edit without blocking order generation.

## Data Model

The existing draft remains:

```json
{
  "target": "vatest.carsem.com.cn",
  "header": {},
  "details": [],
  "meta": {}
}
```

The packet layer adds metadata under `meta.packet`:

```json
{
  "packet_id": "DS12650253",
  "source_files": [],
  "header_candidates": {},
  "field_reviews": [],
  "invoice_lines": [],
  "packing_groups": [],
  "detail_reviews": []
}
```

`header_candidates` stores recommended values and source candidates for manual selection. `detail_reviews` stores quantity checks and source row references for each invoice detail row.

## Commodity Detail Rules

The draft detail count equals the invoice original commodity row count.

For each invoice row:

```text
ItemCode       <- invoice SAMSUNG P/N / P/N / item code
ItemQuantity   <- invoice PC / Quantity
ItemGoodQuantity <- invoice PC / Quantity, when no better good quantity exists
ItemUnitPrice  <- invoice @RMB/1000 / @USD/1000 / unit price
ItemPrice      <- invoice RMB / USD / amount
ItemOrigin     <- invoice origin country
```

Packing rows are grouped with:

```text
ITEM + P/O No + SAMSUNG P/N
```

The group quantity is compared with the invoice row quantity for the same key. Mismatch does not block generation.

## Review Behavior

The draft can be saved and submitted even when review items exist. Review metadata is advisory and visible in the workspace:

- header conflicts
- header missing values
- detail quantity mismatch
- detail missing invoice fields
- unmatched packing groups

Manual edits continue to use the existing draft save endpoint.

## Testing

Backend tests cover:

- invoice original rows produce detail rows without merging
- packing rows are grouped for validation
- quantity mismatch still generates details and marks review
- header conflict metadata keeps recommended values and candidates

Frontend tests cover:

- draft normalization preserves packet metadata
- summary counts review items
