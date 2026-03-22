# Auto Mode Direct Customs Submit Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make auto mode upload tasks continue directly into customs submission and show the full pipeline progress and outcome in the result center.

**Architecture:** Keep one backend extraction task as the pipeline owner. Extend it so auto mode writes draft status before submit, treats customs failure as task failure, and returns enough result metadata for the frontend result center to present the full automatic flow.

**Tech Stack:** Python, FastAPI, Vue 3, pytest

---

## Chunk 1: Backend Auto-Mode Task Semantics

### Task 1: Lock failed-task semantics for customs rejection

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a backend test showing that when auto mode is enabled and customs submission raises a runtime rejection, the extract task ends in `failed` and the history record still contains the generated draft plus failed submission metadata.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_run_extract_task_auto_mode_marks_task_failed_when_customs_submit_fails -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update `app/main.py` so auto-mode customs submission:
- sets submission meta to `running` before submit
- catches submission failure
- persists failed submission meta to history
- marks the extract task as `failed`

- [ ] **Step 4: Run test to verify it passes**

Run the same targeted pytest command and confirm `1 passed`.

### Task 2: Lock success-path metadata for result center

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a backend test showing that a successful auto-mode run stores:
- `auto_mode_enabled`
- `auto_mode_status = succeeded`
- `auto_mode_message`
- `submission.meta.submit_status = succeeded`
- `submission.meta.submit_message`

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_run_extract_task_auto_mode_persists_success_submission_meta -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Keep the current success flow, but ensure the history record is updated with `running -> succeeded` submission meta transitions and the extract task result includes the final auto-mode fields.

- [ ] **Step 4: Run test to verify it passes**

Run the same targeted pytest command and confirm `1 passed`.

## Chunk 2: Result Center Progress Presentation

### Task 3: Lock frontend presentation of auto-mode customs progress

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/App.test.js` or existing relevant frontend test file
- Test: `frontend` test suite for result-center behavior

- [ ] **Step 1: Write the failing test**

Add a frontend test that mounts the result center with an auto-mode task result and verifies the UI shows:
- stage/message for customs auto-submit
- auto-mode final status/message
- submission meta status/message

- [ ] **Step 2: Run test to verify it fails**

Run the targeted frontend test command for the chosen file.
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Update the result center summary area to show the automatic pipeline stages and final customs submission outcome using the task result and stored submission meta.

- [ ] **Step 4: Run test to verify it passes**

Run the targeted frontend test command and confirm `PASS`.

## Chunk 3: Verification

### Task 4: Run focused verification

**Files:**
- Test only

- [ ] **Step 1: Run backend customs suite**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass

- [ ] **Step 2: Run relevant frontend tests**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- <targeted-result-center-test-file>`
Expected: all targeted tests pass

- [ ] **Step 3: Restart backend and verify health**

Run: `pm2 restart carsem-ocr-backend`
Run: `curl -s http://127.0.0.1:16068/api/health`
Expected: `{"status":"ok"}`
