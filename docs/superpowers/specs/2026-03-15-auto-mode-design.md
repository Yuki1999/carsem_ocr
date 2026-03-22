# Auto Mode End-To-End Pipeline Design

## Background

The current system already supports:

- OCR extraction as an async task
- LLM-based customs submission draft generation
- Manual customs-site submission

The next capability is a global "auto mode" switch in system settings. When enabled, a newly submitted extraction task should continue automatically through:

1. OCR extraction
2. LLM field mapping into customs submission draft
3. Automatic customs-site submission

The user requested full automation after upload, with no intermediate confirmation clicks. If the generated submission draft still has required fields missing, the system should still attempt submission and let the customs website decide whether to accept or reject it.

## Goal

Add a global auto mode that turns the current semi-manual workflow into a backend-orchestrated end-to-end pipeline while preserving the existing manual controls for fallback and review.

## Non-Goals

- No retroactive auto-run for old history records
- No repeated automatic retries for the same history record in the first version
- No removal of the manual "generate draft" / "submit" actions

## Recommended Architecture

Use backend orchestration instead of front-end click automation.

### Why backend orchestration

- Task state remains durable even if the user refreshes or closes the page
- The system can expose progress across extraction, draft mapping, and customs submission in one task timeline
- Failure handling stays centralized on the server
- Credentials remain server-side

## Settings Design

Extend the existing persisted system settings with a global boolean:

```json
{
  "active_id": "...",
  "items": [...],
  "auto_mode_enabled": false
}
```

This should live together with the existing LLM settings storage so the frontend can manage it from the current "系统设置" screen.

## Task Pipeline Design

### Existing extraction task behavior

Today the extraction task stops after OCR/LLM extraction and history persistence.

### New auto mode behavior

If `auto_mode_enabled` is true, the extraction task should continue after history persistence:

1. extraction succeeds and creates a history record
2. backend generates a customs submission draft with LLM
3. backend validates the draft, but does not block on missing required fields
4. backend attempts customs submission once
5. extraction task result is updated with auto-mode outcome

### Proposed task stages

- `queued`
- `running_prepare`
- `running_mineru`
- `saving_history`
- `running_submission_mapping`
- `running_customs_submit`
- `done`
- `failed`

### Result payload additions

The extract task result should include auto-mode status so the frontend can display it immediately:

```json
{
  "history": {...},
  "auto_mode_enabled": true,
  "auto_mode_status": "succeeded",
  "auto_mode_message": "自动填报完成",
  "customs_submit_task_id": "..."
}
```

## Failure Handling

### Mapping stage failure

If LLM draft generation fails:

- extraction task becomes `failed`
- history record remains available with OCR result
- user can still open result center and manually regenerate the draft later

### Customs submission failure

If customs submission fails:

- extraction task becomes `failed`
- history record keeps the generated draft and failure message
- user can manually adjust the draft and retry submission

### Missing required fields

Per user instruction, missing required fields should not stop auto mode.

Behavior:

- validation still runs
- `required_missing` still gets recorded on draft meta
- auto mode still proceeds to submit
- final accept/reject comes from the customs site

## Frontend Behavior

### Settings page

Add an "自动模式" switch in the current system settings screen with explanatory text:

- Off: current manual flow
- On: upload then automatically run extraction, mapping, and customs submission

### Result center

Keep existing manual controls, but when auto mode is enabled:

- the task list should show the later pipeline stages
- the result center should show auto-mode status and message
- the draft editor remains available as a fallback repair tool

### Upload flow

The upload form remains the same. The difference is entirely in backend task continuation and frontend progress messaging.

## Backend Components To Change

- `app/llm_settings_store.py`
  Add `auto_mode_enabled` persistence and normalization.
- `app/main.py`
  Extend extraction task execution to call draft generation and customs submission when auto mode is on.
- `app/customs_submission.py`
  Reuse current draft generation and validation helpers.
- `app/customs_browser.py`
  Reuse current submission implementation.

## Testing Strategy

### Backend tests

- auto mode setting persists and loads correctly
- extract task in manual mode stops after history save
- extract task in auto mode continues into draft generation
- extract task in auto mode continues into customs submission even when `required_missing` is non-empty
- task result includes auto-mode status and message

### Frontend tests

- settings page renders and saves auto mode switch
- task/result UI reflects auto mode stages and final status

### Integration verification

- enable auto mode
- submit one sample extraction
- confirm task runs through extraction, mapping, and customs submission
- confirm history detail stores submission result and declaration number if available

## Risks And Mitigations

### Risk: end-to-end task becomes long-running

Mitigation: keep stage updates frequent so the UI reflects progress clearly.

### Risk: auto mode submits low-quality drafts

Mitigation: preserve `required_missing`, `mapping_notes`, and full manual repair path.

### Risk: user accidentally leaves auto mode on

Mitigation: place the switch in system settings with clear explanatory text and visible current status.

## Status

Recommended design chosen by the user on March 15, 2026.
