# About Face Interaction Refresh Design

## Background

The current frontend already supports:

- template management
- extraction task submission
- task and history browsing
- OCR result review
- customs submission draft editing
- system-wide automation settings

Functionally, the product is strong, but the main screens still behave like stacked admin panels. The interaction cost is higher than it needs to be, especially when a user returns to an existing record and needs to quickly answer:

1. what happened on this record
2. what the system believes
3. what evidence supports it
4. what action should happen next

The user requested an optimization inspired by *About Face 4*. The right response is not a cosmetic reskin. It is a clearer interaction model that reduces cognitive friction and makes status, intent, and next actions obvious.

## Goal

Reframe the UI around a task-centered workflow so the product feels like an operator console rather than a collection of settings and output panels.

## Non-Goals

- No backend workflow changes are required for this design pass
- No new business features are required to ship this interaction refresh
- No full information architecture rewrite across every page

## Recommended Interaction Direction

Use a task-centered control room layout.

### Why this direction

- It matches the product's real usage pattern: users launch work, monitor progress, inspect evidence, then decide whether to accept or intervene
- It preserves power-user density without feeling like a raw debug surface
- It lets history revisit scenarios feel intentional instead of fragmented

## Core Interaction Principles

### 1. Make the current object of attention explicit

The selected history record should feel like the active case, not just a row in a list.

The page should establish:

- current file
- current automation state
- whether draft or submission already exists
- most likely next action

### 2. Put evidence next to decisions

Detected fields, submission draft, and source material should be arranged so users can move between them without losing context.

The interface should support:

- seeing extracted values
- checking source proof
- previewing the original source file
- editing submission values

### 3. Separate durable settings from runtime actions

Settings should explain system posture, not compete with live task actions.

The automation toggle should be clearly a system mode control. LLM provider configuration should feel operational and long-lived, not mixed with task-time explanations.

### 4. Promote primary actions, demote utilities

For each screen, one or two actions should be visually primary. Refresh, collapse, and download controls should remain available but should not visually compete with the main flow.

## Screen Design

## Result Center

This becomes the primary operational screen.

### Left rail: Case navigation

The left side remains responsible for task and history selection, but the content is reorganized into clearer bands:

- toolbar with refresh utilities
- live task queue with stronger stage messaging
- history list with stronger active-state emphasis

The selected history item should read like an active case card rather than a generic list row.

### Right side: Active case workspace

The right side should be split into four readable zones:

1. **Case summary**
   - filename, template, model, automation status, timestamp
   - one-line system interpretation of what happened

2. **Extraction findings**
   - detected field cards remain, but grouped as high-signal findings
   - commodity/sublist data remains nearby

3. **Evidence deck**
   - tabs or segmented switch for:
     - original file preview
     - markdown/text preview
     - generated assets when present
   - PDF should be previewed inline when possible
   - images should render inline
   - unsupported files should show a direct-open/download affordance

4. **Submission workspace**
   - submission draft stays editable
   - summary strip shows missing required fields, detail count, and submit state
   - primary action remains “执行填报”

This arrangement follows the About Face idea of keeping related information and actions in one place so users do not have to mentally stitch together separate parts of the system.

## System Settings

The settings page should read as two independent, durable controls:

- LLM access and provider configuration
- automation mode posture

The current version already moved the automation card outside the LLM card. This design pass should refine that further:

- stronger distinction between “integration” and “operating mode”
- less explanatory clutter
- clearer status-led presentation

### LLM card

This card should emphasize:

- which configuration is active
- which provider and model are being used
- where operators make stable changes

### Automation card

This card should emphasize:

- current mode first
- what the pipeline does
- what happens when it is on

The switch should be visually secondary to the status narrative, so the user first understands the consequence and then changes it.

## Extraction Workbench

This page should stay lighter than the result center.

The extraction page is for launch, not analysis. It should:

- keep the upload area and prompt editing
- clarify whether new work will run in manual or automatic mode
- keep one dominant submit action

This means the page should show the active automation posture near the submit area, so users know whether upload will stop after extraction or continue to customs submission automatically.

## Visual Direction

Use a refined editorial-control-room aesthetic rather than a generic enterprise dashboard.

Characteristics:

- strong section headers
- compact but breathable spacing
- muted structural surfaces with more contrast around active items
- warm evidence surfaces for document preview
- clear visual distinction between “status”, “evidence”, and “action”

The goal is confidence and orientation, not visual noise.

## Component-Level Changes

### New result summary strip

Add a summary strip at the top of the active case view showing:

- file name
- current pipeline state
- draft presence
- customs submission outcome

### New evidence tabs

Add a new evidence module in the result center with tabs:

- `原始文件`
- `Markdown / 文本`
- `产物文件`

Selection should persist while browsing within the same history record.

### Original file preview rules

- PDF: inline iframe/embed preview
- image files: inline image preview
- text/markdown: reuse existing markdown/text rendering
- unsupported office/binary files: show filename, type hint, and open/download action

### History revisit behavior

When a history record opens:

- the evidence module should pick the most useful default asset automatically
- if a PDF source exists, default to original preview
- otherwise default to markdown/text preview

This directly addresses the reported pain that returning to a history record does not feel informative enough.

## Error Handling And Feedback

- If original asset preview cannot render, show a clear fallback card rather than a blank area
- If no previewable asset exists, explain what is available
- If a draft is already cached, say it is reused instead of making the user wonder why nothing happened
- Auto-mode messages should be phrased as outcome summaries, not raw internal states

## Testing Strategy

### Frontend verification

- open a history record with PDF source and confirm inline original preview appears
- switch between original preview and markdown preview
- revisit the same history record and confirm the workspace remains readable
- verify responsive behavior on narrow screens

### Regression verification

- manual draft generation and submission controls still work
- settings save flow remains unchanged
- task list and history selection still work

## Status

Recommended design selected by the user on March 15, 2026.
