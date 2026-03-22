# Customs Draft Mawb Hawb Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将报关草稿字段切换为 `Mawb/Hawb`，并让未识别字段在报关填报工作区自动填入 `无`。

**Architecture:** 后端统一负责报关草稿归一化、旧字段兼容和网站提交流程转换；前端只消费和编辑归一化后的新协议。LLM 和规则映射都输出相同的草稿结构，减少分支差异。

**Tech Stack:** FastAPI, Python, Vue 3, Element Plus, Vitest, pytest

---

## Chunk 1: Backend Draft Contract

### Task 1: Add failing backend tests for Mawb Hawb contract

**Files:**
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- rule mapping writes `header["Mawb"]`
- LLM draft reads `Mawb/Hawb`
- missing fields normalize to `无`
- no details creates one placeholder detail row

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_customs_submission.py -q`
Expected: FAIL on old `MainBLNo/SubBLNo` assumptions

- [ ] **Step 3: Write minimal implementation**

Modify backend draft helpers in `app/customs_submission.py` to:
- replace `MainBLNo/SubBLNo` with `Mawb/Hawb`
- normalize blanks to `无`
- migrate legacy drafts on read/merge

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_customs_submission.py -q`
Expected: PASS

## Chunk 2: Backend Submission Compatibility

### Task 2: Add failing backend tests for submit payload conversion

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/customs_browser.py`

- [ ] **Step 1: Write the failing test**

Add a payload flattening test verifying:
- `Mawb` maps to `MainBLNo`
- `Hawb` maps to `SubBLNo`

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_customs_submission.py -q`
Expected: FAIL because payload still reads old draft keys

- [ ] **Step 3: Write minimal implementation**

Update `app/customs_browser.py` payload flattening to read `Mawb/Hawb`.

- [ ] **Step 4: Run tests to verify it passes**

Run: `pytest tests/test_customs_submission.py -q`
Expected: PASS

## Chunk 3: API Prompt and Frontend Draft Helpers

### Task 3: Add failing frontend tests for draft normalization

**Files:**
- Modify: `frontend/src/submissionDraft.test.js`
- Modify: `frontend/src/submissionDraft.js`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- `createEmptySubmissionDraft()` defaults `Mawb/Hawb` to `无`
- legacy `MainBLNo/SubBLNo` normalize into `Mawb/Hawb`

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- submissionDraft.test.js`
Expected: FAIL on old field names and blank defaults

- [ ] **Step 3: Write minimal implementation**

Update:
- `frontend/src/submissionDraft.js`
- LLM draft schema prompt in `app/main.py`

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- submissionDraft.test.js`
Expected: PASS

## Chunk 4: UI Wiring and Full Verification

### Task 4: Update UI labels and verify end-to-end consistency

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Update field rendering to use normalized draft fields**

Ensure the report workspace renders `Mawb/Hawb` and persists `无` defaults.

- [ ] **Step 2: Run backend and frontend targeted tests**

Run: `pytest tests/test_customs_submission.py -q`
Expected: PASS

Run: `cd frontend && npm test -- submissionDraft.test.js`
Expected: PASS

- [ ] **Step 3: Run combined verification**

Run: `pytest tests/test_customs_submission.py -q && cd frontend && npm test -- submissionDraft.test.js`
Expected: all green
