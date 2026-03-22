# TotalSheets From Die Qty Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TotalSheets` be recognized from `Die Qty` or `WaferQty` while keeping the existing field contract unchanged.

**Architecture:** Update the customs prompt, rules fallback, and the detected-field override used after LLM draft generation so trusted die-quantity fields correct the final draft value.

**Tech Stack:** Python, pytest

---

## Chunk 1: Backend Prompt and Fallback

### Task 1: Lock prompt wording with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test asserting the customs prompt says `TotalSheets` comes from `Die Qty` or `WaferQty`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_customs_submission_prompt_maps_total_sheets_from_package_count -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update the prompt wording in `app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run the same command and confirm `1 passed`.

### Task 2: Lock aliasing and detected override with failing tests

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing tests**

Add tests showing:
- `Die Qty = 200` maps to `TotalSheets = 200`
- `llm_output.header.TotalSheets = 100` is overridden by detected `WaferQty = 200`

- [ ] **Step 2: Run tests to verify they fail**

Run the targeted pytest commands for the new tests.
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Add trusted aliases and include `TotalSheets` in the detected-field override logic.

- [ ] **Step 4: Run tests to verify they pass**

Run the same commands and confirm they pass.

## Chunk 2: Verification

### Task 3: Run backend verification

**Files:**
- Test only

- [ ] **Step 1: Run backend customs tests**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass
