# Customs Submit Playwright Mode Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persisted customs submission mode setting so both manual submission and auto mode can switch between the current HTTP engine and a new Playwright engine.

**Architecture:** Keep `submit_to_customs_site()` as the single business entrypoint, but route internally to `http` or `playwright` implementations. Persist the chosen mode in existing LLM settings and surface the active engine in submission metadata so the result center can explain which path executed.

**Tech Stack:** FastAPI, Python requests, Playwright for Python, Vue 3, Vitest, pytest

---

## Chunk 1: Settings Persistence

### Task 1: Add backend settings support for `customs_submit_mode`

**Files:**
- Modify: `app/llm_settings_store.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add a pytest that verifies:
- missing `customs_submit_mode` normalizes to `http`
- `playwright` persists as `playwright`
- invalid values normalize back to `http`

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because `customs_submit_mode` is not yet normalized/preserved.

- [ ] **Step 3: Write minimal implementation**

Update `normalize_llm_settings()`, `_default_settings()`, and `resolve_active_llm_config()` to include `customs_submit_mode`.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS for the new settings assertions.

- [ ] **Step 5: Commit**

```bash
git add app/llm_settings_store.py tests/test_customs_submission.py
git commit -m "feat: persist customs submit mode"
```

### Task 2: Add frontend settings support for `customs_submit_mode`

**Files:**
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/autoModePersistence.test.js`

- [ ] **Step 1: Write the failing test**

Add a Vitest case proving the settings persistence helpers keep `customs_submit_mode` through load/save cycles.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js`
Expected: FAIL because the field is currently ignored.

- [ ] **Step 3: Write minimal implementation**

Update settings normalization/build helpers in `App.vue` so `customs_submit_mode` is loaded, stored in reactive state, and included in save payloads.

- [ ] **Step 4: Run test to verify it passes**

Run the same test command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/autoModePersistence.test.js
git commit -m "feat: persist frontend customs submit mode"
```

## Chunk 2: Submission Engine Routing

### Task 3: Add failing tests for submission routing

**Files:**
- Modify: `tests/test_customs_submission.py`
- Modify: `app/main.py`
- Modify: `app/customs_browser.py`

- [ ] **Step 1: Write the failing tests**

Add pytest coverage for:
- manual/customs submit path passes `customs_submit_mode` into submission
- auto mode path also passes the configured mode
- submission metadata includes `submit_engine`

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because mode is not passed through yet.

- [ ] **Step 3: Write minimal implementation**

Update `main.py` and `customs_browser.py` so:
- settings are read for `customs_submit_mode`
- `submit_to_customs_site()` accepts a mode
- returned submit result contains `submit_engine`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/customs_browser.py tests/test_customs_submission.py
git commit -m "feat: route customs submissions by engine mode"
```

## Chunk 3: Playwright Engine

### Task 4: Add failing tests for Playwright availability and routing

**Files:**
- Create: `app/customs_playwright.py`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:
- `mode="playwright"` routes to Playwright implementation
- if Playwright import/setup fails, the user gets a clear `playwright_unavailable` style error

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because Playwright engine does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `app/customs_playwright.py` with a single focused entrypoint that:
- imports Playwright lazily
- logs into the site
- fetches declaration number
- fills fields
- submits and returns a normalized result

Route `submit_to_customs_site()` to this module when mode is `playwright`.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/customs_playwright.py app/customs_browser.py tests/test_customs_submission.py
git commit -m "feat: add playwright customs submit engine"
```

## Chunk 4: Settings UI and Result Visibility

### Task 5: Add the system settings toggle for submit mode

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Test: `frontend/src/autoModePersistence.test.js`

- [ ] **Step 1: Write the failing test**

Add a frontend test ensuring the settings state exposes and saves the selected mode.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js`
Expected: FAIL because the UI has no mode selection yet.

- [ ] **Step 3: Write minimal implementation**

Add a simple mode selector to the system settings card and wire it into the existing persistence flow.

- [ ] **Step 4: Run test to verify it passes**

Run the same command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/style.css frontend/src/autoModePersistence.test.js
git commit -m "feat: add customs submit mode toggle"
```

### Task 6: Show the active engine in result center

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/autoModeStatus.js`
- Test: `frontend/src/autoModeStatus.test.js`

- [ ] **Step 1: Write the failing test**

Add a Vitest case asserting that `submit_engine` is surfaced in computed result-center status data.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModeStatus.test.js`
Expected: FAIL because engine metadata is not displayed.

- [ ] **Step 3: Write minimal implementation**

Expose `submit_engine` in status helpers and show it in the result center near submit status.

- [ ] **Step 4: Run test to verify it passes**

Run the same command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/autoModeStatus.js frontend/src/autoModeStatus.test.js
git commit -m "feat: show customs submit engine in result center"
```

## Chunk 5: Verification

### Task 7: Run regression checks and restart services

**Files:**
- Modify: `app/main.py`
- Modify: `app/customs_browser.py`
- Create: `app/customs_playwright.py`
- Modify: `app/llm_settings_store.py`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/autoModePersistence.test.js`
- Modify: `frontend/src/autoModeStatus.test.js`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Run backend test suite**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: PASS.

- [ ] **Step 2: Run frontend targeted tests**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js src/autoModeStatus.test.js`
Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Restart services**

Restart the backend and frontend processes using the existing process manager.

- [ ] **Step 5: Verify health**

Run: `curl -s http://127.0.0.1:16068/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add app frontend tests
git commit -m "feat: add playwright customs submit mode"
```
