# Customs Auto Fill Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reviewable customs-site submission draft to OCR results and a manual server-side headless-browser submission flow for `vatest.carsem.com.cn`.

**Architecture:** Keep OCR extraction unchanged, then derive a separate `submission` draft from stored OCR results. Persist the draft on each history record, expose APIs to regenerate/edit/submit it, and run the actual customs-site fill through a backend Playwright task while the frontend result center shows draft editing and submission status.

**Tech Stack:** FastAPI, Python 3.11, Vue 3, Element Plus, Vite, Playwright, pytest, Vitest

---

## File Structure

- Create: `app/customs_submission.py`
  Responsibility: draft schema helpers, required-field validation, alias mapping, response mutation helpers.
- Create: `app/customs_browser.py`
  Responsibility: Playwright login/fill/submit flow for the customs site.
- Create: `tests/test_customs_submission.py`
  Responsibility: backend TDD coverage for draft generation and validation.
- Create: `frontend/src/submissionDraft.js`
  Responsibility: frontend draft normalization, validation summary, and payload helpers.
- Create: `frontend/src/submissionDraft.test.js`
  Responsibility: frontend TDD coverage for draft helpers.
- Modify: `app/template_store.py`
  Responsibility: extend template schema with optional customs mapping configuration.
- Modify: `app/history_store.py`
  Responsibility: support updating the persisted response with draft/submission state.
- Modify: `app/main.py`
  Responsibility: generate drafts, expose draft and submission APIs, manage async submission tasks.
- Modify: `frontend/package.json`
  Responsibility: add test dependencies and scripts for Vitest.
- Modify: `frontend/src/App.vue`
  Responsibility: add draft preview/edit UI, submission controls, and submission-task polling.

## Chunk 1: Backend Draft Model And Template Mapping

### Task 1: Add backend tests for draft generation

**Files:**
- Create: `tests/test_customs_submission.py`
- Modify: none

- [ ] **Step 1: Write the failing test**

```python
from app.customs_submission import build_submission_draft


def test_build_submission_draft_maps_header_and_detail_fields():
    payload = {
        "detected": {
            "主提单号": "MBL001",
            "客户名称": "嘉盛",
            "总价格": "1000",
            "商品明细": [
                {"料号": "P-01", "原产国": "JP", "数量": "10", "良品数量": "9", "总价": "900", "单价": "90"},
            ],
        }
    }
    template = {
        "customs_mapping": {
            "header": {"主提单号": "MainBLNo", "客户名称": "CustomerName", "总价格": "TotalPrice"},
            "detail": {"料号": "ItemCode", "原产国": "ItemOrigin", "数量": "ItemQuantity", "良品数量": "ItemGoodQuantity", "总价": "ItemPrice", "单价": "ItemUnitPrice"},
        }
    }

    draft = build_submission_draft(response_payload=payload, template=template)

    assert draft["header"]["MainBLNo"] == "MBL001"
    assert draft["header"]["CustomerName"] == "嘉盛"
    assert draft["header"]["TotalPrice"] == "1000"
    assert draft["details"][0]["ItemCode"] == "P-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py::test_build_submission_draft_maps_header_and_detail_fields -q`
Expected: FAIL with missing module or missing function.

- [ ] **Step 3: Write minimal implementation**

Create `app/customs_submission.py` with:

- `CUSTOMS_HEADER_FIELDS`
- `CUSTOMS_DETAIL_FIELDS`
- `build_submission_draft(response_payload, template)`
- minimal explicit-mapping support for header and details
- placeholder `meta` block

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_customs_submission.py::test_build_submission_draft_maps_header_and_detail_fields -q`
Expected: PASS

- [ ] **Step 5: Add alias fallback test**

```python
def test_build_submission_draft_uses_aliases_when_template_mapping_missing():
    payload = {
        "detected": {
            "主提运单号": "MBL002",
            "客户": "Carsem",
            "商品明细": [{"商品料号": "X1", "原产国": "MY", "总价": "50", "单价": "5", "总数量": "10", "良品数量": "10"}],
        }
    }

    draft = build_submission_draft(response_payload=payload, template={})

    assert draft["header"]["MainBLNo"] == "MBL002"
    assert draft["header"]["CustomerName"] == "Carsem"
    assert draft["details"][0]["ItemCode"] == "X1"
```

- [ ] **Step 6: Run alias test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py::test_build_submission_draft_uses_aliases_when_template_mapping_missing -q`
Expected: FAIL because alias fallback is not implemented yet.

- [ ] **Step 7: Implement alias fallback and required-missing detection**

Extend `app/customs_submission.py` with:

