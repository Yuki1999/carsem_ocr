import { describe, expect, test } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { createEmptySubmissionDraft } from './features/extraction/submissionDraft'
import { loadLlmSettings } from './features/settings/llmSettings'

describe('project structure', () => {
  test('new feature module paths are importable', () => {
    expect(typeof createEmptySubmissionDraft).toBe('function')
    expect(typeof loadLlmSettings).toBe('function')
  })

  test('product copy positions the app as a universal IDP platform', () => {
    const appVue = readFileSync(resolve(__dirname, 'App.vue'), 'utf-8')
    const indexHtml = readFileSync(resolve(__dirname, '../index.html'), 'utf-8')

    expect(indexHtml).toContain('通用 IDP 智能文档处理平台')
    expect(appVue).toContain('NovaIDP')
    expect(appVue).toContain('智能文档处理总览')
    expect(appVue).toContain('处理工作台')
    expect(appVue).not.toContain('物流单智能抽取')
    expect(appVue).not.toContain('CARSEM SEMICONDUCTOR')
  })
})
