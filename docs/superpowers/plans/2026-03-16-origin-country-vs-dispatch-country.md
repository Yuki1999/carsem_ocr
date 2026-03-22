# Origin Country vs Dispatch Country Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure `OriginCountry` always means country of origin and never dispatch country in customs draft generation.

**Architecture:** Tighten the customs LLM prompt in `app/main.py`, keep rules fallback aligned in `app/customs_submission.py`, and prove the behavior with focused backend tests.

**Tech Stack:** Python, pytest

---

## Chunk 1: Backend Semantics

### Task 1: Lock prompt wording with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test asserting the customs prompt includes language that:
- defines `OriginCountry` as 原产国
- forbids using 启运国 / From
- prefers origin country when both values exist

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_customs_submission_prompt_distinguishes_origin_country_from_dispatch_country -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update `app/main.py` prompt text only enough to satisfy the test.

- [ ] **Step 4: Run test to verify it passes**

Run the same targeted pytest command and confirm `1 passed`.

### Task 2: Lock rules fallback with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a test with both:
- `原产国 = SG`
- `Country（启运国/From） = MY`

Verify the generated draft uses `OriginCountry == SG`.

- [ ] **Step 2: Run test to verify it fails or stays red if alias handling is wrong**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_prefers_origin_country_over_dispatch_country -q`
Expected: `FAIL` if behavior is missing, otherwise review whether rules already satisfy the requirement

- [ ] **Step 3: Write minimal implementation**

Adjust only the alias list or normalization needed so dispatch-country fields cannot populate `OriginCountry`.

- [ ] **Step 4: Run test to verify it passes**

Run the same targeted pytest command and confirm `1 passed`.

## Chunk 2: Verification

### Task 3: Run focused backend verification

**Files:**
- Test only

- [ ] **Step 1: Run backend customs tests**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass
