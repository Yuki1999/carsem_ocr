# OCR Engine Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend-selectable OCR engine with MinerU as default and OpenDataLoader PDF as an alternate pipeline.

**Architecture:** Keep one shared extraction flow and insert a backend OCR dispatch layer ahead of LLM extraction. Persist the selected OCR engine through templates, requests, task results, and history-friendly response payloads.

**Tech Stack:** Python, FastAPI, Vue 3, pytest, Vitest

---

### Task 1: Lock backend OCR-engine dispatch with failing tests

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Create: `app/opendataloader_extractor.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add backend tests covering:
- `_build_extract_payload()` defaults to `mineru`
- `_build_extract_payload()` routes to OpenDataLoader when `ocr_engine=opendataloader`
- the normalized response payload carries `ocr_engine`

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_customs_submission.py -k "ocr_engine or opendataloader" -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Add OCR engine normalization and dispatch in `app/main.py`, then implement `app/opendataloader_extractor.py` with a normalized output shape.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm the targeted tests pass.

### Task 2: Lock frontend OCR-engine defaults and request payload

**Files:**
- Create: `frontend/src/ocrEngine.js`
- Create: `frontend/src/ocrEngine.test.js`
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/ocrEngine.test.js`

- [ ] **Step 1: Write the failing test**

Add frontend tests covering:
- default OCR engine is `mineru`
- template normalization preserves `ocr_engine`
- request payload builder includes selected `ocr_engine`

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/qqr/carsem_ocr/frontend && node ./node_modules/vitest/vitest.mjs run src/ocrEngine.test.js`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Extract OCR-engine defaults/helpers into `frontend/src/ocrEngine.js` and wire `App.vue` to use them in template normalization, editor state, and submit flow.

- [ ] **Step 4: Run test to verify it passes**

Run the same Vitest command and confirm the targeted tests pass.

### Task 3: Surface OCR-engine choice in UI and task results

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `app/main.py`
- Test: targeted backend/frontend tests above

- [ ] **Step 1: Update UI**

Add the OCR engine selector to template editing and extraction workspace, keeping MinerU as the default.

- [ ] **Step 2: Update task/result metadata**

Ensure async task results and response payloads expose the selected OCR engine for result-center display.

- [ ] **Step 3: Verify targeted tests**

Run both targeted backend and frontend test commands and confirm they remain green.

### Task 4: Update docs and run focused verification

**Files:**
- Modify: `README.md`
- Modify: `用户使用说明.md`

- [ ] **Step 1: Document deployment**

Add OpenDataLoader PDF dependency and hybrid-service deployment instructions.

- [ ] **Step 2: Document usage**

Explain how users choose the OCR engine in the frontend and what MinerU vs OpenDataLoader means in practice.

- [ ] **Step 3: Run focused verification**

Run:
- `PYTHONPATH=/home/qqr/carsem_ocr pytest /home/qqr/carsem_ocr/tests/test_customs_submission.py -k "ocr_engine or opendataloader" -q`
- `cd /home/qqr/carsem_ocr/frontend && node ./node_modules/vitest/vitest.mjs run src/ocrEngine.test.js`

Expected: targeted checks pass.
