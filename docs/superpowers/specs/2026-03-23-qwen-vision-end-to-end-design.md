# Qwen Vision End-to-End OCR Design

## Background

The project already supports two OCR/parser engines:

1. `MinerU`
2. `OpenDataLoader PDF`

Both engines eventually feed the shared LLM extraction path. The new requirement is to add a third selectable engine that uses `qwen3.5-plus` as an end-to-end multimodal model for document understanding and field extraction.

## Goal

Add a new OCR engine option that lets users choose a Qwen-based end-to-end extraction flow from the frontend while keeping `MinerU` as the default engine.

## Scope

In scope:

- Add a third OCR engine option in frontend and backend
- Reuse the existing LLM runtime settings (`llm_base_url`, `llm_model`, `llm_api_key`)
- Support `PDF` and image files for the new engine
- Use the multimodal model to perform recognition and field extraction in a single model call path
- Persist enough evidence for result-center inspection

Out of scope for this iteration:

- Direct support for Office files in the Qwen engine
- Automatic Office-to-PDF conversion for the Qwen engine
- Replacing `MinerU` as the default engine

## Product Behavior

### OCR Engine Selector

The frontend OCR engine selector will expose:

- `MinerU`
- `OpenDataLoader PDF`
- `Qwen3.5-Plus 端到端`

Default remains `MinerU`.

### File Support

For `qwen_vision`:

- Supported: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.gif`
- Rejected: `.doc`, `.docx`, `.ppt`, `.pptx`

If a user selects the Qwen engine and uploads an unsupported Office document, the backend should return a clear validation error explaining that the engine currently supports only PDF and image files.

## Architecture

Introduce a dedicated extractor module for the new engine instead of forcing it through the text-only LLM extraction helper.

### New Module

Add `app/qwen_vision_extractor.py` with responsibilities:

- validate file type compatibility for the Qwen engine
- convert PDFs into page images
- normalize image inputs for multimodal requests
- call the OpenAI-compatible chat completions API using image content plus extraction instructions
- parse the model response into normalized extraction payload fields
- build evidence assets for history persistence

### Main Flow Integration

`app.main._build_extract_payload()` will gain a third OCR-engine branch:

- `mineru` -> existing MinerU flow
- `opendataloader` -> existing OpenDataLoader flow
- `qwen_vision` -> new Qwen end-to-end flow

Unlike the other two engines, the Qwen branch will not call `run_llm_extract()` afterward, because extraction is already done by the same multimodal model call.

## Request and Response Contract

### New OCR Engine Value

- `ocr_engine=qwen_vision`

### Response Metadata

The result payload should continue to expose:

- `ocr_engine`
- `ocr_engine_label`
- `detected`
- `preview`
- `llm_content_preview`

For the Qwen engine:

- `ocr_engine` = `qwen_vision`
- `ocr_engine_label` = `Qwen3.5-Plus 端到端`
- `llm_model` should reflect the configured model name, typically `qwen3.5-plus`
- `preview` should contain a readable text preview derived from the model output or OCR summary

## Multimodal Prompting Strategy

The Qwen engine should use one model call that combines:

- the user extraction instruction (`llm_prompt`)
- optional target field hints (`fields`)
- document images or PDF page images

The system instruction should require:

- strict extraction from visible content only
- JSON object output only
- empty strings for missing scalar fields
- empty arrays for missing detail lists

The parser should remain tolerant of common model formatting issues:

- fenced JSON blocks
- leading explanation text plus embedded JSON
- array/object mixtures that still contain one top-level JSON object

## Evidence and History Persistence

The result center should remain usable even though the Qwen engine does not naturally emit MinerU-style `markdown/json/text` bundles.

Persist the following evidence assets:

- original upload
- PDF page render images or original image input copies
- raw model response snapshot
- normalized text preview file
- standard `meta.json`

This allows users to inspect both what was shown to the model and what the model returned.

## Error Handling

### Validation Errors

- unsupported file type for `qwen_vision`
- missing runtime LLM base URL
- missing runtime model name

### Runtime Errors

- PDF-to-image conversion failure
- multimodal request failure
- model response not parseable as JSON

Errors should clearly mention the Qwen engine instead of reusing old MinerU-specific text.

## Frontend Behavior

Frontend changes should stay minimal and consistent with the current OCR engine selector pattern.

- extend OCR engine options with `qwen_vision`
- keep default as `mineru`
- include the new engine in template normalization and extract request submission
- display the selected engine in workspace and result-center summaries

No separate Qwen-specific settings panel is needed in this iteration because runtime config is reused from the existing LLM settings.

## Testing

### Backend

- default OCR engine remains `mineru`
- dispatch selects `qwen_vision` when requested
- `qwen_vision` rejects Office files
- Qwen extractor parses JSON payloads from normal and fenced responses
- history persistence includes Qwen evidence assets
- async extract task preserves Qwen engine metadata

### Frontend

- OCR engine options include `qwen_vision`
- default remains `mineru`
- submit flow sends `qwen_vision`
- template normalization preserves `qwen_vision`

## Risks and Tradeoffs

- PDF page rendering adds local runtime dependencies and processing time
- multimodal model output may be less structurally stable than a pure OCR-plus-parser pipeline
- a single end-to-end model call is simpler to use, but troubleshooting extraction mistakes may require stronger evidence capture

## Recommendation

Implement `qwen_vision` as a third OCR engine that reuses the existing LLM credentials, supports only PDF and image files for now, and stores explicit visual evidence plus raw model output for debugging and review.