- alias maps for common header/detail synonyms
- `required_missing` calculation
- `unmapped_fields` capture
- normalized `meta.auto_mapped`

- [ ] **Step 8: Run backend draft tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

- [ ] **Step 9: Local checkpoint**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS and no regressions in the draft helper file.

### Task 2: Extend template persistence for customs mapping

**Files:**
- Modify: `app/template_store.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing normalization test**

```python
from app.template_store import normalize_templates


def test_normalize_templates_keeps_customs_mapping():
    items = normalize_templates({
        "items": [{
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "llm_prompt": "{}",
            "customs_mapping": {"header": {"主提单号": "MainBLNo"}, "detail": {"料号": "ItemCode"}},
        }]
    })

    assert items[0]["customs_mapping"]["header"]["主提单号"] == "MainBLNo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py::test_normalize_templates_keeps_customs_mapping -q`
Expected: FAIL because `customs_mapping` is dropped today.

- [ ] **Step 3: Implement minimal normalization**

Update `app/template_store.py` to persist:

- `customs_mapping.header`
- `customs_mapping.detail`

Keep invalid values as empty dicts.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_customs_submission.py::test_normalize_templates_keeps_customs_mapping -q`
Expected: PASS

- [ ] **Step 5: Run backend test file**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

## Chunk 2: Backend Persistence And APIs

### Task 3: Add draft regeneration and save endpoints

**Files:**
- Modify: `app/main.py`
- Modify: `app/history_store.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write failing API-level tests for draft regeneration helpers**

Add helper-level tests first rather than full HTTP tests:

```python
from app.customs_submission import attach_submission_draft


def test_attach_submission_draft_writes_submission_into_response_payload():
    payload = {"detected": {"主提单号": "MBL001"}}

    updated = attach_submission_draft(payload, {"header": {}, "details": [], "meta": {}})

    assert "submission" in updated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py::test_attach_submission_draft_writes_submission_into_response_payload -q`
Expected: FAIL because helper does not exist yet.

- [ ] **Step 3: Implement payload mutation helpers**

In `app/customs_submission.py` add:

- `attach_submission_draft(response_payload, draft)`
- `merge_submission_draft(existing_draft, incoming_draft)`
- `validate_submission_draft(draft)`

Use immutable-style copies where practical.

- [ ] **Step 4: Run focused helper tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

- [ ] **Step 5: Add failing FastAPI tests or service-level tests for history update behavior**

Test the workflow:

- load history record
- update response payload with `submission`
- persist updated meta/index summary safely

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: FAIL because APIs/history update path is incomplete.

- [ ] **Step 7: Implement new endpoints in `app/main.py`**

Add:

- `POST /api/history/{record_id}/submission-draft`
- `PUT /api/history/{record_id}/submission-draft`

Implementation notes:

- infer the template from stored `vendor` and `doc_type`
- build or merge `submission`
- persist with `update_history_record_response`
- return the updated history detail or updated `submission`

- [ ] **Step 8: Run backend tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

### Task 4: Add async customs submission task API

**Files:**
- Modify: `app/main.py`
- Create: `app/customs_browser.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing submission-task test**

```python
from app.customs_submission import validate_submission_draft


