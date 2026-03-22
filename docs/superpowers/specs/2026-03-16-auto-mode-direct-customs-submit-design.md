# Auto Mode Direct Customs Submit Design

## Background

The current system already has the basic pieces for auto mode:

- upload starts an async extraction task
- extraction persists a history record
- backend can generate a customs submission draft
- backend can submit the draft to `https://vatest.carsem.com.cn`
- result center already shows task status, OCR output, and submission draft

The user now wants auto mode to behave as a true end-to-end pipeline: upload one document, automatically submit it into the import customs system, and show the full progress in the result center.

## Goal

When global auto mode is enabled, uploading a document should automatically continue from OCR extraction into customs draft generation and direct customs submission, with clear stage-by-stage progress visible in the result center.

## Required Behavior

- Auto mode is a server-side pipeline, not a front-end click simulation
- Uploading a document starts one task that continues through extraction, draft generation, and customs submission
- Auto mode submits to the customs system by default, even when the draft still contains placeholder values like `-1`
- The result center must show:
  - current stage
  - progress percentage
  - auto mode status and message
  - customs submission status and returned message
- If customs submission fails, the overall auto-mode task is considered failed
- The generated draft and failure details remain available for manual repair and re-submit

## Architecture

Use the existing extraction task as the single long-running pipeline owner.

Pipeline:

1. upload file
2. run extraction
3. persist history record
4. generate customs submission draft
5. normalize the draft
6. submit to customs site
7. persist submission result
8. mark task as succeeded or failed

This keeps task state durable, avoids splitting the user experience across multiple tasks, and matches the current backend orchestration pattern already present in `app/main.py`.

## Task Stages

The extraction task should expose these stages consistently:

- `running_prepare`
- `running_extract`
- `running_submission_mapping`
- `running_customs_submit`
- `done`
- `failed`

These stage names should be reflected in the result center copy so the user can tell whether the system is extracting, generating a draft, or filling the customs site.

## Result Center Behavior

The result center should show two related layers of status:

### Task pipeline status

- current task stage
- progress percentage
- current task message

### Auto customs status

- `auto_mode_enabled`
- `auto_mode_status`
- `auto_mode_message`
- `submission.meta.submit_status`
- `submission.meta.submit_message`
- `submission.meta.submit_result`

The manual controls remain available:

- regenerate draft
- edit draft
- submit again manually

This ensures auto mode is the default path while manual recovery remains possible.

## Failure Semantics

### Draft generation failure

- task becomes `failed`
- history OCR result remains available
- no customs submit attempt happens

### Customs submission failure

- task becomes `failed`
- history record keeps the generated draft
- submission meta records failed status and returned message
- result center shows the failure clearly

### Success

- task becomes `done`
- submission meta is updated to `succeeded`
- result center shows customs success message and returned data if available

## Persistence Rules

The history record remains the durable source of truth.

On each auto-mode run:

- persist OCR response first
- attach generated submission draft to `response.submission`
- update submission meta to `running` before customs submit
- update submission meta to `succeeded` or `failed` after customs submit
- update the extract task result with:
  - `auto_mode_enabled`
  - `auto_mode_status`
  - `auto_mode_message`

## Non-Goals

- No automatic retry policy in this iteration
- No background queue split into a second submission task
- No blocking on missing required fields before auto-submit

## Testing

### Backend

- auto mode continues from extraction into submission draft generation
- auto mode continues into direct customs submission
- successful customs submission marks the task `done`
- customs submission failure marks the task `failed`
- history response stores submission draft and submission meta updates

### Frontend

- result center shows auto-mode stage and final status
- result center shows customs submission message from history/task result
- existing manual repair actions still remain visible
