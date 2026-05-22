# Project Structure Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the repository into clearer backend, frontend, docs, and sample-data areas without changing runtime behavior.

**Architecture:** Keep `app/` as the backend package and `frontend/src/` as the frontend root, but introduce focused subdirectories for API, services, stores, feature modules, and styles. Preserve compatibility at the main entrypoint and update all imports, docs, and process configs to use the new structure.

**Tech Stack:** FastAPI, Vue 3, Vite, PM2, pytest, vitest

---

### Task 1: Add structure regression tests

**Files:**
- Create: `tests/test_project_structure.py`
- Create: `frontend/src/projectStructure.test.js`

- [ ] Step 1: Write failing backend structure test
- [ ] Step 2: Run `pytest tests/test_project_structure.py -q` and verify it fails
- [ ] Step 3: Write failing frontend structure test
- [ ] Step 4: Run `npm test -- projectStructure.test.js` from `frontend/` and verify it fails

### Task 2: Reorganize backend package layout

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/services/__init__.py`
- Create: `app/store/__init__.py`
- Move or create: `app/api/app.py`
- Move or create: `app/services/*.py`
- Move or create: `app/store/*.py`
- Modify: `app/main.py`

- [ ] Step 1: Create backend package directories
- [ ] Step 2: Move API, service, and store modules into the new directories
- [ ] Step 3: Update backend imports and keep `app.main` as the public entrypoint
- [ ] Step 4: Run `pytest tests/test_project_structure.py -q`

### Task 3: Reorganize frontend source layout

**Files:**
- Create: `frontend/src/features/**`
- Create: `frontend/src/styles/style.css`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/main.js`
- Move or create: `frontend/src/features/**/*.js`
- Move or create: `frontend/src/features/**/*.test.js`

- [ ] Step 1: Create frontend feature directories
- [ ] Step 2: Move modules and tests into feature folders
- [ ] Step 3: Update Vue and test imports
- [ ] Step 4: Run `npm test -- projectStructure.test.js` from `frontend/`

### Task 4: Clean root-level documentation and sample files

**Files:**
- Create: `samples/`
- Create: `docs/user-guide.md`
- Create: `docs/user-guide.html`
- Modify: `README.md`

- [ ] Step 1: Move sample PDFs under `samples/`
- [ ] Step 2: Move user guide documents under `docs/`
- [ ] Step 3: Update README links and setup notes to reflect the new structure

### Task 5: Verify runtime behavior

**Files:**
- Verify: `ecosystem.config.cjs`
- Verify: `app/main.py`
- Verify: `frontend/src/main.js`

- [ ] Step 1: Run `pytest tests/test_project_structure.py tests/test_customs_submission.py tests/test_llm_extract.py tests/test_qwen_vision_extractor.py -q`
- [ ] Step 2: Run `npm test` from `frontend/`
- [ ] Step 3: Run `pm2 restart carsem-ocr-backend carsem-ocr-frontend`
- [ ] Step 4: Run `curl -fsS http://127.0.0.1:16068/api/health`
