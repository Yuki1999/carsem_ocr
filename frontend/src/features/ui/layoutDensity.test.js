import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(resolve(__dirname, '../../styles/style.css'), 'utf8')
const appVue = readFileSync(resolve(__dirname, '../../App.vue'), 'utf8')

describe('layout density CSS', () => {
  it('matches the NovaIDP design shell with overview as the default entry', () => {
    expect(appVue).toContain('NovaIDP')
    expect(appVue).toContain("const currentNav = ref('overview')")
    expect(appVue).toContain("key: 'overview', label: '总览'")
    expect(appVue).toContain("key: 'extract', label: '处理工作台'")
    expect(appVue).toContain("key: 'result', label: '审核中心'")
    expect(appVue).toContain("key: 'template', label: '模板中心'")
    expect(appVue).toContain("key: 'settings', label: '系统设置'")
    expect(appVue).toContain('class="app-global-header"')
    expect(appVue).toContain('class="global-search"')
    expect(appVue).toContain('class="workspace-switcher"')
    expect(appVue).toContain('class="notification-badge"')
    expect(css).toContain('.app-global-header')
    expect(css).toContain('.global-search')
    expect(css).toContain('.workspace-switcher')
  })

  it('implements the design-specific page shells for core workflows', () => {
    expect(appVue).toContain('dashboard-overview')
    expect(appVue).toContain('processing-workbench')
    expect(appVue).toContain('review-center-shell')
    expect(appVue).toContain('template-center-shell')
    expect(appVue).toContain('settings-console')
    expect(css).toContain('.dashboard-overview')
    expect(css).toContain('.processing-workbench')
    expect(css).toContain('.review-center-shell')
    expect(css).toContain('.template-center-shell')
    expect(css).toContain('.settings-console')
  })

  it('constrains workspace content instead of stretching every section edge to edge', () => {
    expect(css).toMatch(/\.ep-section\s*\{[^}]*max-width:/s)
    expect(css).toMatch(/\.app-global-header\s*\{[^}]*max-width:/s)
  })

  it('uses explicit compact grids for focused workspaces', () => {
    expect(css).toMatch(/\.focus-workspace-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+320px/s)
    expect(css).toMatch(/\.result-shell\s*\{[^}]*grid-template-columns:\s*260px\s+minmax\(0,\s*1fr\)/s)
  })

  it('organizes dense work areas with tabs instead of one long stacked page', () => {
    expect(appVue).toContain('const extractWorkspaceTab')
    expect(appVue).toContain('const resultWorkspaceTab')
    expect(appVue).toContain('class="workspace-tabs extract-workspace-tabs"')
    expect(appVue).toContain('class="workspace-tabs result-workspace-tabs"')
    expect(appVue).toContain('name="fields"')
    expect(appVue).toContain('name="goods"')
    expect(appVue).toContain('name="evidence"')
  })

  it('keeps the declaration panel compact with progressive field disclosure and topbar actions', () => {
    expect(appVue).toContain('const submissionExtraFieldsVisible')
    expect(appVue).toContain('const visibleCustomsHeaderFields')
    expect(appVue).toContain('class="submission-more-toggle"')
    expect(appVue).toContain('workspace-actions')
    expect(appVue).toContain('UserFilled')
  })

  it('aligns the declaration panel with the active case instead of the lower tab area', () => {
    expect(appVue).toContain('class="result-main-layout"')
    expect(appVue).toContain('class="result-main-primary"')
    expect(css).toMatch(/\.result-main-layout\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+minmax\(280px,\s*300px\)/s)
    expect(css).toMatch(/\.result-workspace-grid\s*\{[^}]*grid-template-columns:\s*1fr/s)
  })

  it('uses a restrained enterprise visual system instead of decorative marketing surfaces', () => {
    expect(css).toContain('--surface-1:')
    expect(css).toContain('--surface-2:')
    expect(css).toContain('--control-height:')
    expect(css).toContain('.focus-workspace')
    expect(css).not.toContain('Noto Serif SC')
    expect(css).not.toContain('radial-gradient')
  })

  it('keeps global chrome focused and moves operating metrics into a modal', () => {
    expect(appVue).toContain('const platformInsights')
    expect(appVue).not.toContain('class="product-insight-strip"')
    expect(appVue).toContain('const platformInsightsDialogVisible')
    expect(appVue).toContain('class="platform-insights-dialog"')
    expect(css).toContain('.platform-insights-dialog')
    expect(css).not.toContain('.product-insight-strip')
  })

  it('uses a modal upload wizard instead of always exposing setup panels', () => {
    expect(appVue).toContain('const uploadWizardVisible')
    expect(appVue).toContain('class="focus-workspace"')
    expect(appVue).toContain('class="upload-wizard-dialog"')
    expect(appVue).toContain('class="upload-wizard-steps"')
    expect(css).toContain('.focus-workspace')
    expect(css).toContain('.upload-wizard-dialog')
  })
})
