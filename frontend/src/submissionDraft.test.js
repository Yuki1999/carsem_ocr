import { describe, expect, it } from 'vitest'
import {
  appendDraftDetailRow,
  buildDraftSummary,
  createEmptySubmissionDraft,
  normalizeSubmissionDraft,
  removeDraftDetailRow,
  updateDraftDetailField,
  updateDraftHeaderField,
} from './submissionDraft'

describe('buildDraftSummary', () => {
  it('counts missing required fields', () => {
    const summary = buildDraftSummary({
      header: { Mawb: '-1', CustomerName: '嘉盛' },
      details: [{ ItemCode: 'A1', ItemOrigin: '-1', ItemQuantity: '10', ItemGoodQuantity: '10', ItemPrice: '20', ItemUnitPrice: '2' }],
      meta: { required_missing: ['details[0].ItemOrigin', 'details[0].ItemPrice'] },
    })

    expect(summary.missingCount).toBe(2)
  })
})

describe('draft edits', () => {
  it('updates a header field immutably', () => {
    const draft = createEmptySubmissionDraft()
    const next = updateDraftHeaderField(draft, 'Mawb', 'MBL001')

    expect(next.header.Mawb).toBe('MBL001')
    expect(draft.header.Mawb).toBe('-1')
  })

  it('updates the correct detail row', () => {
    const draft = appendDraftDetailRow(appendDraftDetailRow(createEmptySubmissionDraft()))
    const next = updateDraftDetailField(draft, 1, 'ItemCode', 'A-2')

    expect(next.details[1].ItemCode).toBe('A-2')
    expect(next.details[0].ItemCode).toBe('-1')
  })

  it('removes the target detail row', () => {
    const first = updateDraftDetailField(appendDraftDetailRow(createEmptySubmissionDraft()), 0, 'ItemCode', 'A-1')
    const second = updateDraftDetailField(appendDraftDetailRow(first), 1, 'ItemCode', 'A-2')
    const next = removeDraftDetailRow(second, 0)

    expect(next.details).toHaveLength(2)
    expect(next.details[0].ItemCode).toBe('A-2')
    expect(next.details[1].ItemCode).toBe('-1')
  })

  it('defaults header and detail fields to -1', () => {
    const draft = createEmptySubmissionDraft()

    expect(draft.header.Mawb).toBe('-1')
    expect(draft.header.Hawb).toBe('-1')
    expect(appendDraftDetailRow(draft).details[0].ItemCode).toBe('-1')
  })

  it('normalizes legacy MainBLNo and SubBLNo fields into Mawb and Hawb', () => {
    const normalized = normalizeSubmissionDraft({
      header: { MainBLNo: 'MBL001', SubBLNo: 'HBL001', CustomerName: '嘉盛' },
      details: [],
      meta: {},
    })

    expect(normalized.header.Mawb).toBe('MBL001')
    expect(normalized.header.Hawb).toBe('HBL001')
  })
})
