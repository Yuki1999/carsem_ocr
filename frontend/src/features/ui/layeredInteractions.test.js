import { describe, expect, it } from 'vitest'
import {
  buildExtractionLaunchReview,
  buildFieldDetailView,
} from './layeredInteractions'

describe('layeredInteractions', () => {
  it('marks extraction launch as blocked until file, template, and prompt are ready', () => {
    const review = buildExtractionLaunchReview({
      fileName: '',
      templateName: '未选择模板',
      fieldCount: 0,
      promptText: '',
      autoModeEnabled: false,
    })

    expect(review.ready).toBe(false)
    expect(review.blockerCount).toBe(3)
    expect(review.primaryLabel).toBe('补齐后开始')
    expect(review.items.map((item) => item.status)).toEqual(['error', 'error', 'error', 'info'])
  })

  it('summarizes a ready extraction launch with auto mode context', () => {
    const review = buildExtractionLaunchReview({
      fileName: 'DS12650253_IV(1).xlsx',
      templateName: 'Samsung · 报关单',
      fieldCount: 9,
      promptText: '请提取 JSON',
      autoModeEnabled: true,
    })

    expect(review.ready).toBe(true)
    expect(review.blockerCount).toBe(0)
    expect(review.primaryLabel).toBe('确认并开始')
    expect(review.modeLabel).toBe('自动流水线')
    expect(review.items.map((item) => item.status)).toEqual(['success', 'success', 'success', 'warning'])
  })

  it('builds readable field detail data for structured values', () => {
    const detail = buildFieldDetailView({
      key: '商品明细',
      raw: [{ 'SAMSUNG P/N': 'CL31B106KOHVPNE', PC: '224,000' }],
      value: '商品明细 1 项',
    })

    expect(detail.title).toBe('商品明细')
    expect(detail.statusLabel).toBe('已命中')
    expect(detail.valueText).toBe('商品明细 1 项')
    expect(detail.rawText).toContain('CL31B106KOHVPNE')
    expect(detail.isStructured).toBe(true)
  })
})
