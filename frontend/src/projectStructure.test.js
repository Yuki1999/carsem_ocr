import { describe, expect, test } from 'vitest'

import { createEmptySubmissionDraft } from './features/extraction/submissionDraft'
import { loadLlmSettings } from './features/settings/llmSettings'

describe('project structure', () => {
  test('new feature module paths are importable', () => {
    expect(typeof createEmptySubmissionDraft).toBe('function')
    expect(typeof loadLlmSettings).toBe('function')
  })
})
