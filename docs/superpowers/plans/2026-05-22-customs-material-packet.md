# Customs Material Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate customs submission drafts from one business packet using invoice rows as declaration detail rows and packing rows as validation evidence.

**Architecture:** Add a focused packet-draft service that converts source-level extracted data into the existing submission draft shape plus review metadata. Keep the existing extraction, history, and submission endpoints stable; the existing `build_submission_draft()` function calls the packet service when structured invoice or packing data exists.

**Tech Stack:** Python FastAPI backend, pytest, Vue 3 frontend, Vitest.

---

### Task 1: Backend Packet Draft Service

**Files:**
- Create: `app/services/customs_packet.py`
- Modify: `app/services/customs_submission.py`
- Test: `tests/test_customs_packet.py`

- [ ] Write failing tests for invoice original row detail generation, packing quantity grouping, mismatch review metadata, and header candidate conflicts.
- [ ] Run `pytest tests/test_customs_packet.py -q` and confirm the tests fail because the service does not exist.
- [ ] Implement `build_packet_submission_draft(response_payload, llm_output=None)` with no external dependencies.
- [ ] Call it from `build_submission_draft()` before the existing generic mapping when packet structures are present.
- [ ] Run `pytest tests/test_customs_packet.py -q`.

### Task 2: Prompt And Metadata Contract

**Files:**
- Modify: `app/api/app.py`
- Test: `tests/test_customs_submission.py`

- [ ] Add tests that the customs submission prompt asks the LLM to output `invoice_lines`, `packing_lines`, and `header_candidates`.
- [ ] Update `_build_customs_submission_prompt()` to describe the confirmed packet rules.
- [ ] Run focused backend tests.

### Task 3: Frontend Draft Metadata Preservation

**Files:**
- Modify: `frontend/src/features/extraction/submissionDraft.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/styles/style.css`
- Test: `frontend/src/features/extraction/submissionDraft.test.js`

- [ ] Add tests that `normalizeSubmissionDraft()` preserves `meta.packet` and `buildDraftSummary()` counts review items.
- [ ] Normalize packet metadata defensively in frontend draft utilities.
- [ ] Display packet review tags and concise review items in the submission workspace.
- [ ] Run focused Vitest tests.

### Task 4: Verification

**Files:**
- No new files.

- [ ] Run `pytest tests -q`.
- [ ] Run `npm run test` from `frontend/`.
- [ ] Run `npm run build` from `frontend/`.
- [ ] Run graphify rebuild command required by `AGENTS.md`; if unavailable, capture the exact failure.
- [ ] Restart PM2 services and verify backend health.
