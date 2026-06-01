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
    expect(appVue).toContain('TeleIDP')
    expect(appVue).not.toContain('NovaIDP')
    expect(appVue).toContain('处理工作台')
    expect(appVue).toContain('MinerU API')
    expect(appVue).toContain('JSON Schema 约束')
    expect(appVue).toContain('回写 TMS/WMS/ERP/关务系统')
    expect(appVue).not.toContain('物流单智能抽取')
    expect(appVue).not.toContain('CARSEM SEMICONDUCTOR')
  })

  test('primary navigation uses the requested four-item order', () => {
    const appVue = readFileSync(resolve(__dirname, 'App.vue'), 'utf-8')
    const navItems = appVue.match(/const NAV_ITEMS = \[[\s\S]*?\n\]/)?.[0] || ''

    expect(appVue).toContain("const currentNav = ref('template')")
    expect(navItems).toMatch(/key: 'template'[\s\S]*key: 'extract'[\s\S]*key: 'result'[\s\S]*key: 'settings'/)
    expect(navItems).not.toContain("key: 'overview'")
    expect(navItems).not.toContain("label: '总览'")
    expect(navItems).not.toContain("key: 'evidence'")
    expect(navItems).not.toContain("label: '证据中心'")
    expect(navItems).not.toContain("key: 'automation'")
    expect(navItems).not.toContain("label: '自动化任务'")
  })

  test('primary navigation lives in the global top header', () => {
    const appVue = readFileSync(resolve(__dirname, 'App.vue'), 'utf-8')
    const template = appVue.slice(appVue.indexOf('<template>'))
    const header = template.match(/<header class="app-global-header">[\s\S]*?<\/header>/)?.[0] || ''

    expect(header).toContain('class="ep-brand"')
    expect(header).toContain('class="ep-nav global-nav"')
    expect(header).toContain('mode="horizontal"')
    expect(header).not.toContain('workspace-switcher')
    expect(header).not.toContain('notification-badge')
    expect(header).not.toContain('默认工作区')
    expect(template).not.toContain('<el-aside')
    expect(template).not.toContain("currentNav === 'overview'")
    expect(template).not.toContain('collapse-menu-button')
  })
})
