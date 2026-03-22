# Local Agent Customs Submit Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-agent execution mode so customs submission can be executed on a user’s computer while OCR and draft generation remain on the server.

**Architecture:** Keep the server as the system of record for OCR, drafts, history, and result-center state. Introduce an agent registry plus pull-based local execution tasks so a lightweight local program can poll, execute Playwright locally, and report results back.

**Tech Stack:** FastAPI, Python, Playwright for Python, Vue 3, Vitest, pytest

---

## Chunk 1: Settings and Data Model

### Task 1: Extend settings to support `local_agent` mode

**Files:**
- Modify: `app/llm_settings_store.py`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add pytest coverage verifying:
- `customs_submit_mode` accepts `local_agent`
- `local_agent_id` is preserved
- invalid values normalize safely

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because settings do not yet support `local_agent_id`.

- [ ] **Step 3: Write minimal implementation**

Update settings normalization/defaults to include:
- `customs_submit_mode`
- `local_agent_id`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/llm_settings_store.py tests/test_customs_submission.py
git commit -m "feat: add local agent submit settings"
```

### Task 2: Add local-agent aware frontend settings helpers

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/llmSettings.js`
- Test: `frontend/src/autoModePersistence.test.js`

- [ ] **Step 1: Write the failing test**

Add a Vitest case proving `loadLlmSettings()` and payload building preserve:
- `customs_submit_mode = local_agent`
- `local_agent_id`

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js`
Expected: FAIL because helpers do not preserve `local_agent_id`.

- [ ] **Step 3: Write minimal implementation**

Update frontend settings helpers and state to carry:
- `customs_submit_mode`
- `local_agent_id`

- [ ] **Step 4: Run test to verify it passes**

Run the same test command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/llmSettings.js frontend/src/autoModePersistence.test.js
git commit -m "feat: persist local agent settings"
```

## Chunk 2: Agent Registry

### Task 3: Add backend local-agent registry APIs

**Files:**
- Create: `app/local_agent_store.py`
- Modify: `app/main.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add pytest coverage for:
- agent registration
- heartbeat updates
- listing online agents
- offline timeout classification

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because local-agent APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

Create a small store module and API endpoints:
- `POST /api/local-agents/register`
- `POST /api/local-agents/heartbeat`
- `GET /api/local-agents`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/local_agent_store.py app/main.py tests/test_customs_submission.py
git commit -m "feat: add local agent registry apis"
```

## Chunk 3: Local Submission Task Flow

### Task 4: Make submit paths create local-agent tasks instead of server execution

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add pytest coverage proving:
- manual submit creates a queued local task when mode is `local_agent`
- auto mode also creates a queued local task instead of calling server submit directly
- tasks include `assigned_agent_id`

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because submit paths still execute on the server.

- [ ] **Step 3: Write minimal implementation**

Update submit entrypoints so `local_agent` mode:
- validates selected online agent
- creates a pending local execution task
- records `submit_engine = local_agent`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_customs_submission.py
git commit -m "feat: queue customs submit for local agent"
```

### Task 5: Add agent poll/report APIs for customs tasks

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- `poll-customs-task` returns only tasks assigned to the requesting agent
- `report-customs-task` updates history and task state on success
- `report-customs-task` updates history and task state on failure

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because poll/report APIs do not exist.

- [ ] **Step 3: Write minimal implementation**

Add:
- `POST /api/local-agents/{agent_id}/poll-customs-task`
- `POST /api/local-agents/{agent_id}/report-customs-task`

Ensure history submission metadata is updated with:
- `submit_engine`
- `assigned_agent_id`
- final result state

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_customs_submission.py
git commit -m "feat: add local agent customs task poll and report"
```

## Chunk 4: Local Agent Program

### Task 6: Create a minimal local-agent worker

**Files:**
- Create: `agent/local_customs_agent.py`
- Create: `agent/README.md`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

Add isolated tests for the worker logic:
- registers itself
- polls one task
- executes submit callback
- reports success/failure

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: FAIL because local worker module does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a small CLI worker that:
- reads config from env or simple JSON
- registers/heartbeats
- polls assigned tasks
- runs local Playwright submission
- reports outcome

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/local_customs_agent.py agent/README.md tests/test_customs_submission.py
git commit -m "feat: add local customs agent worker"
```

## Chunk 5: Frontend Settings and Result Center

### Task 7: Add local-agent selection in system settings

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Test: `frontend/src/autoModePersistence.test.js`

- [ ] **Step 1: Write the failing test**

Add frontend coverage proving:
- `local_agent` mode can be selected
- `local_agent_id` is saved

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js`
Expected: FAIL because settings UI does not yet expose agent selection.

- [ ] **Step 3: Write minimal implementation**

Update the settings card to show:
- engine select with `server_http`, `server_playwright`, `local_agent`
- online local agent dropdown when `local_agent` is selected

- [ ] **Step 4: Run test to verify it passes**

Run the same command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/style.css frontend/src/autoModePersistence.test.js
git commit -m "feat: add local agent submit settings ui"
```

### Task 8: Show local-agent execution state in result center

**Files:**
- Modify: `frontend/src/autoModeStatus.js`
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/autoModeStatus.test.js`

- [ ] **Step 1: Write the failing test**

Add Vitest cases ensuring result-center descriptions show:
- `submit_engine = local_agent`
- `assigned_agent_id`
- queued/running local execution wording

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModeStatus.test.js`
Expected: FAIL because local-agent-specific messaging is missing.

- [ ] **Step 3: Write minimal implementation**

Extend status helpers and result-center UI to display:
- execution location
- assigned agent
- local queued/running/success/failure state

- [ ] **Step 4: Run test to verify it passes**

Run the same command.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/autoModeStatus.js frontend/src/App.vue frontend/src/autoModeStatus.test.js
git commit -m "feat: show local agent customs status"
```

## Chunk 6: Verification

### Task 9: Run verification suite and restart services

**Files:**
- Modify: `app/main.py`
- Modify: `app/llm_settings_store.py`
- Create: `app/local_agent_store.py`
- Create: `agent/local_customs_agent.py`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/autoModeStatus.js`
- Modify: `frontend/src/autoModePersistence.test.js`
- Modify: `frontend/src/autoModeStatus.test.js`
- Modify: `tests/test_customs_submission.py`

- [ ] **Step 1: Run backend tests**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: PASS.

- [ ] **Step 2: Run frontend targeted tests**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm test -- src/autoModePersistence.test.js src/autoModeStatus.test.js`
Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run: `cd /home/sip-telecom/Services/carsem_ocr/frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Restart services**

Restart backend and frontend services with the existing process manager.

- [ ] **Step 5: Verify health**

Run: `curl -s http://127.0.0.1:16068/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add app agent frontend tests
git commit -m "feat: add local agent customs submit mode"
```
