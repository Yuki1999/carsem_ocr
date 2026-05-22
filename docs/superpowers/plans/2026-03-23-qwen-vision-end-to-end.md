# Qwen Vision End-to-End OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third OCR engine that uses `qwen3.5-plus` to perform end-to-end multimodal recognition and field extraction for PDF and image uploads.

**Architecture:** Keep the existing shared extract API and result-center flow, but add a dedicated `qwen_vision` branch in the backend. That branch will convert PDFs into page images, call the OpenAI-compatible multimodal chat endpoint directly, normalize the JSON response, and persist visual evidence assets plus model output snapshots.

**Tech Stack:** Python, FastAPI, Vue 3, pytest, Vitest, OpenAI-compatible chat completions API

---

### Task 1: Lock backend routing and validation with failing tests

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test for OCR-engine normalization**

Add tests that assert:

```python
def test_normalize_ocr_engine_accepts_qwen_vision():
    import app.main as main_mod
    assert main_mod._normalize_ocr_engine("qwen_vision") == "qwen_vision"


def test_ocr_engine_label_for_qwen_vision():
    import app.main as main_mod
    assert main_mod._ocr_engine_label("qwen_vision") == "Qwen3.5-Plus 端到端"
```

- [ ] **Step 2: Write the failing test for backend dispatch**

Add a test that asserts `_build_extract_payload()` routes to the Qwen extractor when `ocr_engine="qwen_vision"` and does not call `run_mineru_and_read_text()` or `run_opendataloader_and_read_text()`.

- [ ] **Step 3: Write the failing test for Office-file rejection**

Add a test that asserts:

```python
with pytest.raises(ValueError, match="Qwen3.5-Plus.*仅支持 PDF 和图片"):
    main_mod._build_extract_payload(
        file_name="demo.docx",
        ...
        ocr_engine="qwen_vision",
    )
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run: `PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_customs_submission.py -k "qwen_vision or qwen vision" -q`

Expected: `FAIL` because the new engine is not implemented yet.

- [ ] **Step 5: Implement the minimal dispatch changes**

Modify `app/main.py` to:

- accept `qwen_vision` in `_normalize_ocr_engine()`
- return `Qwen3.5-Plus 端到端` from `_ocr_engine_label()`
- branch to `run_qwen_vision_extract()` inside `_build_extract_payload()`
- short-circuit unsupported Office files with a Qwen-specific validation error

- [ ] **Step 6: Re-run the targeted backend tests**

Run the same pytest command and confirm the new routing/validation tests pass.

- [ ] **Step 7: Commit the backend routing change**

Run:

```bash
git add app/main.py tests/test_customs_submission.py
git commit -m "feat: add qwen vision engine routing"
```

### Task 2: Build the Qwen multimodal extractor with TDD

**Files:**
- Create: `app/qwen_vision_extractor.py`
- Create: `tests/test_qwen_vision_extractor.py`
- Modify: `app/main.py`
- Test: `tests/test_qwen_vision_extractor.py`

- [ ] **Step 1: Write the failing parser tests**

Add tests for response parsing that cover:

```python
def test_parse_qwen_response_accepts_plain_json(): ...
def test_parse_qwen_response_accepts_fenced_json(): ...
def test_parse_qwen_response_extracts_embedded_json_object(): ...
def test_parse_qwen_response_raises_on_non_json_output(): ...
```

- [ ] **Step 2: Write the failing payload-builder test**

Add a test that asserts the extractor builds an OpenAI-compatible multimodal request shaped like:

```python
{
    "model": "qwen3.5-plus",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": [
            {"type": "text", "text": "..."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        ]},
    ],
}
```

- [ ] **Step 3: Write the failing evidence-assets test**

Add a test that asserts the extractor returns normalized history assets such as:

- `qwen_vision/raw-response.json`
- `qwen_vision/preview.txt`
- `qwen_vision/pages/page-1.png`

- [ ] **Step 4: Run the extractor test file to verify it fails**

Run: `PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_qwen_vision_extractor.py -q`

Expected: `FAIL` because the module does not exist yet.

- [ ] **Step 5: Implement the minimal extractor**

Create `app/qwen_vision_extractor.py` with focused helpers:

- `validate_qwen_vision_suffix(file_name: str) -> None`
- `render_qwen_input_images(file_name: str, file_bytes: bytes) -> list[dict[str, Any]]`
- `build_qwen_vision_messages(...) -> list[dict[str, Any]]`
- `parse_qwen_vision_response(raw_content: str) -> dict[str, Any]`
- `run_qwen_vision_extract(...) -> dict[str, Any]`

Implementation notes:

- images should be passed as base64 `data:` URLs for portability
- PDFs should render into page PNGs using the project’s existing PDF tooling if available; otherwise add the smallest local helper needed
- reuse the JSON-cleaning patterns already present in `app/llm_extract.py`

- [ ] **Step 6: Re-run the extractor tests**

Run the same pytest command and confirm the parser, payload, and evidence tests pass.

- [ ] **Step 7: Commit the extractor implementation**

Run:

```bash
git add app/qwen_vision_extractor.py tests/test_qwen_vision_extractor.py app/main.py
git commit -m "feat: add qwen vision extractor"
```

### Task 3: Integrate Qwen results into the shared history/result flow

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing history-persistence test**

Add a test that asserts `_build_extract_payload()` persists `history_assets` returned by the Qwen extractor and includes:

```python
assert any(item["path"] == "qwen_vision/raw-response.json" for item in extra_assets)
assert payload["ocr_engine"] == "qwen_vision"
assert payload["llm_model"] == "qwen3.5-plus"
```

- [ ] **Step 2: Write the failing async-task metadata test**

Add a test that asserts `_run_extract_task()` returns task results carrying:

- `ocr_engine = "qwen_vision"`
- `ocr_engine_label = "Qwen3.5-Plus 端到端"`

- [ ] **Step 3: Run the targeted backend tests to verify they fail**

Run: `PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_customs_submission.py -k "qwen_vision and (history or task or payload)" -q`

Expected: `FAIL`

- [ ] **Step 4: Implement the minimal integration**

Update `app/main.py` so the Qwen branch:

- populates `detected` from the extractor result directly
- sets `preview` from the normalized preview text
- sets `llm_content_preview` from the raw model response preview
- skips the second `run_llm_extract()` call
- appends returned `history_assets` into `extra_assets`

- [ ] **Step 5: Re-run the targeted backend tests**

Run the same pytest command and confirm the integration tests pass.

- [ ] **Step 6: Commit the history/result integration**

Run:

```bash
git add app/main.py tests/test_customs_submission.py
git commit -m "feat: persist qwen vision extract results"
```

### Task 4: Add frontend engine selection coverage

**Files:**
- Modify: `frontend/src/ocrEngine.js`
- Modify: `frontend/src/ocrEngine.test.js`
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/ocrEngine.test.js`

