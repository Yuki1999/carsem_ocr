import { describe, expect, it } from 'vitest'
import {
  buildFallbackPlatformInsights,
  buildInsightCards,
  normalizePlatformInsights,
} from './platformInsights'

describe('platform insights', () => {
  it('normalizes server insights into stable defaults', () => {
    const normalized = normalizePlatformInsights({
      queue: { running: 2, queued: 1 },
      history: { total: 12, recent: [{ id: 'h1', filename: 'invoice.xlsx', review_label: '低风险' }] },
      templates: { total: 5, common: 2, vendor: 3, doc_types: ['发票'] },
      review: { drafts_checked: 4, drafts_with_warnings: 1, missing_fields: 2, review_items: 3 },
      automation: { enabled: true, submit_mode: 'playwright', active_model: 'qwen3.5-plus' },
      recommendations: ['存在待复核资料'],
    })

    expect(normalized.queue.running).toBe(2)
    expect(normalized.queue.failed).toBe(0)
    expect(normalized.history.recent[0].filename).toBe('invoice.xlsx')
    expect(normalized.templates.vendor).toBe(3)
    expect(normalized.review.review_items).toBe(3)
    expect(normalized.automation.active_model).toBe('qwen3.5-plus')
    expect(normalized.recommendations).toEqual(['存在待复核资料'])
  })

  it('builds fallback insights from existing task history template and draft state', () => {
    const fallback = buildFallbackPlatformInsights({
      taskItems: [
        { status: 'running' },
        { status: 'queued' },
        { status: 'failed' },
      ],
      historyItems: [
        { id: 'h1', filename: 'demo.pdf', vendor: 'Samsung', doc_type: '发票', created_at: '2026-05-22T01:00:00+00:00' },
      ],
      templateStats: { common: 5, vendor: 4 },
      submissionSummary: { missingCount: 1, reviewCount: 2, detailCount: 3 },
      autoModeEnabled: false,
      customsSubmitMode: 'http',
      activeModel: 'gemini-3-flash-preview',
    })

    expect(fallback.queue.running).toBe(1)
    expect(fallback.queue.queued).toBe(1)
    expect(fallback.history.total).toBe(1)
    expect(fallback.templates.total).toBe(9)
    expect(fallback.review.drafts_with_warnings).toBe(1)
    expect(fallback.review.missing_fields).toBe(1)
    expect(fallback.review.review_items).toBe(2)
    expect(fallback.automation.enabled).toBe(false)
    expect(fallback.recommendations[0]).toContain('待复核')
  })

  it('builds product KPI cards for the operation cockpit', () => {
    const cards = buildInsightCards(normalizePlatformInsights({
      queue: { queued: 1, running: 2, failed: 0, succeeded: 5 },
      history: { total: 20, recent: [] },
      templates: { total: 10, common: 5, vendor: 5, doc_types: ['发票', '报关单'] },
      review: { drafts_checked: 6, drafts_with_warnings: 2, missing_fields: 1, review_items: 3 },
      automation: { enabled: true, submit_mode: 'playwright', active_model: 'qwen3.5-plus' },
    }))

    expect(cards.map((card) => card.label)).toEqual(['业务队列', '处理历史', '模板覆盖', '人审负载', '自动化'])
    expect(cards[0].value).toBe('3 个运行中')
    expect(cards[3].tone).toBe('warning')
    expect(cards[4].hint).toContain('playwright')
  })
})
