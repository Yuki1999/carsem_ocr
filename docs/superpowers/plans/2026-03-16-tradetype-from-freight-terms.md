# TradeType From Freight Terms Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `TradeType` be recognized from `Freight Terms` or `Incoterm` while keeping the existing field contract unchanged.

**Architecture:** Update the customs prompt and rules fallback only. Keep the draft field name `TradeType` and the site payload unchanged to avoid broad compatibility churn.

**Tech Stack:** Python, pytest

---

## Chunk 1: Backend Prompt and Fallback

### Task 1: Lock prompt wording with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test asserting the customs prompt says `TradeType` comes from `Freight Terms` or `Incoterm`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_customs_submission_prompt_maps_trade_type_from_freight_terms_or_incoterm -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update the prompt wording in `app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run the same command and confirm `1 passed`.

### Task 2: Lock rules fallback aliasing with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test showing `Freight Terms = FOB` maps to `TradeType = FOB`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_maps_trade_type_from_freight_terms -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Add `TradeType` aliases for `Freight Terms`, `Incoterm`, and `Incoterms`.

- [ ] **Step 4: Run test to verify it passes**

Run the same command and confirm `1 passed`.

## Chunk 2: Verification

### Task 3: Run backend verification

**Files:**
- Test only

- [ ] **Step 1: Run backend customs tests**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass
