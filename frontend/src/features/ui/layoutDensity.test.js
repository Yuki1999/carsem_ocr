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

  it('uses explicit compact grids for extraction and result workspaces', () => {
    expect(css).toMatch(/\.extract-control-grid\s*\{[^}]*grid-template-columns:\s*minmax\(260px,\s*320px\)\s+minmax\(0,\s*1fr\)/s)
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
})