def test_validate_submission_draft_requires_header_and_detail_fields():
    draft = {"header": {"MainBLNo": ""}, "details": [], "meta": {}}

    result = validate_submission_draft(draft)

    assert result["ok"] is False
    assert "MainBLNo" in result["required_missing"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py::test_validate_submission_draft_requires_header_and_detail_fields -q`
Expected: FAIL because validation is incomplete.

- [ ] **Step 3: Implement validation and task state structure**

In `app/customs_submission.py`:

- finalize required field lists
- return `{ok, required_missing, message}`

In `app/main.py`:

- add `_CUSTOMS_SUBMIT_TASKS`
- add async updater helpers mirroring extract tasks
- add `POST /api/history/{record_id}/submit-customs`
- add `GET /api/customs-submit/tasks`
- add `GET /api/customs-submit/tasks/{task_id}`

- [ ] **Step 4: Stub browser runner**

Create `app/customs_browser.py` with:

- `submit_to_customs_site(draft, credentials) -> dict`
- temporary placeholder raising clear `NotImplementedError` or returning deterministic fake object in tests via monkeypatch

- [ ] **Step 5: Add monkeypatched task test**

Test that submit endpoint:

- rejects invalid drafts
- starts task for valid drafts
- stores task metadata

- [ ] **Step 6: Run backend tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

## Chunk 3: Playwright Browser Automation

### Task 5: Implement live browser submission flow

**Files:**
- Modify: `app/customs_browser.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write failing browser-helper tests around selector contract**

Add small pure-function tests for:

- payload-to-form-field flattening
- detail row iteration order
- submit result normalization

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: FAIL because browser helper utilities are incomplete.

- [ ] **Step 3: Implement Playwright flow**

In `app/customs_browser.py`:

- open login page
- submit username/password
- assert landing page contains `#dataForm`
- fill header inputs by `name`
- click `#addDetailRow` before each detail row
- fill `.detail-row` inputs in order
- capture dialog/alert text
- submit form and return structured result

Use environment variables such as:

- `CUSTOMS_SITE_URL`
- `CUSTOMS_USERNAME`
- `CUSTOMS_PASSWORD`

- [ ] **Step 4: Add safe failure handling**

Return normalized error categories:

- `login_failed`
- `page_structure_changed`
- `submission_rejected`
- `network_error`
- `unexpected_error`

- [ ] **Step 5: Run backend tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

- [ ] **Step 6: Manual integration verification**

Run a small local script or dedicated endpoint call against the live test site using the approved test credentials stored in env vars.
Expected: successful draft submission or a structured error with enough detail to debug.

## Chunk 4: Frontend Draft Editing Experience

### Task 6: Add frontend helper tests and utilities

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/submissionDraft.js`
- Create: `frontend/src/submissionDraft.test.js`

- [ ] **Step 1: Write failing Vitest cases**

```js
import { describe, expect, it } from 'vitest'
import { buildDraftSummary } from './submissionDraft'

describe('buildDraftSummary', () => {
  it('counts missing required fields', () => {
    const summary = buildDraftSummary({
      header: { MainBLNo: '', CustomerName: '嘉盛' },
      details: [{ ItemCode: 'A1', ItemOrigin: '', ItemQuantity: '10', ItemGoodQuantity: '10', ItemPrice: '20', ItemUnitPrice: '2' }],
      meta: { required_missing: ['MainBLNo', 'details[0].ItemOrigin'] },
    })

    expect(summary.missingCount).toBe(2)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: FAIL because script/helper does not exist yet.

- [ ] **Step 3: Implement frontend helper module**

Add:

- `normalizeSubmissionDraft`
- `buildDraftSummary`
- `updateDraftHeaderField`
- `updateDraftDetailField`

- [ ] **Step 4: Add Vitest config/scripts**

Update `frontend/package.json` with:

- `test`
- `test:watch`

Add `vitest` dev dependency if needed.

- [ ] **Step 5: Run focused frontend tests**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: PASS

### Task 7: Add result-center draft UI

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/submissionDraft.js`
- Test: `frontend/src/submissionDraft.test.js`

- [ ] **Step 1: Add failing helper tests for edit operations**

Cover:

- header edits update a field immutably
- detail edits update the correct row
- add/remove detail row helpers maintain valid shape

- [ ] **Step 2: Run tests to verify failure**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: FAIL because edit helpers are incomplete.

- [ ] **Step 3: Implement UI in `frontend/src/App.vue`**

Add:

- submission draft state derived from `historyDetail.response.submission`
- "生成填报草稿" action when missing
- editable header/detail fields
- missing-required summary
- `保存草稿` button
- `执行填报` button

- [ ] **Step 4: Wire API calls**

Add frontend calls for:

- regenerate draft
- save draft
- start customs submission
- poll customs submission task

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: PASS

- [ ] **Step 6: Run frontend build**

Run: `cd frontend && npm run build`
Expected: PASS

## Chunk 5: End-To-End Verification

### Task 8: Backend and frontend final verification

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run backend tests**

Run: `python -m pytest tests/test_customs_submission.py -q`
Expected: PASS

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test -- submissionDraft.test.js`
Expected: PASS

- [ ] **Step 3: Run frontend production build**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Manual application smoke test**

Run the app, upload a sample document, confirm:

- OCR result still renders
- draft generation works
- edits persist
- submit button starts a customs submission task

- [ ] **Step 5: Live customs-site verification**

Using test-site credentials from environment variables, submit one reviewed draft to `https://vatest.carsem.com.cn/` and confirm:

- task reports success
- returned status message is stored
- generated declaration number is visible if the page exposes it

- [ ] **Step 6: Final checkpoint**

Record any unresolved gaps such as live-site selector fragility or credentials setup requirements before claiming completion.

## Notes For Execution

- This workspace is not a git repository, so replace commit steps with local verification checkpoints.
- Keep browser selectors centralized in `app/customs_browser.py` so site DOM changes are easy to update.
- Do not expose customs credentials to the frontend.
- Prefer backend tests first for each behavior change, then frontend helper tests, then implementation.
