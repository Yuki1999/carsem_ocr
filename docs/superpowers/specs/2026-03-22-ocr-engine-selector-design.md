# OCR Engine Selector Design

## Background

The current extraction pipeline uses MinerU as the only OCR/parser engine:

1. OCR / document parsing
2. LLM-based structured extraction
3. History persistence and result-center display

The user wants to add `opendataloader-pdf` as an additional OCR pipeline while keeping MinerU as the default choice.

## Goal

Allow users to choose the OCR engine in the frontend while keeping the rest of the extraction flow unchanged.

## Required Behavior

- The extraction workspace must expose an OCR engine selector
- Default OCR engine remains `MinerU`
- Users can switch to `OpenDataLoader PDF`
- Backend extraction APIs must accept the selected engine for both sync and async flows
- LLM extraction, history persistence, and result display stay on the shared downstream path
- Existing MinerU behavior remains backward compatible for templates and older payloads

## Architecture

Introduce a small OCR-engine dispatch layer in the backend.

- `MinerU` continues to use the existing official API flow
- `OpenDataLoader PDF` gets a dedicated extractor module
- `app.main._build_extract_payload()` chooses the extractor based on `ocr_engine`
- Both extractors return a normalized output shape with shared keys such as `text`, `markdown`, `json`, `middle_json`, and optional package metadata

This keeps OCR-specific code isolated while minimizing changes to LLM extraction, history, and result presentation.

## OpenDataLoader Integration

The deployment environment may install:

- `Java 11+`
- `opendataloader-pdf`
- `opendataloader-pdf[hybrid]`
- a local `opendataloader-pdf-hybrid` backend service

The backend integration should:

- call the local Python package or CLI from the FastAPI service
- support hybrid OCR mode for scanned PDFs
- expose environment-based configuration for hybrid URL, OCR language, and force-OCR behavior
- gracefully fail with a clear error message when runtime dependencies are missing

## Frontend Behavior

- Add OCR engine selection to the extraction workspace
- Persist OCR engine as part of template configuration so each vendor/doc-type pair can carry its preferred engine
- Show the chosen engine in workspace and result-center summaries

## Data Contract

New request field:

- `ocr_engine`: one of `mineru`, `opendataloader`

New response/result metadata:

- `ocr_engine`
- `ocr_engine_label`

Existing MinerU fields like `model_version`, `parse_method`, and `lang_list` remain available. For OpenDataLoader runs, they may be repurposed or left informational where not applicable.

## Failure Handling

- Invalid OCR engine value should return a 400-level validation error
- Missing OpenDataLoader runtime dependencies should return a clear runtime error
- If OpenDataLoader cannot produce structured layout JSON, the pipeline should still continue with text/markdown when possible

## Testing

### Backend

- OCR engine dispatch selects MinerU by default
- OCR engine dispatch selects OpenDataLoader when requested
- OpenDataLoader outputs are normalized for downstream LLM extraction
- Async extract task preserves selected OCR engine in task results

### Frontend

- Default OCR engine is MinerU
- Template normalization preserves `ocr_engine`
- Submit flow sends selected `ocr_engine`