- [ ] **Step 1: Write the failing frontend tests**

Extend `frontend/src/ocrEngine.test.js` to assert:

```js
expect(OCR_ENGINE_OPTIONS.some((item) => item.value === 'qwen_vision')).toBe(true)
expect(ocrEngineLabel('qwen_vision')).toBe('Qwen3.5-Plus 端到端')
expect(buildExtractRequestFields({ ocr_engine: 'qwen_vision' }).ocr_engine).toBe('qwen_vision')
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run: `cd /home/qqr/carsem_ocr/frontend && node ./node_modules/vitest/vitest.mjs run src/ocrEngine.test.js`

Expected: `FAIL`

- [ ] **Step 3: Implement the minimal frontend support**

Update:

- `frontend/src/ocrEngine.js` to include the new option and label
- `frontend/src/App.vue` to preserve and display `qwen_vision` in forms, templates, and result summaries

- [ ] **Step 4: Re-run the frontend test**

Run the same Vitest command and confirm it passes.

- [ ] **Step 5: Commit the frontend engine support**

Run:

```bash
git add frontend/src/ocrEngine.js frontend/src/ocrEngine.test.js frontend/src/App.vue
git commit -m "feat: add qwen vision frontend selector"
```

### Task 5: Document runtime setup and supported behavior

**Files:**
- Modify: `README.md`
- Modify: `用户使用说明.md`

- [ ] **Step 1: Update backend/runtime docs**

Document:

- the new `ocr_engine=qwen_vision`
- that the engine reuses `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`
- that it currently supports only PDF and image files
- example configuration for an OpenAI-compatible Qwen endpoint

- [ ] **Step 2: Update user-facing usage docs**

Explain:

- when to choose `Qwen3.5-Plus 端到端`
- why Office files are not supported in this mode yet
- what evidence users will see in the result center

- [ ] **Step 3: Commit the docs update**

Run:

```bash
git add README.md 用户使用说明.md
git commit -m "docs: describe qwen vision engine"
```

### Task 6: Run focused verification and final regression checks

**Files:**
- Test: `tests/test_customs_submission.py`
- Test: `tests/test_qwen_vision_extractor.py`
- Test: `frontend/src/ocrEngine.test.js`

- [ ] **Step 1: Run focused backend checks**

Run:

```bash
PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_qwen_vision_extractor.py -q
PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_customs_submission.py -k "qwen_vision or qwen vision" -q
```

Expected: both commands pass.

- [ ] **Step 2: Run focused frontend checks**

Run:

```bash
cd /home/qqr/carsem_ocr/frontend && node ./node_modules/vitest/vitest.mjs run src/ocrEngine.test.js
```

Expected: pass.

- [ ] **Step 3: Run broader smoke verification**

Run:

```bash
PYTHONPATH=/home/qqr/carsem_ocr pytest -q
cd /home/qqr/carsem_ocr/frontend && npm run build
```

Expected: test suite stays green and frontend build succeeds.

- [ ] **Step 4: Summarize any remaining runtime follow-up**

Record any environment prerequisites discovered during implementation, especially PDF rendering dependencies or provider-specific multimodal payload quirks.
