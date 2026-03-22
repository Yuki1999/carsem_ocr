# Header Quantity Semantics Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the three header quantity semantics so total quantity, good quantity, and total sheets each map from the right OCR fields.

**Architecture:** Update prompt wording, header alias fallback, and detected-field override logic together so the direct LLM path and fallback rules stay aligned.

**Tech Stack:** Python, pytest

---

## Chunk 1: Prompt and Mapping

### Task 1: Lock prompt wording with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test asserting the customs prompt documents:
- `TotalQuantity` from `Qty` / `Summary Quantity`
- `GoodQuantity` from `Gross Qty` / `Summary Gross Qty`
- `TotalSheets` from `Die Qty` / `WaferQty`

- [ ] **Step 2: Run test to verify it fails**

Run the targeted pytest command for the new prompt test.
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update prompt wording in `app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run the same command and confirm `1 passed`.

### Task 2: Lock fallback aliases and detected overrides with failing tests

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing tests**

Add tests showing:
- `Qty` maps to `TotalQuantity`
- `Gross Qty` maps to `GoodQuantity`
- `Die Qty` maps to `TotalSheets`
- detected `Summary Quantity`, `Summary Gross Qty`, and `Summary WaferQty` override incorrect LLM values

- [ ] **Step 2: Run tests to verify they fail**

Run the targeted pytest commands for the new tests.
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Adjust aliases and detected override fields only enough to satisfy the tests.

- [ ] **Step 4: Run tests to verify they pass**

Run the same commands and confirm they pass.

## Chunk 2: Verification

### Task 3: Run backend verification

**Files:**
- Test only

- [ ] **Step 1: Run backend customs tests**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass
