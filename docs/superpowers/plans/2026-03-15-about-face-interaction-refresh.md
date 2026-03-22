# About Face Interaction Refresh Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the frontend interaction model so task selection, evidence review, and submission actions feel clearer and more intentional, while adding inline original-file preview for history records.

**Architecture:** Keep the existing Vue single-page structure, but reorganize the result center into a case-oriented workspace with a summary band, stronger history navigation, and a new evidence deck that supports original-file preview. Refine the settings and extraction screens so durable controls and runtime actions are visually distinct.

**Tech Stack:** Vue 3, Element Plus, Vite, CSS, Vitest

---

## File Structure

- Modify: `frontend/src/App.vue`
  Responsibility: add evidence deck state, original-file preview logic, updated result-center layout, and lighter settings/extraction interaction copy.
- Modify: `frontend/src/style.css`
  Responsibility: add the new layout, tabs, summary strips, active-case styling, and preview surfaces.
- Modify: `frontend/src/submissionDraft.test.js`
  Responsibility: keep existing helper coverage green after UI-side changes.

## Chunk 1: Add Evidence Deck State

### Task 1: Introduce result-evidence selection logic

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Add a failing UI behavior target**

Define the behavior in code comments and by introducing state usage that is currently missing:

- evidence tab state
- original-file candidate selection
- preview type detection

- [ ] **Step 2: Implement minimal evidence state**

Add helpers for:

- detecting original file candidates from history assets
- choosing a default evidence tab
- determining whether to render PDF, image, markdown/text, or fallback download

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: PASS

## Chunk 2: Rebuild Result Center Around Active Case

### Task 2: Add case summary and evidence module

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Update the template layout**

Restructure the active result area into:

- case summary band
- extraction findings block
- submission workspace
- evidence deck with tabs

- [ ] **Step 2: Add original-file preview UI**

Render:

- inline PDF preview for PDF assets
- inline image preview for image assets
- markdown/text preview for extracted text
- fallback open/download panel for unsupported files

- [ ] **Step 3: Improve history rail emphasis**

Make the selected history item and live tasks feel like current cases instead of plain list entries.

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS

## Chunk 3: Clarify Extraction And Settings Posture

### Task 3: Refine system posture communication

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Adjust extraction screen copy and posture**

Show whether upload will run in manual or automatic mode near the submit area.

- [ ] **Step 2: Refine settings information hierarchy**

Make:

- LLM integration card feel like long-lived infrastructure
- automation card feel like system operating mode

- [ ] **Step 3: Keep current save flows untouched**

Do not change settings API behavior or task behavior.

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS

## Chunk 4: Final Verification

### Task 4: Verify refreshed interaction end to end

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run frontend tests**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: PASS

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Restart frontend service**

Run: `pm2 restart carsem-ocr-frontend`
Expected: process returns online

- [ ] **Step 4: Manual smoke check**

Verify in browser:

- history record opens with a clear active-case summary
- original PDF preview is visible when source PDF exists
- markdown/text preview remains available
- submission workspace still works
- settings page hierarchy is clearer

## Notes For Execution

- This workspace is not a git repository, so use verification checkpoints instead of commit steps.
- Keep the current backend/API contract intact.
- Preserve the existing manual controls even when rearranging layout.
