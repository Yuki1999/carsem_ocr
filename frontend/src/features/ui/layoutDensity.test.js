import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(resolve(__dirname, '../../styles/style.css'), 'utf8')
const appVue = readFileSync(resolve(__dirname, '../../App.vue'), 'utf8')

describe('layout density CSS', () => {
  it('constrains workspace content instead of stretching every section edge to edge', () => {
    expect(css).toMatch(/\.ep-section\s*\{[^}]*max-width:/s)
    expect(css).toMatch(/\.workspace-topbar\s*\{[^}]*max-width:/s)
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
    expect(appVue).toContain('class="workspace-actions"')
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
    expect(appVue).toContain("const currentNav = ref('extract')")
    expect(appVue).not.toContain("key: 'overview'")
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
    expect(appVue).not.toContain("v-show=\"currentNav === 'overview'\"")
    expect(css).toContain('.focus-workspace')
    expect(css).toContain('.upload-wizard-dialog')
  })
})
