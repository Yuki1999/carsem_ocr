import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(resolve(__dirname, '../../styles/style.css'), 'utf8')
const appVue = readFileSync(resolve(__dirname, '../../App.vue'), 'utf8')

describe('layout density CSS', () => {
  const countSelector = (selector) => {
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return (css.match(new RegExp(`${escaped}\\s*\\{`, 'g')) || []).length
  }

  it('matches the TeleIDP design shell with template center as the default entry', () => {
    expect(appVue).toContain('TeleIDP')
    expect(appVue).not.toContain('NovaIDP')
    expect(appVue).toContain("const currentNav = ref('template')")
    expect(appVue).not.toContain("key: 'overview', label: '总览'")
    expect(appVue).toMatch(/key: 'template', label: '模板中心'[\s\S]*key: 'extract', label: '处理工作台'[\s\S]*key: 'result', label: '审核中心'[\s\S]*key: 'settings', label: '系统设置'/)
    expect(appVue).toContain("key: 'extract', label: '处理工作台'")
    expect(appVue).toContain("key: 'result', label: '审核中心'")
    expect(appVue).toContain("key: 'template', label: '模板中心'")
    expect(appVue).toContain("key: 'settings', label: '系统设置'")
    expect(appVue).toContain('class="app-global-header"')
    expect(appVue).toContain('class="ep-nav global-nav"')
    expect(appVue).toContain('mode="horizontal"')
    expect(appVue).toContain(':ellipsis="false"')
    expect(appVue).toContain('class="global-search"')
    expect(appVue).not.toContain('class="workspace-switcher"')
    expect(appVue).not.toContain('class="notification-badge"')
    expect(appVue).not.toContain('默认工作区')
    expect(css).toContain('.app-global-header')
    expect(css).toContain('.global-nav-group')
    expect(css).toContain('.global-search')
    expect(css).not.toContain('.workspace-switcher')
    expect(css).not.toContain('.notification-badge')
  })

  it('implements the design-specific page shells for core workflows', () => {
    expect(appVue).not.toContain('dashboard-overview')
    expect(appVue).toContain('processing-workbench')
    expect(appVue).toContain('review-center-shell')
    expect(appVue).toContain('template-center-shell')
    expect(appVue).toContain('settings-console')
    expect(css).not.toContain('.dashboard-overview')
    expect(css).toContain('.processing-workbench')
    expect(css).toContain('.review-center-shell')
    expect(css).toContain('.template-center-shell')
    expect(css).toContain('.settings-console')
  })

  it('frames TeleIDP around the production IDP pipeline and MinerU API', () => {
    expect(appVue).toContain('const PIPELINE_STAGES')
    expect(appVue).toContain('文件接入')
    expect(appVue).toContain('图像增强 / 去斜 / 方向识别')
    expect(appVue).toContain('单据分类')
    expect(appVue).toContain('OCR / 版面 / 表格解析')
    expect(appVue).toContain('字段抽取')
    expect(appVue).toContain('JSON Schema 约束')
    expect(appVue).toContain('业务规则校验')
    expect(appVue).toContain('人审异常')
    expect(appVue).toContain('回写 TMS/WMS/ERP/关务系统')
    expect(appVue).toContain('MinerU API')
    expect(appVue).toContain('templateContractCards')
    expect(appVue).toContain('reviewExceptionGroups')
    expect(appVue).toContain('runtimeConnectorCards')
    expect(css).toContain('.pipeline-stage-rail')
    expect(css).toContain('.template-contract-grid')
    expect(css).toContain('.review-exception-grid')
    expect(css).toContain('.settings-runtime-grid')
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

  it('does not keep stacked legacy shell styling layers after the TeleIDP redesign', () => {
    expect(css).not.toContain('Workspace UX refresh')
    expect(css).not.toContain('Enterprise product system refresh')
    expect(countSelector('.ep-shell')).toBeLessThanOrEqual(2)
    expect(countSelector('.ep-aside')).toBe(0)
    expect(countSelector('.ep-content')).toBeLessThanOrEqual(2)
    expect(countSelector('.ep-section')).toBeLessThanOrEqual(2)
    expect(css).toMatch(/@media \(max-width:\s*1160px\)[\s\S]*\.ep-shell\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column/s)
    expect(css).toMatch(/@media \(max-width:\s*1160px\)[\s\S]*\.global-nav\.el-menu--horizontal\s*\{[^}]*width:\s*100%/s)
    expect(css).toMatch(/@media \(max-width:\s*1160px\)[\s\S]*\.ep-main\s*\{[^}]*min-width:\s*100%/s)
  })

  it('keeps review workspace markup nested without leaking tab content as page text', () => {
    expect(appVue).not.toContain('</el-tabs>\n                                        </div>\n                                      </div>')
    expect(appVue).not.toContain('v-show="currentNav ===')
    expect(appVue).toContain('v-if="currentNav ===')
    expect(appVue).toMatch(/<div class="result-main-layout">[\s\S]*<div class="result-main-primary">[\s\S]*<div class="workspace-secondary">[\s\S]*<\/div>\s*<\/div>\s*<\/template>/)
  })
})
