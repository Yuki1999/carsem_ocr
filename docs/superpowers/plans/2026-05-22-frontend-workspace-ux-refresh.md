# Frontend Workspace UX Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Vue/Element Plus frontend workspace so upload, result review, and customs draft workflows are clearer and easier to use.

**Architecture:** Keep the existing single-page App.vue structure and centralized style.css. Add small computed helpers for UI state, then refresh CSS tokens and component styling without changing backend contracts.

**Tech Stack:** Vue 3, Element Plus, CSS, Vitest, Vite.

---

### Task 1: UI State Helpers

**Files:**
- Modify: `frontend/src/features/extraction/submissionDraft.js`
- Test: `frontend/src/features/extraction/submissionDraft.test.js`

- [ ] Add tests for review summary and warning state.
- [ ] Expose stable summary fields used by the refreshed UI.
- [ ] Run `npm run test -- submissionDraft.test.js`.

### Task 2: Workspace Layout Refresh

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/styles/style.css`

- [ ] Add a compact top context bar inside the main content.
- [ ] Improve result, upload, task/history, and customs review markup where needed.
- [ ] Refresh CSS tokens, cards, buttons, tables, upload area, nav, and responsive rules.

### Task 3: Verification

**Files:**
- No new production files.

- [ ] Run `npm run test`.
- [ ] Run `npm run build`.
- [ ] Run backend tests if shared code changed.
- [ ] Verify desktop and mobile screenshots.
- [ ] Run graphify rebuild command and record result.
- [ ] Restart PM2 services and check health.
